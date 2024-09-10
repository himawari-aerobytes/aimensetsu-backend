from functools import wraps
from unittest import mock
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from rag_sample_app.models import Document, Thread


def _mock_jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return _wrapped_view


mock.patch("rag_sample_app.utils.jwt_required", _mock_jwt_required).start()


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
