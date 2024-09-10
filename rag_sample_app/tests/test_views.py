from functools import wraps
from unittest import mock
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from rag_sample_app.models import Document, Thread


# JWT 認証用デコレータモック
def _mock_jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# jwt_requiredを書き換えるために、Viewsを読み込む前にmock化をする
mock.patch("rag_sample_app.utils.jwt_required", _mock_jwt_required).start()
from rag_sample_app.views import (
    generate_and_save_summary,
    get_openai_response,
    limit_string_length,
)


class APITestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser", email="test@example.com")
        self.client.force_authenticate(user=self.user)


class ChatHistoryListCreateTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.thread = Thread.objects.create(creator=self.user)

    def test_get_chat_history(self):
        url = reverse("chat-history-list-create")
        response = self.client.get(url, {"thread_id": self.thread.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_chat_history(self):
        url = reverse("chat-history-list-create")
        data = {
            "thread_id": self.thread.id,
            "message": "Hello world",
            "sender": self.user.username,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class DocumentListTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.document = Document.objects.create(content="Doc Content")

    def test_get_documents(self):
        url = reverse("document-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class OpenAIResponseTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.thread = Thread.objects.create(creator=self.user)

    @patch("requests.get")
    @patch("openai.chat.completions.create")
    def test_post_openai_response(self, mock_openai, mock_requests):
        mock_requests.return_value.status_code = 200
        mock_requests.return_value.json.return_value = {
            "value": [{"content": "doc content"}]
        }
        mock_openai.return_value.choices[0].message.content = "AI response"

        url = reverse("openai-response")
        data = {"search_word": "search", "thread_id": self.thread.id}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("response", response.data)


class ThreadSummaryTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.thread = Thread.objects.create(creator=self.user)

    @patch("rag_sample_app.views.generate_and_save_summary")
    def test_get_thread_summary(self, mock_generate_summary):
        mock_generate_summary.return_value = "Generated summary"
        url = reverse("thread-summary", args=[self.thread.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)


class CreateNewThreadTest(APITestBase):
    @patch("rag_sample_app.views.get_openai_response")
    def test_create_new_thread(self, mock_openai_response):
        mock_openai_response.return_value = "Initial response"
        url = reverse("new-thread")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("thread_id", response.data)


class DeleteThreadTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.thread = Thread.objects.create(creator=self.user)

    def test_delete_thread(self):
        url = reverse("delete-thread", args=[self.thread.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class LogoutViewTest(APITestBase):
    @patch("rag_sample_app.views.RefreshToken")
    def test_logout_view(self, mock_refresh_token):

        url = reverse("logout")
        response = self.client.post(url, {"refresh_token": "dummy-token"})

        # Mock呼び出し確認
        # RefreshToken が 1 回だけ呼ばれたことを確認し、 'dummy-token' が渡されたことを確認
        mock_refresh_token.assert_called_once_with("dummy-token")
        mock_refresh_token.return_value.blacklist.assert_called_once()
        # レスポンス確認
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)


class GetFirstMessageTest(APITestBase):
    def setUp(self):
        super().setUp()
        self.thread = Thread.objects.create(creator=self.user, first_message="Hello!")

    def test_get_first_message(self):
        url = reverse("get-first-message", args=[self.thread.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("response", response.data)


class LimitStringLengthTest(SimpleTestCase):

    def test_string_exceeds_max_length(self):
        # max_length を超える場合
        input_string = "This is a long string."
        max_length = 10
        expected_output = "This is a "  # 10文字目まで切り詰められる
        result = limit_string_length(input_string, max_length)
        self.assertEqual(result, expected_output)

    def test_string_equal_to_max_length(self):
        # 文字列がちょうど max_length の場合
        input_string = "1234567890"
        max_length = 10
        expected_output = "1234567890"  # そのまま返される
        result = limit_string_length(input_string, max_length)
        self.assertEqual(result, expected_output)

    def test_string_less_than_max_length(self):
        # 文字列が max_length より短い場合
        input_string = "short"
        max_length = 10
        expected_output = "short"  # そのまま返される
        result = limit_string_length(input_string, max_length)
        self.assertEqual(result, expected_output)

    def test_empty_string(self):
        # 空文字列のテスト
        input_string = ""
        max_length = 10
        expected_output = ""  # 空文字列のまま返される
        result = limit_string_length(input_string, max_length)
        self.assertEqual(result, expected_output)


class GenerateAndSaveSummaryTest(TestCase):

    @patch("rag_sample_app.views.ChatHistory.objects.filter")
    def test_generate_and_save_summary(self, mock_filter):
        # モックオブジェクトの設定
        thread = MagicMock()  # モックの Thread インスタンスを作成
        mock_chat_history = [
            MagicMock(message="Hello world"),
            MagicMock(message="How are you?"),
            MagicMock(message="Goodbye"),
        ]

        # filter の返り値に exclude, order_by, reverse メソッドチェーンを適用する
        mock_filter.return_value.exclude.return_value.order_by.return_value.reverse.return_value = (
            mock_chat_history
        )

        # 関数の呼び出し
        result = generate_and_save_summary(thread)

        # 期待される結果
        expected_summary = "Hello world\nHow are you?\nGoodbye"

        # アサーション
        self.assertEqual(result, expected_summary)
        self.assertEqual(thread.summary, expected_summary)
        thread.save.assert_called_once()  # thread.save() が1回呼ばれたことを確認

        # モックが正しく呼ばれたことを確認
        mock_filter.assert_called_once_with(thread_id=thread)
        mock_filter.return_value.exclude.assert_called_once_with(sender="AI")
        mock_filter.return_value.exclude.return_value.order_by.assert_called_once_with(
            "timestamp"
        )
        mock_filter.return_value.exclude.return_value.order_by.return_value.reverse.assert_called_once()


class GetOpenAIResponseTest(SimpleTestCase):

    @patch("rag_sample_app.views.openai.chat.completions.create")
    def test_get_openai_response(self, mock_openai_create):
        # モックのレスポンスを設定
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "AI response"
        mock_openai_create.return_value = mock_response

        # テスト用のメッセージを送信
        user_message = "こんにちは、自己紹介をしてください。"
        result = get_openai_response(user_message)

        # 期待されるリクエスト内容
        expected_messages = [
            {
                "role": "system",
                "content": "あなたは、面接官の高橋です。面接を受ける人に対して、適切な質問をしてください。面接は１対１です。最初は自己紹介から始めましょう。",
            },
            {"role": "user", "content": user_message},
        ]

        # モックの呼び出しを検証
        mock_openai_create.assert_called_once_with(
            model="gpt-3.5-turbo", messages=expected_messages
        )

        # 関数の結果がモックされたレスポンスと一致するか確認
        self.assertEqual(result, "AI response")
