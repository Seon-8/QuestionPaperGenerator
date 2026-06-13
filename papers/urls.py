from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("ajax/load-topics/", views.load_topics, name="load_topics"),

    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/add/", views.add_subject, name="add_subject"),

    path("topics/add/", views.add_topic, name="add_topic"),

    path("questions/", views.question_list, name="question_list"),
    path("questions/add/", views.add_question, name="add_question"),

    path("papers/", views.paper_list, name="paper_list"),
    path("papers/generate/", views.generate_paper, name="generate_paper"),
    path("papers/<int:paper_id>/", views.paper_preview, name="paper_preview"),
    path("papers/<int:paper_id>/download/", views.download_paper_pdf, name="download_paper_pdf"),
    path("papers/<int:paper_id>/answer-key/", views.download_answer_key_pdf, name="download_answer_key_pdf"),

    path("questions/ai-generate/", views.ai_generate_questions, name="ai_generate_questions"),
]