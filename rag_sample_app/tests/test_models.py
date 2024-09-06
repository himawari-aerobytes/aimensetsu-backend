from django.test import TestCase
from rag_sample_app.models import Thread
import uuid  # uuidモジュールをインポート
from django.contrib.auth import get_user_model

class ThreadModelTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="test@example.com",password="password123")
      
    def test_uuid_generation(self):
        thread = Thread.objects.create(creator=self.user)
        self.assertIsInstance(thread.id,uuid.UUID)

     