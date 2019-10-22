from django.urls import path
from . import views

urlpatterns = [
    path('', views.hi, name = 'home_page'),
    path('getFiles/', views.getFiles, name='getFiles'),
]