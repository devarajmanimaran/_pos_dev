from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Supplier, GeoLocation
import uuid

@ensure_csrf_cookie
def supplier_home(request):
    suppliers = Supplier.objects.all()
    regions = Supplier.objects.values_list('region', flat=True).distinct().order_by('region')
    cities = Supplier.objects.values_list('city', flat=True).distinct().order_by('city')
    return render(request, 'supplier/supplier.html', {
        'suppliers': suppliers,
        'regions': regions,
        'cities': cities
    })

@require_http_methods(["POST"])
def delete_supplier(request, supplier_id):
    try:
        supplier = Supplier.objects.get(supplier_id=supplier_id)
        supplier.delete()
        return JsonResponse({'status': 'success'})
    except Supplier.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Supplier with ID {supplier_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def add_supplier(request):
    if request.method == 'POST':
        # Generate unique supplier_id
        supplier_id = str(uuid.uuid4())
        
        # Create new supplier
        Supplier.objects.create(
            supplier_id=supplier_id,
            supplier_name=request.POST.get('name'),
            landline_number=request.POST.get('landline_number'),
            phone_number=request.POST.get('phone_number'),
            email=request.POST.get('email'),
            contact_person=request.POST.get('contact_person'),
            address=request.POST.get('address'),
            region=request.POST.get('region'),
            city=request.POST.get('city'),
            payment_terms=request.POST.get('payment_terms'),
            is_active='Active'
        )
        return redirect('supplier_home')

    # Get regions and cities with their relationships
    locations = GeoLocation.objects.all()
    region_city_map = {}
    for loc in locations:
        if loc.state not in region_city_map:
            region_city_map[loc.state] = []
        region_city_map[loc.state].append(loc.city)

    return render(request, 'supplier/add_supplier.html', {
        'region_city_map': region_city_map,
        'payment_terms_choices': ['Net 30', 'Net 45', 'Net 60', 'Immediate']
    })

def edit_supplier(request, supplier_id):
    supplier = Supplier.objects.get(supplier_id=supplier_id)
    
    if request.method == 'POST':
        # Update supplier with new data
        supplier.supplier_name = request.POST.get('name')
        supplier.landline_number = request.POST.get('landline_number')
        supplier.phone_number = request.POST.get('phone_number')
        supplier.email = request.POST.get('email')
        supplier.contact_person = request.POST.get('contact_person')
        supplier.address = request.POST.get('address')
        supplier.region = request.POST.get('region')
        supplier.city = request.POST.get('city')
        supplier.payment_terms = request.POST.get('payment_terms')
        supplier.save()
        return redirect('supplier_home')

    # Get locations for dropdowns
    locations = GeoLocation.objects.all()
    region_city_map = {}
    for loc in locations:
        if loc.state not in region_city_map:
            region_city_map[loc.state] = []
        region_city_map[loc.state].append(loc.city)

    return render(request, 'supplier/edit_supplier.html', {
        'supplier': supplier,
        'region_city_map': region_city_map,
        'payment_terms_choices': ['Net 30', 'Net 45', 'Net 60', 'Immediate']
    })