from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_request, name='create_request'),
    path('api/state/', views.requests_api_state, name='requests_api_state'),
    path('my/', views.my_requests, name='my_requests'),
    path('tv/<str:tv_secret>/', views.tv_board, name='tv_board'),
    path('tech/', views.tech_dashboard, name='tech_dashboard'),
    path('tech/update/', views.tech_update_request, name='tech_update_request'),
    path('analytics/', views.analytics, name='analytics'),
]