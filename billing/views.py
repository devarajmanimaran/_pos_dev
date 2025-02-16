from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db import connection
import uuid
from datetime import datetime
import random
import json  # Add this import
from django.template.loader import render_to_string
import pdfkit  # You'll need to install pdfkit and wkhtmltopdf
import os


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
        bill_data["Qty"] = float(qty)

        # Calculate total price
        bill_data["Total"] = float(qty) * bill_data["Discount_Price"]

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
        data = json.loads(request.body)
        items = data.get('items', [])
        customer_id = data.get('customer_id', 'GENERIC001')
        payment_method = data.get('paymentMethod', 'CASH')
        
        if not items:
            return JsonResponse({"error": "No items in bill"}, status=400)
        
        # Aggregate items by product_id
        aggregated_items = {}
        for item in items:
            product_id = item['productId']
            if product_id in aggregated_items:
                # Update existing item
                agg_item = aggregated_items[product_id]
                agg_item['quantity'] += float(item['quantity'])
                agg_item['total'] += float(item['total'])
            else:
                # Add new item
                aggregated_items[product_id] = {
                    'productId': product_id,
                    'quantity': float(item['quantity']),
                    'unitPrice': float(item['unitPrice']),
                    'discountPrice': float(item['discountPrice']),
                    'cgst': float(item['cgst']),
                    'sgst': float(item['sgst']),
                    'total': float(item['total'])
                }
        
        # Convert back to list
        items = list(aggregated_items.values())
        
        sales_id = generate_sales_id()
        bill_no = get_bill_number()
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        employee_id = 'admin'
        
        # Calculate total bill amount
        total_bill_amount = sum(item['total'] for item in items)
        
        with connection.cursor() as cursor:
            try:
                # Insert sales record
                sales_query = '''
                INSERT INTO pos_dev.sales 
                (sales_id, bill_no, customer_id, total_amount, creation_date, employee_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                '''
                
                cursor.execute(sales_query, [
                    sales_id,
                    bill_no,
                    customer_id,
                    total_bill_amount,
                    created_date,
                    employee_id
                ])
                
                # Insert aggregated sales details
                details_query = '''
                INSERT INTO pos_dev.sales_details 
                (sales_details_id, sales_id, product_id, total_units, unit_price, 
                 discount_price, cgst, sgst, total_amount, created_date, bill_no, customer_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                
                for item in items:
                    sales_details_id = f"{sales_id}_{item['productId']}"
                    cgst_amount = (item['cgst'] / 100) * item['total']
                    sgst_amount = (item['sgst'] / 100) * item['total']
                    
                    cursor.execute(details_query, [
                        sales_details_id,
                        sales_id,
                        item['productId'],
                        item['quantity'],
                        item['unitPrice'],
                        item['discountPrice'],
                        cgst_amount,
                        sgst_amount,
                        item['total'],
                        created_date,
                        bill_no,
                        customer_id
                    ])
                
                # Add payment record
                payment_query = '''
                INSERT INTO pos_dev.bill_payment 
                (bill_no, payment_mode, total_amount)
                VALUES (%s, %s, %s)
                '''
                
                cursor.execute(payment_query, [
                    bill_no,
                    payment_method,
                    total_bill_amount
                ])
                
                connection.commit()
                
                return JsonResponse({
                    "success": True,
                    "sales_id": sales_id,
                    "bill_no": bill_no
                })
                
            except Exception as e:
                print(f"Database error: {str(e)}")
                connection.rollback()
                raise
                
    except Exception as e:
        print(f"Error saving bill: {str(e)}")
        return JsonResponse({
            "error": f"Failed to save bill: {str(e)}"
        }, status=500)

def generate_pdf(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Aggregate items by product ID
            aggregated_items = {}
            for item in data.get('items', []):
                product_id = item['productId']
                if product_id in aggregated_items:
                    agg_item = aggregated_items[product_id]
                    agg_item['quantity'] += float(item['quantity'])
                    agg_item['total'] += float(item['total'])
                    agg_item['gst_rate1']=item['cgst']+item['sgst']
                else:
                    aggregated_items[product_id] = {
                        'productId': product_id,
                        'productName': item['productName'],
                        'quantity': float(item['quantity']),
                        'unitPrice': float(item['unitPrice']),
                        'discountPrice': float(item['discountPrice']),
                        'cgst': float(item['cgst']),
                        'sgst': float(item['sgst']),
                        'total': float(item['total']),
                        'gst_rate1': float((item['cgst'])+ (item['sgst']))
                    }

            # Convert aggregated items back to list
            items = list(aggregated_items.values())
            
            bill_data = {
                'bill_no': data.get('billNo', ''),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payment_method': data.get('paymentMethod', 'CASH'),
                'customer': data.get('customer', {}),
                'items': items,
                'grand_total': data.get('grandTotal', 0),
            }

            # Calculate tax summary from aggregated items
            gst_summary = {}
            total_tax_amount = 0  # Initialize grand total tax
            
            for item in items:
                gst_rate = item['cgst'] + item['sgst']
                taxable_value = item['discountPrice'] * item['quantity']
                cgst_amount = (item['cgst'] / 100) * taxable_value
                sgst_amount = (item['sgst'] / 100) * taxable_value
                total_tax = cgst_amount + sgst_amount
                total_tax_amount += total_tax  # Add to grand total tax
                
                if gst_rate not in gst_summary:
                    gst_summary[gst_rate] = {
                        'taxable_value': taxable_value,
                        'cgst': cgst_amount,
                        'sgst': sgst_amount,
                        'total_tax': total_tax
                    }
                else:
                    summary = gst_summary[gst_rate]
                    summary['taxable_value'] += taxable_value
                    summary['cgst'] += cgst_amount
                    summary['sgst'] += sgst_amount
                    summary['total_tax'] += total_tax

            # Update bill_data with tax summary and total tax
            bill_data = {
                'bill_no': data.get('billNo', ''),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payment_method': data.get('paymentMethod', 'CASH'),
                'customer': data.get('customer', {}),
                'items': items,
                'grand_total': data.get('grandTotal', 0),
                'total_tax_amount': round(total_tax_amount, 2),  # Add total tax to bill data
                'tax_summary': [
                    {
                        'gst_rate': rate,
                        'taxable_value': round(summary['taxable_value'], 2),
                        'cgst': round(summary['cgst'], 2),
                        'sgst': round(summary['sgst'], 2),
                        'total_tax': round(summary['total_tax'], 2)
                    }
                    for rate, summary in sorted(gst_summary.items())
                ]
            }

            print("Bill Data for PDF:", bill_data)  # Debug print
            
            html_string = render_to_string('billing/pdf_template.html', bill_data)
            
            config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
            
            # Fixed options for thermal printer
            options = {
                #'page-size': 'A4',
                'page-width': '101.6mm',  # 4 inches in mm
                'page-height': '297mm',    # Default height (will be adjusted automatically)
                'margin-top': '3mm',
                'margin-right': '3mm',
                'margin-bottom': '3mm',
                'margin-left': '3mm',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None,
                'disable-smart-shrinking': None,
                'dpi': 300,
                'quiet': ''
            }
            
            try:
                pdf = pdfkit.from_string(html_string, False, options=options, configuration=config)
                if not pdf:
                    raise Exception("PDF generation failed - empty output")
                
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = 'inline'
                return response
                
            except Exception as e:
                print(f"PDFKit Error: {str(e)}")
                raise
            
        except Exception as e:
            print(f"PDF Generation Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
