from django.urls import path

from . import views

app_name='links'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),    
    path('<int:pk>/', views.ShortenedLinkView.as_view(), name='shortened_link'),    
    path('<str:code>/', views.redirectView, name='redirect'),    
]
