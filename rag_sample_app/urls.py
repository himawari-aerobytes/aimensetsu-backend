from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AllThreads,
    ChatHistoryListCreate,
    DeleteThread,
    DocumentList,
    LogoutView,
    MyTokenObtainPairView,
    OpenAIResponse,
    RegisterUser,
    ThreadSummary,
    create_new_thread,
    get_first_message,
)

urlpatterns = [
    path("documents/", DocumentList.as_view(), name="document-list"),
    path("openai/", OpenAIResponse.as_view(), name="openai-response"),
    path(
        "chat-history/",
        ChatHistoryListCreate.as_view(),
        name="chat-history-list-create",
    ),
    path("new-thread/", create_new_thread, name="new-thread"),
    path(
        "thread-summary/<str:thread_id>/",
        ThreadSummary.as_view(),
        name="thread_summary",
    ),
    path("all-threads/", AllThreads.as_view(), name="all_threads"),
    path("token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegisterUser.as_view(), name="register"),
    path(
        "delete-thread/<uuid:thread_id>/", DeleteThread.as_view(), name="delete-thread"
    ),
    path(
        "first-message/<uuid:thread_id>/", get_first_message, name="get-first-message"
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
