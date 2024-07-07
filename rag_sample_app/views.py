from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from .models import Document
from .serializers import DocumentSerializer
import openai
import os
import requests
from .models import ChatHistory
from .serializers import ChatHistorySerializer
from dotenv import load_dotenv
from uuid import uuid4
from rest_framework.decorators import api_view

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
class ChatHistoryListCreate(generics.ListCreateAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer

class DocumentList(APIView):
    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

class OpenAIResponse(APIView):
    def post(self, request):
        search_word = request.data.get("search_word")
        thread_id = request.data.get("thread_id")  # thread_idを取得

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
            combined_content = "\n".join([doc.get('content', 'No content found') for doc in results['value'][:1]])
            print(combined_content)
            prompt = f"以下の情報に基づいて質問に答えてください（答えられる情報がない場合は、AIベースの回答をしてください）: {combined_content}"
        else:
            prompt = search_word

        # ここでチャット履歴を取得して、messagesリストに追加する
        chat_history_items = ChatHistory.objects.filter(thread_id=thread_id).order_by('timestamp')
        messages = [{"role": "system", "content": "あなたは、プログラミングの専門家です。ユーザのエンジニアから、質問を受けて回答してください。プログラミングの質問以外は答えないでください。"}]
        
        for item in chat_history_items:
            messages.append({"role": "user", "content": item.user_input})
            messages.append({"role": "assistant", "content": item.ai_response})

        messages.append({"role": "user", "content": prompt})

        openai_response = openai.chat.completions.create(
            model="gpt-35-turbo",
            messages=messages
        )
        
        response = openai_response.choices[0].message.content
        # チャット履歴を保存
        print("#####################")
        print(search_word)
        print("#####################")
        chat_history = ChatHistory(user_input=prompt, ai_response=response)
        chat_history.save()
        print(prompt)
        return Response({"response": response})

@api_view(['POST'])
def create_new_thread(request):
    new_uuid = str(uuid4())
    new_thread = ChatHistory(thread_id=new_uuid)
    new_thread.save()  # 新しいスレッドIDを保存
    return Response({'thread_id': new_uuid})  # 新しいスレッドIDをフロントエンドに返す
