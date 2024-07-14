from django.db import models
from django.apps import AppConfig
import uuid  # uuidモジュールをインポート

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
class ChatHistory(models.Model):
    thread_id = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='chats')
    # thread_idのデフォルト値を設定

    user_input = models.TextField()
    ai_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread {self.thread_id} - {self.user_input[:50]}"
    

