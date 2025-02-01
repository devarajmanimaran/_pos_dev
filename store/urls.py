from django.urls import path
from . import views
from .views import get_po_details

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('inbound-check/', views.inbound_check, name='inbound_check'),
    path('po-details/<str:po_id>/', get_po_details, name='po-details'),  # Change <int:po_id> to <str:po_id>
]




