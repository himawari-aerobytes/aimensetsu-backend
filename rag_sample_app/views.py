import datetime
import os
import random

import openai
import requests
from django.utils.decorators import method_decorator
from dotenv import load_dotenv
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatHistory, Document, Thread
from .serializers import ChatHistorySerializer, DocumentSerializer
from .utils import jwt_required  # utils.pyからデコレータをインポート


def load_environment():
    # 開発環境か本番環境かに応じてファイルを指定
    environment = os.getenv("ENV", "development")
    if environment == "production":
        load_dotenv(".env.production")
    else:
        load_dotenv(".env.development")


load_environment()

# 環境変数の取得
api_key = os.getenv("API_KEY")
search_service = os.getenv("SEARCH_SERVICE")
index = os.getenv("INDEX")
aoai_api_key = os.getenv("OPENAI_API_KEY")
aoai_service_name = os.getenv("OPENAI_RESOURCE_NAME")
aoai_deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME")
aoai_resource_name = os.environ.get("OPENAI_RESOURCE_NAME")
aoai_api_version = os.getenv("OPENAI_API_VERSION")
aoai_model = os.getenv("OPENAI_MODEL")
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


# 最新のユーザからのチャットを１行で取得する
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


# 3つの名前からランダムに選択する関数
def choose_random_name():
    names = ["高階", "渡海", "佐伯", "藤原", "西崎", "世良", "猫田"]
    return random.choice(names)


# 実行例
choose_random_name()


def get_openai_response(message):
    messages = [
        {
            "role": "system",
            "content": f"あなたは、面接官の{choose_random_name()}です。面接を受ける人に対して、適切な質問をしてください。面接は１対１です。最初は自己紹介から始めましょう。",
        }
    ]
    messages.append({"role": "user", "content": message})
    openai_response = openai.chat.completions.create(
        model=aoai_model, messages=messages
    )
    return openai_response.choices[0].message.content


class ChatHistoryList(generics.ListCreateAPIView):
    serializer_class = ChatHistorySerializer

    # dispatchメソッドにデコレータを適用
    @method_decorator(jwt_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        thread_id = self.request.query_params.get("thread_id")
        user = self.request.user

        try:
            thread = Thread.objects.get(creator=user, id=thread_id)
        except Thread.DoesNotExist:
            return None

        return ChatHistory.objects.filter(thread_id=thread)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset is None:
            return Response(
                {"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND
            )

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
            return Response(
                {"error": "search_word is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        thread_id = request.data.get("thread_id")  # thread_idを取得
        user = request.user
        if thread_id:
            try:
                thread = Thread.objects.get(creator=user, id=thread_id)
            except Thread.DoesNotExist:
                return Response(
                    {"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            thread = Thread.objects.create(creator=user)

        search_url = f"https://{search_service}.search.windows.net/indexes/{index}/docs"
        headers = {"Content-Type": "application/json", "api-key": api_key}
        params = {"api-version": "2021-04-30-Preview", "search": search_word}
        response = requests.get(search_url, headers=headers, params=params)

        if response.status_code == status.HTTP_200_OK:
            try:
                results = response.json()
            except requests.exceptions.JSONDecodeError as e:
                return Response(
                    {"error": "JSON decode error: " + str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
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
            model=aoai_model, messages=messages
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
        user = request.user
        try:
            thread = Thread.objects.get(creator=user, id=thread_id)
        except Thread.DoesNotExist:
            return Response(
                {"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not thread.summary:
            summary = generate_and_save_summary(thread)
        else:
            summary = thread.summary

        return Response({"summary": summary})


class AllThreads(APIView):

    @method_decorator(jwt_required)
    def get(self, request):
        user = request.user
        threads = Thread.objects.filter(creator=user).order_by("-created_at")
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
    response = get_openai_response(
        "こんにちは。面接に来た受験者に挨拶してください。自己紹介を促してください。"
    )
    new_thread = Thread.objects.create(creator=user, first_message=response)

    return Response(
        {"thread_id": str(new_thread.id), "response": response},
        status=status.HTTP_201_CREATED,
    )


class DeleteThread(APIView):

    @method_decorator(jwt_required)
    def delete(self, request, thread_id):
        user = request.user
        try:
            thread = Thread.objects.get(creator=user, id=thread_id)
        except Thread.DoesNotExist:
            return Response(
                {"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND
            )

        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 初めてのメッセージを返す
@api_view(["POST"])
@jwt_required
def get_first_message(request, thread_id):
    user = request.user
    # ユーザIDで絞り込み
    response = Thread.objects.filter(creator=user, id=thread_id).first()

    if response is None:
        return Response(
            {"error": "the first message was not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    response = response.first_message
    return Response({"response": response})
