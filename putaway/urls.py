from django.urls import path
from .views import putaway_home  # Import your views

urlpatterns = [
    path('', putaway_home, name='putaway_home'),
]
