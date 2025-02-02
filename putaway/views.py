from django.shortcuts import render

def putaway_home(request):
    return render(request, 'putaway/home.html')
