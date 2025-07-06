from django.urls import path
from . import views

urlpatterns = [
    path('deleteuser/', views.delete_user,
         name='delete_user'),
]
