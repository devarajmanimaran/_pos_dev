from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import POOrderLines  # Ensure this matches your model
from django.views.decorators.csrf import csrf_exempt

# Create your views here.


def material_inward(request):
    # Query data from PostgreSQL table "pos_dev"."PO_ORDER_LINES"
    query = """
    select po_number
        po_header_id,
        order_date,
        status,
        supplier_id
        from pos_dev.Po_Order_Headers
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Prepare the data as a list of dictionaries
    columns = [
        'PO_NO', 'CREATED_DATE', 'STATUS', 'SUPPLIER_ID'
    ]
    data = [dict(zip(columns, row)) for row in rows]

    return render(request, 'material_inward/material_inward.html', {'data': data})

def get_po_details(request, po_id):
    order_lines = POOrderLines.objects.filter(po_number=po_id)
    
    if not order_lines.exists():
        return JsonResponse({"error": "PO not found"}, status=404)
    
    data = [
        {
            "po_line_id": order_line.po_line_id,
            "po_number": order_line.po_number,
            "product_name": order_line.product_name,
            "priority": order_line.priority,
            "quantity_ordered": order_line.quantity_ordered,
            "uom": order_line.uom,
            "status": order_line.status,
            "quantity_invoice": order_line.quantity_invoice,
            "quantity_received": order_line.quantity_received,
            "quantity_accepted": order_line.quantity_accepted,
            "quantity_rejected": order_line.quantity_rejected,
            "rejection_reason": order_line.notes or "",
            "is_processed": order_line.status in ['Received', 'Pending for approval', 'Partially Received', 'Rejected']
        }
        for order_line in order_lines
    ]
    
    return render(request, 'material_inward/po_details.html', {'order_lines': data, 'po_number': po_id})

def process_po_receipt(request):
    if request.method == "POST":
        data = request.POST
        try:
            # Ensure default values if fields are missing or empty
            po_number = data.get("po_number", "").strip()
            po_line_id = int(data.get("po_line_id") or 0)
            quantity_invoice = int(data.get("quantity_invoice") or 0)
            quantity_received = int(data.get("quantity_received") or 0)
            quantity_accepted = int(data.get("quantity_accepted") or 0)
            quantity_rejected = int(data.get("quantity_rejected") or 0)
            rejection_reason = data.get("rejection_reason", "None").strip()
            priority = data.get("priority", "Non Critical").strip()

            # Ensure PO number is not empty
            if not po_number:
                return JsonResponse({"success": False, "error": "PO number is required."})

            with connection.cursor() as cursor:
                query = """
                    CALL "pos_dev".process_po_receipt_new(
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(query, [
                    po_number, po_line_id, quantity_invoice, quantity_received,
                    quantity_accepted, quantity_rejected, rejection_reason, priority
                ])
                # Fetch the new status after processing
                cursor.execute("SELECT status FROM pos_dev.po_order_lines WHERE po_line_id = %s", [po_line_id])
                new_status = cursor.fetchone()[0]

            return JsonResponse({"success": True, "new_status": new_status})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})