from django.urls import path
from .views import supplier_home, delete_supplier, add_supplier, edit_supplier

urlpatterns = [
    path('', supplier_home, name='supplier_home'),
    path('delete/<str:supplier_id>/', delete_supplier, name='delete_supplier'),
    path('add/', add_supplier, name='add_supplier'),
    path('edit/<str:supplier_id>/', edit_supplier, name='edit_supplier'),
]
