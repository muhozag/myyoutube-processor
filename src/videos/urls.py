from django.urls import path
from . import views

urlpatterns = [
    path('', views.VideoListView.as_view(), name='video_list'),
    path('<int:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('submit/', views.VideoCreateView.as_view(), name='video_submit'),
    path('<int:pk>/process/', views.process_video, name='process_video'),
    path('<int:pk>/status/', views.video_status, name='video_status'),
    path('<int:pk>/generate-summary/', views.generate_transcript_summary, name='generate_summary'),
]