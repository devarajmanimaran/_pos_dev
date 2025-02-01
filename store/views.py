from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import POOrderLines  # Ensure this matches your model


def homepage(request):
    return render(request, 'store/index.html')


def inbound_check(request):
    # Query data from PostgreSQL table "pos_dev"."PO_ORDER_LINES"
    query = """
    select po_number
        po_header_id,
        order_date,
        status,
        supplier_id
        from "pos_dev"."Po_Order_Headers"
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Prepare the data as a list of dictionaries
    columns = [
        'PO_NO', 'CREATED_DATE', 'STATUS', 'SUPPLIER_ID'
    ]
    data = [dict(zip(columns, row)) for row in rows]

    return render(request, 'store/inbound_check.html', {'data': data})

def get_po_details(request, po_id):
    order_lines = POOrderLines.objects.filter(po_number=po_id)
    
    if not order_lines.exists():
        return JsonResponse({"error": "PO not found"}, status=404)
    
    data = [
        {
            "po_line_id": order_line.po_line_id,
            "po_number": order_line.po_number,
            "product_name": order_line.product_name,
            "quantity_ordered": order_line.quantity_ordered,
            "quantity_received": order_line.quantity_received,
            "quantity_accepted": order_line.quantity_accepted,
            "quantity_rejected": order_line.quantity_rejected,
            "rejection_reason": order_line.notes or ""
        }
        for order_line in order_lines
    ]
    
    return JsonResponse(data, safe=False)
