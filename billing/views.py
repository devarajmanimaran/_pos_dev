from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
import uuid
from datetime import datetime
import random
import json  # Add this import


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



def get_customer(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        
        if not phone:
            return JsonResponse({'found': False, 'error': 'Phone number is required'})
            
        query = '''
        SELECT Customer_ID, Customer_Name, Address_Line_1, Address_Line_2
        FROM pos_dev.Customer
        WHERE Phone_Number = %s;
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [phone])
                result = cursor.fetchone()
                
            if result:
                return JsonResponse({
                    'found': True,
                    'customer': {
                        'customer_id': result[0],
                        'name': result[1],
                        'address1': result[2],
                        'address2': result[3]
                    }
                })
            return JsonResponse({'found': False, 'error': 'Customer not found'})
            
        except Exception as e:
            print(f"Database error: {str(e)}")  # For debugging
            return JsonResponse({
                'found': False,
                'error': 'Database error occurred'
            }, status=500)

def save_customer(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address1 = request.POST.get("address1")
        address2 = request.POST.get("address2")
        
        if not name or not phone:
            return JsonResponse({'success': False, 'error': 'Name and phone are required'})

        # Generate unique customer ID
        customer_id = str(uuid.uuid4())
        # Get current timestamp
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        added_by = 'admin'  # Hardcoded for now

        # First check if customer with this phone number already exists
        check_query = '''
        SELECT COUNT(*) FROM pos_dev.Customer 
        WHERE Phone_Number = %s;
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(check_query, [phone])
                if cursor.fetchone()[0] > 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Customer with this phone number already exists'
                    })
                
                # If no existing customer, proceed with insert
                insert_query = '''
                INSERT INTO pos_dev.Customer 
                (Customer_ID, Customer_Name, Phone_Number, Address_Line_1, Address_Line_2, Created_Date, Added_By) 
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                '''
                
                cursor.execute(insert_query, [
                    customer_id,
                    name, 
                    phone, 
                    address1, 
                    address2,
                    created_date,
                    added_by
                ])
                connection.commit()
                
                return JsonResponse({
                    'success': True,
                    'customer_id': customer_id
                })
                
        except Exception as e:
            print(f"Database error in save_customer: {str(e)}")  # For debugging
            return JsonResponse({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }, status=500)

def get_bill_number():
    current_date = datetime.now().strftime('%Y%m%d')
    
    query = '''
    SELECT MAX(RIGHT(bill_no, 4)) 
    FROM pos_dev.sales 
    WHERE LEFT(bill_no, 8) = %s
    '''
    
    with connection.cursor() as cursor:
        cursor.execute(query, [current_date])
        result = cursor.fetchone()[0]
        
    next_number = '0001' if not result else str(int(result) + 1).zfill(4)
    return f"{current_date}{next_number}"

def generate_sales_id():
    current_date = datetime.now().strftime('%Y%m%d')
    while True:
        random_number = str(random.randint(1000, 9999))
        sales_id = f"{current_date}{random_number}"
        
        # Check if this sales_id already exists
        query = "SELECT COUNT(*) FROM pos_dev.sales WHERE sales_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(query, [sales_id])
            if cursor.fetchone()[0] == 0:
                return sales_id

def save_bill(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # Debug line to check incoming data
        print("Request body:", request.body.decode('utf-8'))
        
        data = json.loads(request.body)
        items = data.get('items', [])
        customer_id = data.get('customer_id', 'GENERIC001')
        
        if not items:
            return JsonResponse({"error": "No items in bill"}, status=400)
        
        sales_id = generate_sales_id()
        bill_no = get_bill_number()
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        employee_id = 'admin'
        
        # Debug lines
        print(f"Generated sales_id: {sales_id}")
        print(f"Generated bill_no: {bill_no}")
        
        # Insert into sales table
        sales_query = '''
        INSERT INTO pos_dev.sales 
        (sales_id, bill_no, customer_id, total_amount, creation_date, employee_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        '''
        
        # Insert into sales_details table - adjusted column names
        details_query = '''
        INSERT INTO pos_dev.sales_details 
        (sales_details_id, sales_id, product_id, total_units, unit_price, 
         discount_price, cgst, sgst, total_amount, created_date, bill_no, customer_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        total_bill_amount = 0
        
        with connection.cursor() as cursor:
            try:
                # First insert the main sales record
                cursor.execute(sales_query, [
                    sales_id,
                    bill_no,
                    customer_id,
                    0,  # Will update this after calculating details
                    created_date,
                    employee_id
                ])
                
                # Then insert each item's details
                for item in items:
                    sales_details_id = f"{sales_id}_{item['productId']}"
                    total_amount = float(item['total'])
                    cgst_amount = (float(item['cgst']) / 100) * total_amount
                    sgst_amount = (float(item['sgst']) / 100) * total_amount
                    
                    print(f"Processing item: {item}")  # Debug line
                    
                    cursor.execute(details_query, [
                        sales_details_id,
                        sales_id,
                        item['productId'],
                        item['quantity'],
                        item['unitPrice'],
                        item['discountPrice'],
                        cgst_amount,  # Changed to calculated amount
                        sgst_amount,  # Changed to calculated amount
                        total_amount,
                        created_date,
                        bill_no,
                        customer_id
                    ])
                    
                    total_bill_amount += total_amount
                
                # Update the total amount in sales table
                cursor.execute(
                    "UPDATE pos_dev.sales SET total_amount = %s WHERE sales_id = %s",
                    [total_bill_amount, sales_id]
                )
                
                connection.commit()
                
                return JsonResponse({
                    "success": True,
                    "sales_id": sales_id,
                    "bill_no": bill_no
                })
                
            except Exception as e:
                print(f"Database error: {str(e)}")  # Debug line
                connection.rollback()
                raise  # Re-raise the exception for the outer try block
                
    except Exception as e:
        print(f"Error saving bill: {str(e)}")  # Debug line
        return JsonResponse({
            "error": f"Failed to save bill: {str(e)}"
        }, status=500)
