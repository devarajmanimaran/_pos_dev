from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Max
from .models import POOrderHeader, Supplier, StoreDetails
from django.shortcuts import get_object_or_404
from .models import Product, ProductSupplierCost, POOrderLines
from django.db import connection
from django.utils import timezone
from django.db import transaction
import json

def purchase_order_list(request):
    # Get all purchase orders with supplier details
    po_orders = POOrderHeader.objects.select_related('supplier').all()

    # Handle search by PO number
    search_query = request.GET.get('search', '')  # Default to empty string instead of None
    if search_query:
        po_orders = po_orders.filter(po_number__icontains=search_query)

    # Handle filter by status
    status_filter = request.GET.get('status', 'All')  # Default to 'All' instead of None
    if status_filter and status_filter != 'All':
        po_orders = po_orders.filter(status=status_filter)

    return render(request, 'purchase_order/purchase_order.html', {
        'orders': po_orders,
        'search_query': search_query,  # Now passes empty string by default
        'status_filter': status_filter
    })

def add_po(request):
    # Generate the next PO number
    last_po = POOrderHeader.objects.aggregate(Max('po_number'))
    last_po_number = last_po['po_number__max']
    if last_po_number:
        next_po_number = f"PO-{int(last_po_number.split('-')[1]) + 1}"
    else:
        next_po_number = "PO-20231023"  # Default starting PO number

    # Fetch all suppliers and stores
    suppliers = Supplier.objects.all()
    stores = StoreDetails.objects.all()

    # Fetch the "My Store" record
    my_store = StoreDetails.objects.filter(my_store='Yes').first()

    return render(request, 'purchase_order/add_po.html', {
        'next_po_number': next_po_number,
        'suppliers': suppliers,
        'stores': stores,
        'my_store': my_store,
    })

def get_products(request):
    supplier_id = request.GET.get('supplier_id')
    if not supplier_id:
        return JsonResponse({'error': 'Supplier ID is required'}, status=400)

    # Fetch product IDs supplied by the selected supplier
    product_ids = ProductSupplierCost.objects.filter(supplier_id=supplier_id).values_list('product_ID', flat=True)

    # Fetch product details for the filtered product IDs
    products = Product.objects.filter(product_id__in=product_ids).select_related('category_id')
    product_list = [
        {
            'product_id': product.product_id,
            'product_name': product.product_name,
            'product_description': product.product_description,
            'uom': product.uom,
            'category_name': product.category_id.category_name,
        }
        for product in products
    ]

    return JsonResponse(product_list, safe=False)

def get_supplier_products(request, supplier_id):
    try:
        # Use a raw query to ensure correct schema reference
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.product_id, p.product_name, p.product_description, 
                       p.uom, pc.category_name
                FROM product p
                JOIN product_supplier_cost psc ON p.product_id = psc.product_id
                JOIN product_category pc ON p.category_id = pc.category_id
                WHERE psc.supplier_id = %s
            """, [supplier_id])
            
            columns = [col[0] for col in cursor.description]
            products = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

            return JsonResponse({'products': products})
    except Exception as e:
        print(f"Error fetching products: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

def get_product_costs(request, product_id, supplier_id):
    try:
        # Updated SQL query with correct schema reference
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT unit_cost, tax 
                FROM product_supplier_cost 
                WHERE product_id = %s AND supplier_id = %s
            """, [product_id, supplier_id])
            
            row = cursor.fetchone()
            if row:
                return JsonResponse({
                    'unit_cost': float(row[0]),
                    'tax': float(row[1])
                })
            return JsonResponse({
                'unit_cost': 0.00,
                'tax': 0.00
            })
    except Exception as e:
        print(f"Error in get_product_costs: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

def save_purchase_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        
        with transaction.atomic():
            # Get the next available po_header_id
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(MAX(po_header_id), 0) + 1 
                    FROM po_order_headers
                """)
                next_header_id = cursor.fetchone()[0]

            # Create PO Header using raw SQL
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO po_order_headers (
                        po_header_id, po_number, supplier_id, order_date, 
                        expected_delivery_date, total_order_value, status,
                        created_by, created_date, notes, reference_number,
                        shipped_by, shippment_reference
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING po_header_id
                """, [
                    next_header_id,
                    data['po_number'],
                    data['supplier_id'],
                    data['order_date'],
                    data['expected_delivery_date'],
                    data['total_order_value'],
                    'Open',
                    1,  # created_by
                    timezone.now(),
                    data['notes'] or 'None',
                    data.get('reference_number', 0),  # default to 0 if not provided
                    'None',  # shipped_by
                    'None'   # shippment_reference
                ])
                
                po_header_id = cursor.fetchone()[0]

            # Create PO Lines using raw SQL with explicit product_id handling
            for idx, product in enumerate(data['products'], 1):
                if not product.get('product_id'):
                    raise ValueError(f"Missing product_id for product: {product.get('product_name')}")
                
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO po_order_lines (
                            po_line_num, po_header_id, po_number, product_id,
                            product_name, priority, quantity_ordered, uom,
                            unit_price, total_price, status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, [
                        float(idx),
                        po_header_id,
                        data['po_number'],
                        product['product_id'],  # This should now be properly populated
                        product['product_name'],
                        'None',
                        product['quantity'],
                        product['uom'],
                        product['unit_cost'],
                        product['subtotal'],
                        'Open'
                    ])

        return JsonResponse({'success': True, 'po_number': data['po_number']})
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)
    except Exception as e:
        print(f"Error saving purchase order: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)