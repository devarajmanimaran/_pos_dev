from django.shortcuts import render
from django.db import connection

def homepage(request):
    return render(request, 'store/index.html')


def inbound_check(request):
    # Query data from PostgreSQL table "pos_dev"."PO_ORDER_LINES"
    query = """
    SELECT "PO_ORDER_NUMBER", PO_HEADER_ID, PO_LINE_ID, LINE_NUMBER, PRODUCT, ORDERED_QTY,
           RECEVIED_QTY, RETURN_QTY, LOT, RETURN_REASON, CREATED_DATE, STATUS,"Supplier_ID"
    FROM "pos_dev"."PO_ORDER_LINES"
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Prepare the data as a list of dictionaries
    columns = [
        'PO_ORDER_NUMBER', 'PO_HEADER_ID', 'PO_LINE_ID', 'LINE_NUMBER', 'PRODUCT', 'ORDERED_QTY',
        'RECEVIED_QTY', 'RETURN_QTY', 'LOT', 'RETURN_REASON', 'CREATED_DATE', 'STATUS', 'Supplier_ID'
    ]
    data = [dict(zip(columns, row)) for row in rows]

    return render(request, 'store/inbound_check.html', {'data': data})