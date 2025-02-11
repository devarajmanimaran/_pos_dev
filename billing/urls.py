from django.urls import path
from .views import bill_value,billing_home,save_bill   # Import your views
from . import views

urlpatterns = [
     path('', bill_value, name='bill_value'),
     path('form/', bill_value, name="billing_form"),
     path('bill/', bill_value, name='bill_value'),
<<<<<<< Updated upstream
     
]
=======
     path('get-customer/', views.get_customer, name='get_customer'),
     path('save-customer/', views.save_customer, name='save_customer'),
     path('save_bill/', views.save_bill, name='save_bill'),
]
>>>>>>> Stashed changes
