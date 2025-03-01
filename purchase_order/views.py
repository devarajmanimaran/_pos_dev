from django.shortcuts import render, redirect
from django.db.models import Max
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from .models import POOrderHeader, Product, ProductCategory, Supplier, ProductSupplierCost, POOrderLines
from .forms import POOrderHeaderForm
from django.db import connection, transaction

def get_category(request, product_id):
    try:
        product = Product.objects.get(product_id=product_id)
        category = ProductCategory.objects.get(category_id=product.category_id)
        return JsonResponse({'category_name': category.category_name})
    except (Product.DoesNotExist, ProductCategory.DoesNotExist):
        return JsonResponse({'error': 'Category not found'}, status=404)

def get_suppliers_for_product(request, product_id):
    try:
        print(f"Fetching suppliers for product: {product_id}")  # Debug log
        suppliers = Supplier.objects.filter(
            productsuppliercost__product_id=product_id
        ).distinct().values('supplier_id', 'supplier_name')
        print(f"Found suppliers: {list(suppliers)}")  # Debug log
        return JsonResponse({'suppliers': list(suppliers)})
    except Exception as e:
        print(f"Error in get_suppliers_for_product: {str(e)}")  # Debug log
        return JsonResponse({'error': str(e)}, status=400)

def get_products_for_supplier(request, supplier_id):
    try:
        print(f"Fetching products for supplier: {supplier_id}")
        # First try to get the raw SQL query for debugging
        query = Product.objects.filter(
            productsuppliercost__supplier_id=supplier_id
        ).distinct()
        print(f"SQL Query: {query.query}")  # Print the SQL query
        
        products = list(query.values('product_id', 'product_name'))
        print(f"Found products: {products}")
        
        if not products:
            print("No products found for this supplier")
            
        return JsonResponse({'products': products})
    except Exception as e:
        print(f"Error in get_products_for_supplier: {str(e)}")
        # Try alternative query
        try:
            print("Trying alternative query...")
            products = Product.objects.raw("""
                SELECT p.product_id, p.product_name 
                FROM product p 
                JOIN product_supplier_cost psc ON p.product_id = psc.product_id 
                WHERE psc.supplier_id = %s
            """, [supplier_id])
            
            product_list = [{'product_id': p.product_id, 'product_name': p.product_name} 
                          for p in products]
            print(f"Found products (alternative): {product_list}")
            return JsonResponse({'products': product_list})
        except Exception as e2:
            print(f"Alternative query also failed: {str(e2)}")
            return JsonResponse({'error': str(e)}, status=400)

def get_supplier_details(request, supplier_id):
    try:
        supplier = Supplier.objects.get(supplier_id=supplier_id)
        return JsonResponse({
            'address': supplier.address,
            'phone': supplier.phone_number,
            'payment_terms': supplier.payment_terms
        })
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)

def get_unit_cost(request, product_id, supplier_id):
    try:
        print(f"Fetching unit cost for product {product_id} and supplier {supplier_id}")
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT unit_cost 
                FROM product_supplier_cost
                WHERE product_id = %s AND supplier_id = %s
            """, [product_id, supplier_id])
            
            row = cursor.fetchone()
            if row:
                unit_cost = float(row[0])
                print(f"Found unit cost: {unit_cost}")
                return JsonResponse({'unit_cost': unit_cost})
            
        print("No unit cost found")
        return JsonResponse({'unit_cost': 0})
    except Exception as e:
        print(f"Error fetching unit cost: {str(e)}")
        return JsonResponse({'unit_cost': 0})

def add_po(request):
    try:
        # Generate the next PO number
        max_po_number = POOrderHeader.objects.aggregate(Max('po_number'))['po_number__max']
        if max_po_number:
            next_po_number = f"PO-{int(max_po_number.split('-')[1]) + 1}"
        else:
            next_po_number = "PO-20231015"  # Default starting PO number

        if request.method == 'POST':
            post_data = request.POST.copy()
            total_order_value = float(request.POST.get('total_value', 0))
            supplier_id = request.POST.get('supplier')
            priority = request.POST.get('priority')
            
            with transaction.atomic():
                # 1. Create PO Header
                po_header = POOrderHeader.objects.create(
                    po_number=post_data['po_number'],
                    supplier_id=supplier_id,
                    order_date=timezone.now(),
                    total_order_value=total_order_value,
                    status='Open',
                    created_by=1,
                    created_date=timezone.now()
                )

                # 2. Create PO Lines
                line_num = 1.0
                for key in request.POST:
                    if key.startswith('product-') and request.POST[key]:
                        index = key.split('-')[1]
                        product_id = request.POST[key]
                        quantity = int(request.POST.get(f'qty-{index}', 0))
                        unit_cost = float(request.POST.get(f'unit-cost-{index}', 0))
                        subtotal = float(request.POST.get(f'subtotal-{index}', 0))
                        
                        if quantity > 0:
                            product = Product.objects.get(product_id=product_id)
                            
                            POOrderLines.objects.create(
                                po_line_num=line_num,
                                po_header_id=po_header.po_header_id,  # Changed to use ID directly
                                po_number=post_data['po_number'],
                                product_id=product_id,  # Changed to use ID directly
                                product_name=product.product_name,
                                priority=priority,
                                quantity_ordered=quantity,
                                uom='pcs',
                                unit_price=unit_cost,
                                total_price=subtotal,
                                status='Open'
                            )
                            line_num += 0.1

                return redirect('purchase_order_list')
        
        # Rest of the view remains the same...
        else:
            initial_data = {
                'po_number': next_po_number,
                'order_date': timezone.now(),
                'total_order_value': 0.00
            }
            form = POOrderHeaderForm(initial=initial_data)

        # Fetch all products and suppliers for the form
        try:
            products = Product.objects.all()
        except:
            products = []  # Provide empty list if table doesn't exist

        context = {
            'form': form,
            'products': products,
            'suppliers': Supplier.objects.all(),  # Add this line
        }
        return render(request, 'purchase_order/add_po.html', context)

    except Exception as e:
        # Log the error and show a user-friendly message
        print(f"Error in add_po view: {str(e)}")
        context = {
            'error_message': "Unable to load the form. Please contact support."
        }
        return render(request, 'purchase_order/add_po.html', context)

from django.shortcuts import render
from .models import POOrderHeader

def purchase_order_list(request):
    # Get all purchase orders
    po_orders = POOrderHeader.objects.all()

    # Handle search by PO number
    search_query = request.GET.get('search')
    if search_query:
        po_orders = po_orders.filter(po_number__icontains=search_query)

    # Handle filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        po_orders = po_orders.filter(status=status_filter)

    return render(request, 'purchase_order/purchase_order.html', {'po_orders': po_orders})