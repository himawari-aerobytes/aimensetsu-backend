from django.urls import path

from .views import (
    AllThreads,
    ChatHistoryList,
    DeleteThread,
    DocumentList,
    OpenAIResponse,
    ThreadSummary,
    create_new_thread,
    get_first_message,
)

urlpatterns = [
    path("documents/", DocumentList.as_view(), name="document-list"),
    path("openai/", OpenAIResponse.as_view(), name="openai-response"),
    path(
        "chat-history/",
        ChatHistoryList.as_view(),
        name="chat-history-list",
    ),
    path("new-thread/", create_new_thread, name="new-thread"),
    path(
        "thread-summary/<str:thread_id>/",
        ThreadSummary.as_view(),
        name="thread-summary",
    ),
    path("all-threads/", AllThreads.as_view(), name="all-threads"),
    path(
        "delete-thread/<uuid:thread_id>/", DeleteThread.as_view(), name="delete-thread"
    ),
    path(
        "first-message/<uuid:thread_id>/", get_first_message, name="get-first-message"
    ),
]
