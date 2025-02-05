from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection



def billing_home(request):
    return render(request, 'billing/home.html')


def bill_value(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        qty = request.POST.get("qty")

        if not product_id or not qty:
            return JsonResponse({"error": "Product ID and Quantity are required."}, status=400)

        query = '''
        SELECT p.Product_ID, 
                p.Product_Name, 
                pm.Unit_Price, 
                pm.Discount_Price, 
                g.CGST,
                g.SGST
        FROM pos_dev.Product p
        JOIN pos_dev.price_master pm ON p.Product_ID = pm.Product_id
        JOIN pos_dev.gst g ON p.Category_ID = g.Category_ID
        WHERE p.Product_ID = %s;
        '''
        with connection.cursor() as cursor:
            cursor.execute(query, (str(product_id),))
            result = cursor.fetchone()  # Use fetchone() for efficiency since we expect a single product

        if not result:
            return JsonResponse({"error": "Product not found."}, status=404)

        # Define column names
        columns = ['Product_ID', 'Product_Name', 'Unit_Price', 'Discount_Price',  'CGST', 'SGST']

        # Convert result to dictionary
        bill_data = dict(zip(columns, result))
        bill_data["Qty"] = int(qty)

        # Calculate total price
        bill_data["Total"] = int(qty) * bill_data["Discount_Price"]

        # Return JSON response
        return JsonResponse(bill_data)

    # Render form for GET requests
    return render(request, 'billing/form.html')
