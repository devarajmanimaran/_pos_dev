from django.urls import path
from .views import bill_value,billing_home   # Import your views

urlpatterns = [
     path('', billing_home, name='billing_home'),
     path('form/', bill_value, name="billing_form"),
     path('bill/', bill_value, name='bill_value'),
     
]
