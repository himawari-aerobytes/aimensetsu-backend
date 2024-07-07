from django.db import models
from django.apps import AppConfig

class Document(models.Model):
    content = models.TextField()

    def __str__(self):
        return self.content[:50]

class RagSampleAppConfig(AppConfig):
    name = 'rag_sample_app'

class ChatHistory(models.Model):
    thread_id = models.CharField(max_length=100,default='default_thread_id')  # 追加
    # thread_idのデフォルト値を設定

    user_input = models.TextField()
    ai_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread {self.thread_id} - {self.user_input[:50]}"
