from django.urls import path
from . import views
from . import views_ai

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("api/ai/chat/", views_ai.ai_chat_api, name="ai-chat-api"),
    path("mortgages/applications/<int:pk>/ai-underwrite/", views_ai.ai_underwrite_api, name="ai-underwrite-api"),
    path("mortgages/applications/<int:pk>/save-ai-notes/", views_ai.ai_save_notes_api, name="ai-save-notes-api"),
]
