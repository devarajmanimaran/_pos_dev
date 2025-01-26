from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('inbound-check/', views.inbound_check, name='inbound_check'),
]
