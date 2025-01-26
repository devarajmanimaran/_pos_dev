from django.shortcuts import render

def homepage(request):
    return render(request, 'store/index.html')
