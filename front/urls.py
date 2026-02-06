from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='front-index'),
    path('user/<uuid:user_id>/', views.user_chat, name='front-user-chat'),
]
