"""
Defines URL patterns for 'accounts' app.
"""
from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    # Include default auth urls.
    # This approach uses default Django routes and views.
    path('', include('django.contrib.auth.urls')),
    # Registration page.
    path('register/', views.register, name='register'),
    ]   

