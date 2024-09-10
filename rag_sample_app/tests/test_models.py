import uuid  # uuidモジュールをインポート

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rag_sample_app.models import ChatHistory, Document, Thread, User


class ThreadModelTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test@example.com", password="password123"
        )

    def test_uuid_generation(self):
        thread = Thread.objects.create(creator=self.user)
        self.assertIsInstance(thread.id, uuid.UUID)

    def test_auto_now_add_for_created_at(self):
        thread = Thread.objects.create(creator=self.user)
        self.assertIsNotNone(thread.created_at)
        self.assertLessEqual(thread.created_at, timezone.now())

    def test_null_fields(self):
        thread = Thread.objects.create(creator=self.user)
        self.assertIsNone(thread.summary)
        self.assertIsNone(thread.first_message)

    def test_foreign_key_relation_with_user(self):
        thread = Thread.objects.create(creator=self.user)
        self.assertEqual(thread.creator.get_username(), "test@example.com")


class DocumentModelTest(TestCase):
    def test_str_method(self):
        doc = Document.objects.create(content="This is a test document.")
        self.assertEqual(str(doc), "This is a test document.")


class ChatHistoryModelTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test@example.com", password="password123"
        )
        self.thread = Thread.objects.create(creator=self.user)

    def test_message_creation(self):
        chat = ChatHistory.objects.create(
            thread_id=self.thread,
            message="Hello, this is a test message.",
            sender="User1",
        )
        self.assertEqual(chat.message, "Hello, this is a test message.")
        self.assertEqual(chat.sender, "User1")

    def test_timestamp_auto_now_add(self):
        chat = ChatHistory.objects.create(
            thread_id=self.thread, message="Another message", sender="User2"
        )
        self.assertIsNotNone(chat.timestamp)
        self.assertLessEqual(chat.timestamp, timezone.now())

    def test_foreign_key_relation_with_thread(self):
        chat = ChatHistory.objects.create(
            thread_id=self.thread, message="Thread relation test", sender="User1"
        )
        self.assertEqual(chat.thread_id, self.thread)

    def test_str_method(self):
        message_text = "Hello, this is a test message."
        chat = ChatHistory.objects.create(
            thread_id=self.thread, message=message_text, sender="User1"
        )
        # 期待される__str__の出力
        expected_output = f"Thread {self.thread.id} - {message_text[:50]}"
        # __str__ メソッドの出力を確認
        self.assertEqual(str(chat), expected_output)


class UserModelTest(TestCase):
    def test_create_user(self):
        user = get_user_model().objects.create_user(
            username="user1@example.com", password="password123"
        )
        self.assertEqual(user.username, "user1@example.com")
        self.assertTrue(user.check_password("password123"))

    def test_email_is_unique(self):
        user1 = get_user_model().objects.create_user(
            username="unique@example.com", password="password123"
        )
        with self.assertRaises(Exception):
            user2 = get_user_model().objects.create_user(
                username="unique@example.com", password="password456"
            )
