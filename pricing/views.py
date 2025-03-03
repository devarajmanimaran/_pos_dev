from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, F, Value, CharField, DecimalField, Window
from django.db.models.functions import Coalesce, RowNumber, Cast
from django.db.models.expressions import OrderBy
from datetime import datetime
import json
import pytz
import pandas as pd
from io import BytesIO  # Add this import
from .models import Product, PriceMaster, PricingHistory, GST
from .forms import PriceUpdateForm, ProductUpdateForm
from django.core.paginator import Paginator
from django.db import connection  # Add this import if not already present

def price_history(request):
    try:
        product_id = request.GET.get('product_id', '')
        product_name = request.GET.get('product_name', '')
        category_id = request.GET.get('category_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        page = int(request.GET.get('page', 1))
        per_page = 100

        # Updated base queryset with proper category_id handling
        queryset = PriceMaster.objects.select_related(
            'product', 
            'product__category_id'
        ).annotate(
            serial_no=Window(
                expression=RowNumber(),
                order_by=F('product__product_id').asc()
            ),
            product_name=F('product__product_name'),
            category_id=Cast(
                'product__category_id__category_id',
                output_field=CharField()
            ),
            cgst=Coalesce(
                Cast('product__category_id__cgst', DecimalField(max_digits=10, decimal_places=2)),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            sgst=Coalesce(
                Cast('product__category_id__sgst', DecimalField(max_digits=10, decimal_places=2)),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            data_type=Value('current', CharField())
        )

        # Apply filters
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if product_name:
            queryset = queryset.filter(product__product_name__icontains=product_name)
        if category_id:
            # Clean the category ID from both input and database values for comparison
            clean_category_id = category_id.split('.')[0] if '.' in category_id else category_id
            queryset = queryset.filter(
                Q(product__category_id__category_id__exact=clean_category_id) |
                Q(product__category_id__category_id__exact=f"{clean_category_id}.0")
            )

        # Switch to historical view if date range provided
        is_historical = bool(start_date and end_date)
        if is_historical:
            queryset = PricingHistory.objects.select_related('product').filter(
                updated_on__date__range=[start_date, end_date]
            ).annotate(data_type=Value('historical', CharField()))

        # Pagination
        paginator = Paginator(queryset.order_by('product_id'), per_page)
        page_obj = paginator.get_page(page)

        return render(request, 'pricing/history.html', {
            'prices': page_obj,
            'product_id': product_id,
            'product_name': product_name,
            'category_id': category_id,
            'start_date': start_date,
            'end_date': end_date,
            'is_historical': is_historical,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_records': paginator.count,
                'per_page': per_page,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'showing_start': (page_obj.number - 1) * per_page + 1,
                'showing_end': min(page_obj.number * per_page, paginator.count)
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_price(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        updates = json.loads(request.body)
        if not isinstance(updates, list):
            updates = [updates]

        success_count = 0
        errors = []
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.now(ist)

        for data in updates:
            try:
                product_id = data.get('product_id')
                if not product_id:
                    errors.append('Product ID is required')
                    continue

                # Clean up the input data
                cleaned_data = {
                    'product_id': product_id,
                    'product_name': data.get('product_name', '').strip(),
                    'category_id': data.get('category_id', '').strip(),
                    'discount_price': data.get('discount_price', '').strip().replace('₹', '').replace(',', '')
                }

                product = Product.objects.filter(product_id=product_id).first()
                if not product:
                    errors.append(f'Product {product_id} not found')
                    continue

                changes_made = False

                # Handle product updates
                if cleaned_data['product_name'] or cleaned_data['category_id']:
                    update_data = {}
                    if cleaned_data['product_name']:
                        update_data['product_name'] = cleaned_data['product_name']
                    if cleaned_data['category_id']:
                        update_data['category_id'] = cleaned_data['category_id']
                    
                    if update_data:
                        Product.objects.filter(product_id=product_id).update(**update_data)
                        changes_made = True

                # Handle price updates
                if cleaned_data['discount_price']:
                    try:
                        new_price = float(cleaned_data['discount_price'])
                        price_master = PriceMaster.objects.get(product_id=product_id)
                        
                        if new_price != price_master.discount_price:
                            # Create history record
                            PricingHistory.objects.create(
                                history_id=f"PH_{product_id}_{current_timestamp.strftime('%Y%m%d%H%M%S')}",
                                product=product,
                                unit_cost=price_master.unit_cost,
                                unit_price=price_master.unit_price,
                                discount_price=new_price,
                                discount_price_old=price_master.discount_price,
                                updated_on=current_timestamp,
                                added_by='admin',
                                modified_by='admin'
                            )

                            # Update price master
                            price_master.discount_price = new_price
                            price_master.modified_by = 'admin'
                            price_master.updated_on = current_timestamp
                            price_master.save()
                            changes_made = True
                    except ValueError:
                        errors.append(f"Invalid price format for product {product_id}")
                        continue

                if changes_made:
                    success_count += 1

            except Exception as e:
                errors.append(f'Error updating product {product_id}: {str(e)}')
                continue

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
        print(f"Update error: {str(e)}")
        return JsonResponse({
            'error': f'Failed to process updates: {str(e)}',
            'success': False
        }, status=500)

def download_excel(request):
    try:
        # Get filter parameters
        filters = {
            'product_id': request.GET.get('product_id', ''),
            'product_name': request.GET.get('product_name', ''),
            'category_id': request.GET.get('category_id', '')
        }
        filters = {k: v for k, v in filters.items() if v}  # Remove empty filters
        
        # Get data using ORM
        queryset = PriceMaster.objects.get_product_details(filters)
        
        # Create DataFrame
        data = [{
            'Product ID': item.product.product_id,
            'Product Name': item.product.product_name,
            'Category ID': item.product.category_id.category_id if item.product.category_id else '',
            'CGST (%)': item.cgst,
            'SGST (%)': item.sgst,
            'Unit Cost': item.unit_cost,
            'Unit Price': item.unit_price,
            'Discount Price': item.discount_price,
            'Added By': item.added_by,
            'Modified By': item.modified_by,
            'Last Updated': item.updated_on.strftime('%Y-%m-%d %H:%M:%S')
        } for item in queryset]

        if not data:
            return JsonResponse({'error': 'No data found'}, status=404)

        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Price Master')
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Price Master']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length

        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=price_master_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return response

    except Exception as e:
        import traceback
        print(f"Excel download error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': f'Excel download failed: {str(e)}'
        }, status=500)

def upload_excel(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        excel_file = request.FILES['file']
        df = pd.read_excel(excel_file)
        
        # Validate columns
        required_columns = ['Product ID']
        if not all(col in df.columns for col in required_columns):
            return JsonResponse({'error': 'Missing required columns'}, status=400)
        
        changes = []
        errors = []
        
        # Get current data using ORM
        product_ids = df['Product ID'].astype(str).tolist()
        current_records = {
            str(p.product.product_id): {
                'product_id': p.product.product_id,
                'product_name': p.product.product_name,
                'category_id': p.product.category_id.category_id if p.product.category_id else None,
                'discount_price': float(p.discount_price)
            }
            for p in PriceMaster.objects.select_related(
                'product', 
                'product__category_id'
            ).filter(product__product_id__in=product_ids)
        }
        
        # Process changes
        for _, row in df.iterrows():
            product_id = str(row['Product ID']).strip()
            if product_id not in current_records:
                errors.append(f"Product not found: {product_id}")
                continue
                
            current = current_records[product_id]
            change = {
                'product_id': product_id,
                'current': current,
                'new': {},
                'changes': []
            }
            
            # Improved category ID comparison
            if 'Category ID' in df.columns and not pd.isna(row['Category ID']):
                new_category = str(row['Category ID']).strip()
                current_category = str(current['category_id']) if current['category_id'] else ''
                
                if new_category and new_category != current_category:
                    change['new']['category_id'] = new_category
                    change['changes'].append('Category')
            
            # Check for changes
            if 'Product Name' in df.columns and not pd.isna(row['Product Name']):
                new_name = str(row['Product Name']).strip()
                if new_name != current['product_name']:
                    change['new']['product_name'] = new_name
                    change['changes'].append('Product Name')
            
            if 'Discount Price' in df.columns and not pd.isna(row['Discount Price']):
                try:
                    new_price = float(row['Discount Price'])
                    if new_price != current['discount_price']:
                        change['new']['discount_price'] = new_price
                        change['changes'].append('Price')
                except ValueError:
                    errors.append(f"Invalid price format for product {product_id}")
                    continue
            
            if change['changes']:
                changes.append(change)

        # Apply changes using bulk operations
        if changes:
            success_count = PriceMaster.objects.bulk_update_prices(changes)
        
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