from django.urls import path
from . import views
from django.urls import path, include
# from .views import get_po_details

urlpatterns = [
    path('', views.homepage, name='homepage'),
    # path('material-inward/', include('material_inward.urls', namespace='material_inward'))
]




