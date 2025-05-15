from django.urls import path
from . import views

urlpatterns = [
    path('', views.custom_admin_view),  # 👈 Root URL shows admin page
    path('custom-admin/', views.custom_admin_view, name='custom_admin'),
    path('delete-face/<int:face_id>/', views.delete_face, name='delete_face'),
    path('logs/', views.view_logs, name='view_logs'),

    # 🔹 Recognition system routes
    path('start-basic/', views.start_basic_recognition, name='start_basic'),
    path('start-faiss/', views.start_faiss_recognition, name='start_faiss'),

    # New video feed route
    path('video-feed/', views.video_feed, name='video_feed'),
]
