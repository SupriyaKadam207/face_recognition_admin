from django.urls import path
from . import views

urlpatterns = [

    # Main Admin and Dashboard
    path('', views.custom_admin_view, name='home'),
    path('custom-admin/', views.custom_admin_view, name='custom_admin'),

    # Face Data Management
    path('delete-face/<int:face_id>/', views.delete_face, name='delete_face'),
    path('update-face/<int:face_id>/', views.update_face, name='update_face'),

    # Logs and User Logs
    path('logs/', views.view_logs, name='view_logs'),

    # Face Recognition System
    path('start-basic/', views.start_faiss_recognition, name='start_basic'),
    path('start-faiss/', views.start_faiss_recognition, name='start_faiss'),
    path('video-feed/', views.video_feed, name='video_feed'),

    # Attendance Management
    path('attendance/logs/', views.attendance_logs, name='attendance_logs'),
    path('attendance/summary/', views.attendance_summary, name='attendance_summary'),
    path('attendance/export/pdf/', views.export_attendance_pdf, name='export_attendance_pdf'),
    path('attendance/export/excel/', views.export_attendance_excel, name='export_attendance_excel'),
    path('attendance/logs/details/', views.attendance_log_details, name='attendance_log_details'),

    # 🏆 Leaderboard
    path('attendance/leaderboard/', views.attendance_leaderboard, name='attendance_leaderboard'),
]
