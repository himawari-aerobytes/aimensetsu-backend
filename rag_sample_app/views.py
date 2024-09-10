import datetime
import os
from uuid import uuid4

import openai
import requests
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from dotenv import load_dotenv
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import ChatHistory, Document, Thread
from .serializers import ChatHistorySerializer, DocumentSerializer, UserSerializer
from .utils import jwt_required  # utils.pyからデコレータをインポート

# 開発環境か本番環境かに応じてファイルを指定
environment = os.getenv("ENV", "development")
if environment == "production":
    load_dotenv(".env.production")
else:
    load_dotenv(".env.development")

# 環境変数の取得
api_key = os.getenv("API_KEY")
search_service = os.getenv("SEARCH_SERVICE")
index = os.getenv("INDEX")
aoai_api_key = os.getenv("OPENAI_API_KEY")
aoai_service_name = os.getenv("OPENAI_RESOURCE_NAME")
aoai_deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME")
aoai_resource_name = os.environ.get("OPENAI_RESOURCE_NAME")
aoai_api_version = os.getenv("OPENAI_API_VERSION")
SENDER_NAME_AI = "AI"

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
    chat_history_items = (
        ChatHistory.objects.filter(thread_id=thread)
        .exclude(sender=SENDER_NAME_AI)
        .order_by("timestamp")
        .reverse()
    )

    # ユーザからの入力を取得
    user_input = "\n".join([item.message for item in chat_history_items])
    thread.summary = user_input
    thread.save()
    return user_input


def get_openai_response(message):
    messages = [
        {
            "role": "system",
            "content": "あなたは、面接官の高橋です。面接を受ける人に対して、適切な質問をしてください。面接は１対１です。最初は自己紹介から始めましょう。",
        }
    ]
    messages.append({"role": "user", "content": message})
    openai_response = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages
    )
    return openai_response.choices[0].message.content


class ChatHistoryListCreate(generics.ListCreateAPIView):
    serializer_class = ChatHistorySerializer

    # dispatchメソッドにデコレータを適用
    @method_decorator(jwt_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        thread_id = self.request.query_params.get("thread_id")
        user = self.request.user

        try:
            thread = Thread.objects.get(id=thread_id)
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)

        # スレッドの作成者が現在のユーザーかどうかを確認
        if thread.creator != user:
            return Response(
                {"error": "You do not have permission to access this thread"},
                status=403,
            )

        return ChatHistory.objects.filter(thread_id=thread)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DocumentList(APIView):

    @method_decorator(jwt_required)
    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)


class OpenAIResponse(APIView):

    @method_decorator(jwt_required)
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
            return Response(
                {"error": "You do not have permission to access this thread"},
                status=403,
            )

        search_url = f"https://{search_service}.search.windows.net/indexes/{index}/docs"
        headers = {"Content-Type": "application/json", "api-key": api_key}
        params = {"api-version": "2021-04-30-Preview", "search": search_word}
        response = requests.get(search_url, headers=headers, params=params)

        if response.status_code == 200:
            try:
                results = response.json()
            except requests.exceptions.JSONDecodeError as e:
                return Response({"error": "JSON decode error: " + str(e)}, status=500)
        else:
            return Response(
                {"error": f"Error {response.status_code}: {response.text}"},
                status=response.status_code,
            )

        if results["value"]:
            max_length = 2000
            combined_content = "\n".join(
                [
                    limit_string_length(
                        doc.get("content", "No content found"), max_length
                    )
                    for doc in results["value"][:1]
                ]
            )
            prompt = f"以下の<document>に基づいて質問に答えてください（答えられる情報がない場合は、AIベースの回答をしてください）<document> {combined_content}</document>"
        else:
            prompt = search_word

        # ここでチャット履歴を取得して、messagesリストに追加する
        chat_history_items = ChatHistory.objects.filter(thread_id=thread).order_by(
            "timestamp"
        )
        messages = [
            {
                "role": "system",
                "content": "あなたは、企業の面接官です。面接を受ける人に対して、適切な質問をしてください。",
            }
        ]

        messages.append({"role": "assistant", "content": thread.first_message})

        for item in chat_history_items:
            if item.sender == "USER":
                messages.append({"role": "user", "content": item.message})
            elif item.sender == "AI":
                messages.append({"role": "assistant", "content": item.message})

        # search_wordを履歴に追加
        if search_word != prompt:
            messages.append({"role": "system", "content": search_word})

        messages.append({"role": "user", "content": prompt})

        openai_response = openai.chat.completions.create(
            model="gpt-35-turbo", messages=messages
        )

        response = openai_response.choices[0].message.content

        # チャット履歴を保存
        user_input = ChatHistory(
            thread_id=thread,
            message=search_word,
            timestamp=datetime.datetime.now(),
            sender="USER",
        )
        user_input.save()
        ai_input = ChatHistory(
            thread_id=thread,
            message=response,
            timestamp=datetime.datetime.now(),
            sender="AI",
        )
        ai_input.save()
        return Response({"response": response})


class ThreadSummary(APIView):

    @method_decorator(jwt_required)
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

    @method_decorator(jwt_required)
    def get(self, request):
        threads = Thread.objects.filter(creator=request.user).order_by("-created_at")
        thread_data = []
        for thread in threads:
            if not thread.summary:
                summary = generate_and_save_summary(thread)
            else:
                summary = thread.summary
            thread_data.append(
                {
                    "thread_id": str(thread.id),
                    "summary": summary,
                    "created_at": thread.created_at,
                }
            )

        return Response({"threads": thread_data})


@api_view(["POST"])
@jwt_required
def create_new_thread(request):
    user = request.user
    if not user.is_authenticated:
        return Response({"error": "User is not authenticated"}, status=403)

    response = get_openai_response(
        "こんにちは。面接に来た受験者に挨拶してください。自己紹介を促してください。"
    )
    new_thread = Thread.objects.create(creator=user, first_message=response)

    return Response(
        {"thread_id": str(new_thread.id), "response": response},
        status=status.HTTP_201_CREATED,
    )


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token["username"] = user.username
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


class DeleteThread(APIView):

    @method_decorator(jwt_required)
    def delete(self, request, thread_id):
        try:
            thread = Thread.objects.get(id=thread_id)
        except Thread.DoesNotExist:
            return Response(
                {"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # スレッドの作成者が現在のユーザーかどうかを確認
        if thread.creator != request.user:
            return Response(
                {"error": "You do not have permission to delete this thread"},
                status=status.HTTP_403_FORBIDDEN,
            )

        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 初めてのメッセージを返す
@api_view(["POST"])
@jwt_required
def get_first_message(request, thread_id):
    user = request.user
    if not user.is_authenticated:
        return Response({"error": "User is not authenticated"}, status=403)

    # thread_idがなければエラーを返す
    if not thread_id:
        return Response({"error": "thread_id is required"}, status=400)

    response = Thread.objects.filter(creator=user, id=thread_id).first().first_message

    return Response({"response": response})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @method_decorator(jwt_required)
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)
