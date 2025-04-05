from django.urls import path
from .views import putaway_home, update_putaway

urlpatterns = [
    path('', putaway_home, name='putaway_home'),
    path('update/<int:putaway_id>/', update_putaway, name='update_putaway'),
]
