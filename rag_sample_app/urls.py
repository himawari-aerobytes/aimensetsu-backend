from django.urls import path
from .views import DocumentList, OpenAIResponse, ChatHistoryListCreate,create_new_thread, ThreadSummary, AllThreads
from .views import create_new_thread

urlpatterns = [
    path('documents/', DocumentList.as_view(), name='document-list'),
    path('openai/', OpenAIResponse.as_view(), name='openai-response'),
    path('chat-history/', ChatHistoryListCreate.as_view(), name='chat-history-list-create'),
    path('new-thread/', create_new_thread, name='new-thread'),
    path('thread-summary/<str:thread_id>/', ThreadSummary.as_view(), name='thread_summary'),
    path('all-threads/', AllThreads.as_view(), name='all_threads'),

]