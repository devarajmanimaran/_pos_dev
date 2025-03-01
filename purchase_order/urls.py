from django.urls import path
from . import views

urlpatterns = [
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/add/', views.add_po, name='add_po'),
    path('get-category/<str:product_id>/', views.get_category, name='get_category'),
    path('get-suppliers/<str:product_id>/', views.get_suppliers_for_product, name='get-suppliers'),
    path('get-products/<str:supplier_id>/', views.get_products_for_supplier, name='get-products'),
    path('get-supplier-details/<str:supplier_id>/', views.get_supplier_details, name='get-supplier-details'),
    path('get-unit-cost/<str:product_id>/<str:supplier_id>/', views.get_unit_cost, name='get-unit-cost'),
]