from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse, HttpResponse
from datetime import datetime
import json
import pytz  # Add this import at the top
import pandas as pd
from openpyxl import Workbook
from io import BytesIO

def price_history(request):
    try:
        product_id = request.GET.get('product_id', '')
        product_name = request.GET.get('product_name', '')
        category_id = request.GET.get('category_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        page = int(request.GET.get('page', 1))
        per_page = 100
        
        # Flag to indicate if we're showing historical data
        is_historical = bool(start_date and end_date)
        
        # Base query for count
        count_query = '''
        SELECT COUNT(*) 
        FROM pos_dev.price_master pm
        LEFT JOIN pos_dev.product p ON pm.product_id = p.Product_ID
        WHERE 1=1
        '''
        
        # Base query for data
        query = '''
        SELECT 
            ROW_NUMBER() OVER (ORDER BY pm.product_id) as Serial_No,
            pm.Product_ID,
            COALESCE(p.Product_Name, 'N/A') as Product_Name,
            COALESCE(p.Category_ID, 'N/A') as Category_ID,
            COALESCE(g.CGST, 0) as CGST,
            COALESCE(g.SGST, 0) as SGST,
            pm.Unit_Cost,
            pm.Unit_Price,
            pm.Discount_Price,
            NULL as Discount_Price_Old,
            pm.Added_By,
            pm.Modified_By,
            TO_CHAR(pm.Updated_On, 'DD-MM-YYYY HH24:MI:SS') as Updated_On,
            'current' as data_type
        FROM pos_dev.price_master pm
        LEFT JOIN pos_dev.product p ON pm.product_id = p.Product_ID
        LEFT JOIN pos_dev.gst g ON p.Category_ID = g.Category_ID
        WHERE 1=1
        '''
        
        count_params = []
        params = []

        # Exact match for Product ID
        if product_id:
            query += " AND pm.Product_ID = %s"
            count_query += " AND pm.Product_ID = %s"
            params.append(product_id)
            count_params.append(product_id)

        # Exact match for Category ID
        if category_id:
            query += " AND p.Category_ID = %s"
            count_query += " AND p.Category_ID = %s"
            params.append(category_id)
            count_params.append(category_id)

        # LIKE match for Product Name
        if product_name:
            query += " AND p.Product_Name ILIKE %s"
            count_query += " AND p.Product_Name ILIKE %s"
            params.append(f'%{product_name}%')
            count_params.append(f'%{product_name}%')
        
        with connection.cursor() as cursor:
            cursor.execute(count_query, count_params)
            total_records = cursor.fetchone()[0]
        
        # Calculate total pages
        total_pages = (total_records + per_page - 1) // per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Switch to historical view if date range is provided
        if is_historical:
            query = query.replace('price_master pm', 'pricing_history ph')
            query = query.replace('pm.', 'ph.')
            query = query.replace("'current' as data_type", "'historical' as data_type")
            query = query.replace(
                "CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata'", 
                "ph.Updated_On AT TIME ZONE 'Asia/Kolkata'"
            )
            query += " AND DATE(ph.Updated_On) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        
        query += " ORDER BY Product_ID LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            prices = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            pagination = {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'per_page': per_page,
                'has_previous': page > 1,
                'has_next': page < total_pages,
                'showing_start': offset + 1,
                'showing_end': min(offset + per_page, total_records)
            }
            
            return render(request, 'pricing/history.html', {
                'prices': prices,
                'product_id': product_id,
                'product_name': product_name,
                'category_id': category_id,
                'start_date': start_date,
                'end_date': end_date,
                'is_historical': is_historical,
                'pagination': pagination
            })
            
    except Exception as e:
        print(f"Database error in price_history: {str(e)}")
        return JsonResponse({
            'error': f'Failed to fetch price history: {str(e)}'
        }, status=500)

def update_price(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        updates = json.loads(request.body)
        print("Received updates:", updates)  # Debug log
        
        if not isinstance(updates, list):
            updates = [updates]

        success_count = 0
        errors = []
        
        # Get current IST timestamp
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.now(ist).replace(tzinfo=None)
        
        for data in updates:
            try:
                product_id = data.get('product_id')
                if not product_id:
                    errors.append('Product ID is required')
                    continue

                with connection.cursor() as cursor:
                    # First verify product exists
                    check_query = '''
                    SELECT Product_ID FROM pos_dev.product WHERE Product_ID = %s
                    '''
                    cursor.execute(check_query, [product_id])
                    if not cursor.fetchone():
                        errors.append(f'Product {product_id} not found')
                        continue

                    changes_made = False

                    # Handle product name and category updates
                    if 'product_name' in data or 'category_id' in data:
                        product_update_query = '''
                        UPDATE pos_dev.product 
                        SET Product_Name = COALESCE(%s, Product_Name),
                            Category_ID = COALESCE(%s, Category_ID)
                        WHERE Product_ID = %s
                        '''
                        cursor.execute(product_update_query, [
                            data.get('product_name'),
                            data.get('category_id'),
                            product_id
                        ])
                        changes_made = True

                    # Handle discount price update
                    if 'discount_price' in data:
                        # Get current pricing info before making changes
                        current_price_query = '''
                        SELECT Unit_Cost, Unit_Price, Discount_Price 
                        FROM pos_dev.price_master 
                        WHERE Product_ID = %s
                        '''
                        cursor.execute(current_price_query, [product_id])
                        current_price = cursor.fetchone()

                        if current_price:
                            discount_price = float(data['discount_price'].replace('₹', '').strip())
                            history_id = f"PH_{product_id}_{current_timestamp.strftime('%Y%m%d%H%M%S')}"

                            # First save to pricing_history
                            price_history_query = '''
                            INSERT INTO pos_dev.pricing_history 
                            (history_id, product_id, unit_cost, unit_price, 
                             discount_price, discount_price_old, updated_on, 
                             added_by, modified_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            '''
                            cursor.execute(price_history_query, [
                                history_id,
                                product_id,
                                current_price[0],  # Unit_Cost
                                current_price[1],  # Unit_Price
                                discount_price,
                                current_price[2],  # Old Discount_Price
                                current_timestamp,
                                'admin',
                                'admin'
                            ])

                            # Then update price_master
                            update_master_query = '''
                            UPDATE pos_dev.price_master 
                            SET discount_price = %s,
                                modified_by = %s,
                                updated_on = %s
                            WHERE product_id = %s
                            '''
                            cursor.execute(update_master_query, [
                                discount_price,
                                'admin',
                                current_timestamp,
                                product_id
                            ])
                            changes_made = True
                        else:
                            errors.append(f'No pricing info found for product {product_id}')
                            continue

                    if changes_made:
                        success_count += 1
                        connection.commit()
                    else:
                        errors.append(f'No changes detected for product {product_id}')

            except Exception as e:
                print(f"Error updating product {product_id}: {str(e)}")
                errors.append(f'Error updating product {product_id}: {str(e)}')
                connection.rollback()

        if success_count > 0:
            return JsonResponse({
                'success': True,
                'message': f'Successfully updated {success_count} products',
                'errors': errors if errors else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No updates were successful',
                'errors': errors
            }, status=400)

    except Exception as e:
        print(f"Error in update_price: {str(e)}")
        return JsonResponse({
            'error': f'Failed to process updates: {str(e)}',
            'success': False
        }, status=500)

def download_excel(request):
    try:
        # Get filter parameters from query string
        product_id = request.GET.get('product_id', '')
        product_name = request.GET.get('product_name', '')
        category_id = request.GET.get('category_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        
        # Base query for current prices
        query = '''
        SELECT 
            p.Product_ID,
            p.Product_Name,
            p.Category_ID,
            COALESCE(g.CGST, 0) as CGST,
            COALESCE(g.SGST, 0) as SGST,
            pm.Unit_Cost,
            pm.Unit_Price,
            pm.Discount_Price,
            pm.Updated_On
        FROM pos_dev.price_master pm
        LEFT JOIN pos_dev.product p ON pm.product_id = p.Product_ID
        LEFT JOIN pos_dev.gst g ON p.Category_ID = g.Category_ID
        WHERE 1=1
        '''
        
        params = []
        
        # Exact match for Product ID
        if product_id:
            query += " AND p.Product_ID = %s"
            params.append(product_id)
            
        # Exact match for Category ID
        if category_id:
            query += " AND p.Category_ID = %s"
            params.append(category_id)
            
        # LIKE match for Product Name
        if product_name:
            query += " AND p.Product_Name ILIKE %s"
            params.append(f'%{product_name}%')
        
        # Date range if provided
        if start_date and end_date:
            query += " AND DATE(pm.Updated_On) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
            
        query += " ORDER BY p.Product_ID"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
        # Create DataFrame with all columns
        df = pd.DataFrame(rows, columns=[
            'Product ID', 'Product Name', 'Category ID', 
            'CGST (%)', 'SGST (%)', 'Unit Cost', 
            'Unit Price', 'Discount Price', 'Last Updated'
        ])
        
        # Format currency columns
        currency_columns = ['Unit Cost', 'Unit Price', 'Discount Price']
        for col in currency_columns:
            df[col] = df[col].apply(lambda x: f'₹ {x:,.2f}')
        
        # Format percentage columns
        percentage_columns = ['CGST (%)', 'SGST (%)']
        for col in percentage_columns:
            df[col] = df[col].apply(lambda x: f'{x}%')
        
        # Create Excel file
        output = BytesIO()
        
        # Create Excel writer with datetime formatting
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Price Master')
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Price Master']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length
        
        output.seek(0)
        
        # Generate filename with current filters
        filename_parts = ['price_data']
        if product_id:
            filename_parts.append(f'pid_{product_id}')
        if category_id:
            filename_parts.append(f'cat_{category_id}')
        if product_name:
            filename_parts.append('filtered')
        filename_parts.append(datetime.now().strftime('%Y%m%d'))
        
        filename = '_'.join(filename_parts) + '.xlsx'
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        print(f"Excel download error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def upload_excel(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        excel_file = request.FILES['file']
        df = pd.read_excel(excel_file)

        # Required columns
        required_columns = ['Product ID']
        optional_columns = ['Product Name', 'Category ID', 'Discount Price']
        
        # Check required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return JsonResponse({
                'error': f'Missing required columns: {", ".join(missing_columns)}'
            }, status=400)

        changes = []
        errors = []
        
        with connection.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    # Convert product_id to string and clean it
                    product_id = str(row['Product ID']).strip()
                    
                    # Get current product info
                    cursor.execute("""
                        SELECT 
                            p.product_id,
                            p.product_name,
                            p.category_id,
                            pm.unit_cost,
                            pm.unit_price,
                            pm.discount_price
                        FROM pos_dev.product p
                        LEFT JOIN pos_dev.price_master pm ON p.product_id = pm.product_id
                        WHERE p.product_id = %s
                    """, [product_id])
                    
                    result = cursor.fetchone()
                    if result:
                        current_data = {
                            'product_id': result[0],
                            'product_name': result[1],
                            'category_id': result[2],
                            'unit_cost': result[3],
                            'unit_price': result[4],
                            'discount_price': float(result[5]) if result[5] else 0
                        }
                        
                        change = {
                            'product_id': product_id,
                            'current': current_data,
                            'new': {},
                            'changes': []
                        }
                        
                        # Check each column for changes
                        if 'Product Name' in df.columns and not pd.isna(row['Product Name']):
                            new_name = str(row['Product Name']).strip()
                            if new_name != current_data['product_name']:
                                change['new']['product_name'] = new_name
                                change['changes'].append('Product Name')
                        
                        if 'Category ID' in df.columns and not pd.isna(row['Category ID']):
                            new_category = str(row['Category ID']).strip()
                            if new_category != current_data['category_id']:
                                change['new']['category_id'] = new_category
                                change['changes'].append('Category')
                        
                        if 'Discount Price' in df.columns and not pd.isna(row['Discount Price']):
                            try:
                                new_price = float(row['Discount Price'])
                                if new_price != current_data['discount_price']:
                                    change['new']['discount_price'] = new_price
                                    change['changes'].append('Price')
                            except ValueError:
                                errors.append(f"Invalid price format for product {product_id}")
                                continue
                        
                        if change['changes']:
                            changes.append(change)
                    else:
                        errors.append(f"Product not found: {product_id}")
                
                except Exception as e:
                    errors.append(f"Error processing row {index + 1}: {str(e)}")
                    continue
        
        # Generate summary
        summary = {
            'total_products': len(changes),
            'price_changes': sum(1 for c in changes if 'Price' in c['changes']),
            'name_changes': sum(1 for c in changes if 'Product Name' in c['changes']),
            'category_changes': sum(1 for c in changes if 'Category' in c['changes'])
        }

        return JsonResponse({
            'success': True,
            'changes': changes,
            'summary': summary,
            'errors': errors if errors else None,
            'message': f"Found {len(changes)} products with changes"
        })
        
    except Exception as e:
        print(f"Excel upload error: {str(e)}")
        return JsonResponse({
            'error': f'Failed to process Excel file: {str(e)}'
        }, status=500)
