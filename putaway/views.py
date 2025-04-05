from django.shortcuts import render
from django.http import JsonResponse
from .models import PutawayIntransist, Product, Location

def putaway_home(request):
    # Change to filter only pending items
    putaway_items = PutawayIntransist.objects.filter(status='Pending')
    product_ids = [item.product_id for item in putaway_items]
    products = {p.product_id: p for p in Product.objects.filter(product_id__in=product_ids)}
    
    # Get all locations for dropdown
    locations = Location.objects.all().values('location_id', 'location_name')
    
    # Attach products to putaway items
    for item in putaway_items:
        item._product = products.get(item.product_id)
    
    return render(request, 'putaway/home.html', {
        'putaway_items': putaway_items,
        'locations': locations
    })

def update_putaway(request, putaway_id):
    if request.method == 'POST':
        try:
            location_name = request.POST.get('location_name')
            if not location_name:
                return JsonResponse({'status': 'error', 'message': 'Please select a valid location code'})
            
            putaway = PutawayIntransist.objects.get(putaway_id=putaway_id)
            putaway.location_name = location_name
            putaway.status = 'Completed'
            putaway.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
