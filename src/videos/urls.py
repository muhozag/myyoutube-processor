from django.urls import path
from . import views

urlpatterns = [
    path('', views.VideoListView.as_view(), name='video_list'),
    path('<int:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('submit/', views.VideoCreateView.as_view(), name='video_submit'),
    path('<int:pk>/process/', views.process_video, name='process_video'),
    # Adding an alternative URL pattern that matches exactly the error message format
    path('<int:video_id>/process/', views.process_video_by_id, name='process_video_by_id'),
    path('<int:pk>/status/', views.video_status, name='video_status'),
    path('<int:pk>/generate-summary/', views.generate_transcript_summary, name='generate_summary'),
    path('<int:pk>/delete/', views.delete_video, name='delete_video'),
]