from django.contrib.auth import get_user_model
from django.test import TestCase

from rag_sample_app.models import ChatHistory, Document, Thread  # 適切なモデルをインポート
from rag_sample_app.serializers import (
    ChatHistorySerializer,
    DocumentSerializer,
    UserSerializer,
)

User = get_user_model()


class DocumentSerializerTest(TestCase):

    def setUp(self):
        # テスト用のDocumentインスタンスを作成
        self.document = Document.objects.create(
            content="This is a test document content"
        )

    def test_document_serializer(self):
        # シリアライズされたデータが正しいかを確認
        serializer = DocumentSerializer(self.document)
        data = serializer.data
        self.assertEqual(data["content"], self.document.content)


class ChatHistorySerializerTest(TestCase):

    def setUp(self):
        # テスト用のUserインスタンスを作成
        self.user = User.objects.create(username="test", password="pass")
        # テスト用のThreadインスタンスを作成
        self.thread = Thread.objects.create(creator=self.user)
        # テスト用のChatHistoryインスタンスを作成
        self.chat_history = ChatHistory.objects.create(
            thread_id=self.thread,
            message="This is a test message",
            sender="Test Sender",
        )

    def test_chat_history_serializer(self):
        # シリアライズされたデータが正しいかを確認
        serializer = ChatHistorySerializer(self.chat_history)
        data = serializer.data
        self.assertEqual(data["thread_id"], self.chat_history.thread_id.id)
        self.assertEqual(data["message"], self.chat_history.message)
        self.assertEqual(data["sender"], self.chat_history.sender)
        self.assertIsNotNone(
            data["timestamp"]
        )  # timestamp がシリアライズされているか確認


class UserSerializerTest(TestCase):

    def setUp(self):
        self.user_data = {"username": "testuser", "password": "securepassword"}

    def test_user_serializer_fields(self):
        # フィールドが正しくシリアライズ/デシリアライズされるかを確認
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        self.assertIn("username", serializer.validated_data)
        self.assertIn("password", serializer.validated_data)

    def test_password_write_only(self):
        # パスワードがシリアライズされないことを確認
        user = User.objects.create_user(**self.user_data)
        serializer = UserSerializer(user)
        self.assertNotIn("password", serializer.data)

    def test_create_user(self):
        # ユーザーが正しく作成されるかを確認
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.username, self.user_data["username"])
        # パスワードがハッシュ化されているかを確認
        self.assertTrue(user.check_password(self.user_data["password"]))
