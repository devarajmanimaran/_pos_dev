from django.urls import path
from .views import material_inward, get_po_details  # Ensure correct import

app_name = 'material_inward'  # Add this line

urlpatterns = [
    path('', material_inward, name='material_inward'),
    path('po-details/<str:po_id>/', get_po_details, name='po-details'),
]
