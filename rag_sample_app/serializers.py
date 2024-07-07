from rest_framework import serializers
from .models import Document
from .models import ChatHistory

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'

class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'thread_id', 'user_input', 'ai_response', 'timestamp']