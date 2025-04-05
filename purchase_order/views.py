from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Max
from .models import POOrderHeader, Supplier, StoreDetails
from django.shortcuts import get_object_or_404
from .models import Product, ProductSupplierCost, POOrderLines, PODrafts
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

    # Also fetch drafts
    drafts = PODrafts.objects.all()

    return render(request, 'purchase_order/purchase_order.html', {
        'orders': po_orders,
        'drafts': drafts,
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
                        shipped_by, shippment_preference
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

def save_draft(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        
        with transaction.atomic():
            draft = PODrafts.objects.create(
                # Supplier details
                supplier_name=data['supplier_name'],
                supplier_address=data['supplier_address'],
                supplier_city=data['supplier_city'],
                supplier_region=data['supplier_region'],
                supplier_phone_number=data['supplier_phone'],
                supplier_payment_terms=data['supplier_payment_terms'],
                
                # Store details
                store_name=data['store_name'],
                store_address=data['store_address'],
                store_city=data['store_city'],
                store_region=data['store_region'],
                store_phone_number=data['store_phone'],
                
                # Order details
                reference_number=data.get('reference_number'),
                ordered_date=data.get('ordered_date'),
                expected_delivery_date=data.get('expected_delivery_date'),
                shipped_by=data.get('shipped_by', 'None'),
                shippment_preference=data.get('shippment_preference', 'None'),
                notes=data.get('notes', 'None'),
                
                # Product and cost details
                product_details=data['product_details'],
                cost_summary=data['cost_summary'],
                shipping_cost=data.get('shipping_cost', 0),
                discount=data.get('discount', 0),
                other_adjustments=data.get('other_adjustments', 0),
                total_amount=data['total_amount']
            )

        return JsonResponse({'success': True, 'draft_id': draft.draft_id})
    except Exception as e:
        print(f"Error saving draft: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

def load_draft(request, draft_id):
    try:
        draft = PODrafts.objects.get(draft_id=draft_id)
        
        # Format dates for JavaScript
        ordered_date = draft.ordered_date.strftime('%Y-%m-%d') if draft.ordered_date else ''
        expected_delivery_date = draft.expected_delivery_date.strftime('%Y-%m-%d') if draft.expected_delivery_date else ''
        
        # Fetch all suppliers and stores for the form
        suppliers = Supplier.objects.all()
        stores = StoreDetails.objects.all()
        my_store = StoreDetails.objects.filter(my_store='Yes').first()

        # Get the next PO number
        last_po = POOrderHeader.objects.aggregate(Max('po_number'))
        last_po_number = last_po['po_number__max']
        next_po_number = f"PO-{int(last_po_number.split('-')[1]) + 1}" if last_po_number else "PO-20231023"

        # Convert Decimal objects to float for JSON serialization
        draft_data = {
            'draft_id': draft.draft_id,
            'supplier_name': draft.supplier_name,
            'supplier_address': draft.supplier_address,
            'supplier_city': draft.supplier_city,
            'supplier_region': draft.supplier_region,
            'supplier_phone': draft.supplier_phone_number,
            'supplier_payment_terms': draft.supplier_payment_terms,
            'store_name': draft.store_name,
            'store_address': draft.store_address,
            'store_city': draft.store_city,
            'store_region': draft.store_region,
            'store_phone': draft.store_phone_number,
            'reference_number': draft.reference_number,
            'ordered_date': ordered_date,
            'expected_delivery_date': expected_delivery_date,
            'shipped_by': draft.shipped_by,
            'shipment_preference': draft.shippment_preference,
            'notes': draft.notes,
            'product_details': draft.product_details,
            'cost_summary': draft.cost_summary,
            'shipping_cost': float(draft.shipping_cost),
            'discount': float(draft.discount),
            'other_adjustments': float(draft.other_adjustments),
            'total_amount': float(draft.total_amount)
        }

        context = {
            'next_po_number': next_po_number,
            'suppliers': suppliers,
            'stores': stores,
            'my_store': my_store,
            'draft_data': draft_data,
        }

        return render(request, 'purchase_order/add_po.html', context)
    except PODrafts.DoesNotExist:
        return JsonResponse({'error': 'Draft not found'}, status=404)

def edit_draft(request, draft_id):
    print("====== DEBUG: edit_draft called ======")
    print(f"Draft ID: {draft_id}")
    try:
        draft = PODrafts.objects.get(draft_id=draft_id)
        print(f"Found draft: {draft}")
        print(f"Draft data:")
        print(f"Supplier Name: {draft.supplier_name}")
        print(f"Product Details: {draft.product_details}")
        print(f"Cost Summary: {draft.cost_summary}")
        
        # Format dates for template
        ordered_date = draft.ordered_date.strftime('%Y-%m-%d') if draft.ordered_date else ''
        expected_delivery_date = draft.expected_delivery_date.strftime('%Y-%m-%d') if draft.expected_delivery_date else ''
        
        # Get lists for dropdowns
        suppliers = Supplier.objects.all()
        stores = StoreDetails.objects.all()
        my_store = StoreDetails.objects.filter(my_store='Yes').first()

        context = {
            'draft': draft,
            'ordered_date': ordered_date,
            'expected_delivery_date': expected_delivery_date,
            'suppliers': suppliers,
            'stores': stores,
            'my_store': my_store
        }
        
        print(f"Context being sent to template: {context}")
        return render(request, 'purchase_order/edit_draft.html', context)
    except PODrafts.DoesNotExist as e:
        print(f"Draft not found error: {e}")
        return JsonResponse({'error': 'Draft not found'}, status=404)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return JsonResponse({'error': str(e)}, status=500)