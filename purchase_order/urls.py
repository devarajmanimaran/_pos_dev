from django.urls import path
from . import views

print("Loading URL patterns...")  # Debug print

urlpatterns = [
    path('', views.purchase_order_list, name='purchase_order_list'),
    path('add-po/', views.add_po, name='add_po'),
    path('get-supplier-products/<str:supplier_id>/', views.get_supplier_products, name='get-supplier-products'),
    path('get-product-costs/<str:product_id>/<str:supplier_id>/', views.get_product_costs, name='get-product-costs'),
    path('save-purchase-order/', views.save_purchase_order, name='save-purchase-order'),
    path('save-draft/', views.save_draft, name='save-draft'),
    path('load-draft/<int:draft_id>/', views.load_draft, name='load-draft'),
    path('edit-draft/<int:draft_id>/', views.edit_draft, name='edit-draft'),
]