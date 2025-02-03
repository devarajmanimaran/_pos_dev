from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
# from .models import POOrderLines  # Ensure this matches your model


def homepage(request):
    return render(request, 'store/index.html')
