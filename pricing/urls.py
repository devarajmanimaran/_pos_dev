from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('', views.price_history, name='pricing_index'),
    path('history/', views.price_history, name='price_history'),
    path('update/', views.update_price, name='update_price'),
    path('excel/download/', views.download_excel, name='download_excel'),
    path('excel/upload/', views.upload_excel, name='upload_excel'),
]