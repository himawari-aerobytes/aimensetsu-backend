from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from .models import Document,Thread
from .serializers import DocumentSerializer
import openai
import os
import requests
from .models import ChatHistory
from .serializers import ChatHistorySerializer
from dotenv import load_dotenv
from uuid import uuid4
from rest_framework.decorators import api_view, permission_classes
import datetime
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer
from rest_framework import status

load_dotenv()

# 環境変数の取得
api_key = os.getenv("API_KEY")
search_service = os.getenv("SEARCH_SERVICE")
index = os.getenv("INDEX")
aoai_api_key = os.getenv("OPENAI_API_KEY")
aoai_service_name = os.getenv("OPENAI_RESOURCE_NAME")
aoai_deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME")
aoai_resource_name=os.environ.get("OPENAI_RESOURCE_NAME")
aoai_api_version = os.getenv("OPENAI_API_VERSION")

# OpenAI APIの設定
openai.api_type = "azure"
openai.api_version = aoai_api_version
openai.api_key = aoai_api_key
openai.azure_endpoint = f"https://{aoai_resource_name}.openai.azure.com/openai/deployments/{aoai_deployment_name}/chat/completions?api-version={aoai_api_version}"

def limit_string_length(strings, max_length):
    """
        文字数制限を超えた文字列を切り詰める
    """
    if len(strings) > max_length:
        return strings[:max_length]
    return strings

def generate_and_save_summary(thread):
    chat_history_items = ChatHistory.objects.filter(thread_id=thread).order_by('timestamp').reverse()

    # ユーザからの入力を取得
    user_input = "\n".join([item.user_input for item in chat_history_items])
    thread.summary = user_input
    print("以下の内容を要約しました：",user_input)
    thread.save()
    return user_input

class ChatHistoryListCreate(generics.ListCreateAPIView):
    serializer_class = ChatHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thread_id = self.request.query_params.get('thread_id')
        user = self.request.user

        try:
            thread = Thread.objects.get(id=thread_id)
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)
        
        # スレッドの作成者が現在のユーザーかどうかを確認
        if thread.creator != user:
            return Response({"error": "You do not have permission to access this thread"}, status=403)
        
        return ChatHistory.objects.filter(thread_id=thread)


class DocumentList(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

class OpenAIResponse(APIView):
    def post(self, request):
        search_word = request.data.get("search_word")
        if search_word is None:
            return Response({"error": "search_word is required"}, status=400)
        thread_id = request.data.get("thread_id")  # thread_idを取得
        if thread_id:
            try:
                thread = Thread.objects.get(id=thread_id)
            except Thread.DoesNotExist:
                return Response({"error": "Thread not found"}, status=404)
        else:
            thread = Thread.objects.create()
            thread_id = str(thread.id)

        user = request.user
        # スレッドの作成者が現在のユーザーかどうかを確認
        if thread.creator != user:
            return Response({"error": "You do not have permission to access this thread"}, status=403)
        
        search_url = f"https://{search_service}.search.windows.net/indexes/{index}/docs"
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        params = {
            "api-version": "2021-04-30-Preview",
            "search": search_word
        }
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            try:
                results = response.json()
            except requests.exceptions.JSONDecodeError as e:
                return Response({"error": "JSON decode error: " + str(e)}, status=500)
        else:
            return Response({"error": f"Error {response.status_code}: {response.text}"}, status=response.status_code)
        
        
        if results['value']:
            max_length = 2000
            combined_content = "\n".join([limit_string_length(doc.get('content', 'No content found'),max_length)for doc in results['value'][:1]])
            #print(combined_content)
            # インスタンスの種類を確認
            print(combined_content)
            prompt = f"以下の<document>に基づいて質問に答えてください（答えられる情報がない場合は、AIベースの回答をしてください）<document> {combined_content}</document>"
        else:
            prompt = search_word

        # ここでチャット履歴を取得して、messagesリストに追加する
        chat_history_items = ChatHistory.objects.filter(thread_id=thread).order_by('timestamp')
        messages = [{"role": "system", "content": "あなたは、企業の面接官です。面接を受ける人に対して、適切な質問をしてください。最初は自己紹介から始めましょう。"}]
        

        for item in chat_history_items:
            messages.append({"role": "user", "content": item.user_input})
            messages.append({"role": "assistant", "content": item.ai_response})

        # search_wordを履歴に追加
        if search_word != prompt:
            messages.append({"role": "system", "content": search_word})
        
        messages.append({"role": "user", "content": prompt})

        openai_response = openai.chat.completions.create(
            model="gpt-35-turbo",
            messages=messages
        )
        
        response = openai_response.choices[0].message.content
        # チャット履歴を保存
        print("#####################")
        print(search_word)
        print(thread_id)
        print("#####################")

        # チャット履歴を保存
        chat_history = ChatHistory(thread_id=thread, user_input=search_word, ai_response=response, timestamp=datetime.datetime.now())
        chat_history.save()
        

        print(prompt)
        return Response({"response": response})
    
class ThreadSummary(APIView):
    def get(self, request, thread_id):
        try:
            thread = Thread.objects.get(id=thread_id)
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)

        if not thread.summary:
            summary = generate_and_save_summary(thread)
        else:
            summary = thread.summary

        return Response({"summary": summary})

class AllThreads(APIView):
    def get(self, request):
        threads = Thread.objects.all()
        thread_data = []
        for thread in threads:
            if not thread.summary:
                summary = generate_and_save_summary(thread)
            else:
                summary = thread.summary
            thread_data.append({
                "thread_id": str(thread.id),
                "summary": summary,
                "created_at": thread.created_at
            })
        return Response({"threads": thread_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_new_thread(request):
    print(request)
    user = request.user
    if not user.is_authenticated:
        return Response({"error": "User is not authenticated"}, status=403)

    new_thread = Thread.objects.create(creator=user)
    return Response({'thread_id': str(new_thread.id)})


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
