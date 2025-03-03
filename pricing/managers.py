from django.db import models, transaction
from django.db.models import F, Value, Window, Q, CharField, DecimalField
from django.db.models.functions import Coalesce, RowNumber, Cast
from django.utils import timezone  # Add this import

class PriceMasterManager(models.Manager):
    def get_product_details(self, filters=None):
        queryset = self.select_related(
            'product',
            'product__category_id'
        ).annotate(
            serial_no=Window(
                expression=RowNumber(),
                order_by=F('product__product_id').asc()
            ),
            cgst=Coalesce('product__category_id__cgst', Value(0.0)),
            sgst=Coalesce('product__category_id__sgst', Value(0.0)),
            clean_category_id=Cast(
                'product__category_id__category_id',
                output_field=CharField()
            ),
            category_id=Cast(
                'product__category_id__category_id',
                output_field=CharField()
            )
        )
        
        if filters:
            if filters.get('product_id'):
                queryset = queryset.filter(product__product_id=filters['product_id'])
            if filters.get('product_name'):
                queryset = queryset.filter(product__product_name__icontains=filters['product_name'])
            if filters.get('category_id'):
                clean_category = filters['category_id'].split('.')[0] if '.' in filters['category_id'] else filters['category_id']
                queryset = queryset.filter(
                    Q(product__category_id__category_id__exact=clean_category) |
                    Q(product__category_id__category_id__exact=f"{clean_category}.0")
                )
        
        return queryset.order_by('product__product_id')

    def bulk_update_prices(self, changes, user='admin'):
        from .models import PricingHistory, Product
        from datetime import datetime
        
        current_timestamp = datetime.now().replace(microsecond=0)
        history_records = []
        updated_prices = []
        updated_products = []

        with transaction.atomic():
            for change in changes:
                try:
                    # Get existing records
                    price_record = self.get(product_id=change['product_id'])
                    product = Product.objects.get(product_id=change['product_id'])
                    
                    # Only update category if it's explicitly changed and valid
                    if 'category_id' in change['new'] and change['new']['category_id']:
                        new_category = change['new']['category_id'].strip()
                        current_category = product.category_id.category_id if product.category_id else None
                        
                        if new_category != current_category:
                            product.category_id_id = new_category
                            updated_products.append(product)

                    # Handle price changes
                    if 'discount_price' in change['new']:
                        history_records.append(
                            PricingHistory(
                                history_id=f"PH_{change['product_id']}_{current_timestamp.strftime('%Y%m%d%H%M%S')}",
                                product_id=change['product_id'],
                                unit_cost=price_record.unit_cost,
                                unit_price=price_record.unit_price,
                                discount_price=change['new']['discount_price'],
                                discount_price_old=price_record.discount_price,
                                updated_on=current_timestamp,  # Use the same timestamp
                                added_by=user,
                                modified_by=user
                            )
                        )
                        
                        price_record.discount_price = change['new']['discount_price']
                        price_record.modified_by = user
                        price_record.updated_on = current_timestamp  # Ensure timestamp is set
                        updated_prices.append(price_record)

                    # Handle name changes
                    if 'product_name' in change['new']:
                        new_name = change['new']['product_name'].strip()
                        if new_name != product.product_name:
                            product.product_name = new_name
                            if product not in updated_products:
                                updated_products.append(product)

                except (Product.DoesNotExist, self.model.DoesNotExist) as e:
                    print(f"Error processing product {change['product_id']}: {str(e)}")
                    continue

            # Bulk operations
            if history_records:
                PricingHistory.objects.bulk_create(history_records)
            
            if updated_prices:
                self.bulk_update(updated_prices, ['discount_price', 'modified_by', 'updated_on'])
            
            if updated_products:
                # Only update fields that have actually changed
                Product.objects.bulk_update(
                    updated_products, 
                    ['category_id', 'product_name']
                )

        return len(updated_prices) + len(updated_products)
