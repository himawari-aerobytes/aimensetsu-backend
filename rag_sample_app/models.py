from django.db import models
from django.apps import AppConfig
import uuid  # uuidモジュールをインポート
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractBaseUser

class Document(models.Model):
    content = models.TextField()

    def __str__(self):
        return self.content[:50]

class RagSampleAppConfig(AppConfig):
    name = 'rag_sample_app'

class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, null=True)  # 要約フィールドを追加
    creator = models.ForeignKey(User, on_delete=models.CASCADE)  # 作成者フィールドを追加
    first_message = models.TextField(blank=True, null=True)  # 初回メッセージフィールドを追加
class ChatHistory(models.Model):
    thread_id = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='chats')
    # thread_idのデフォルト値を設定
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sender = models.TextField()

    def __str__(self):
        return f"Thread {self.thread_id} - {self.message[:50]}"
    
class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    

