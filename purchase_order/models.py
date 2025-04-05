from django.db import models

class Supplier(models.Model):
    supplier_id = models.CharField(primary_key=True, max_length=255)
    supplier_name = models.CharField(max_length=255)
    # Add other fields from your supplier table as needed
    phone_number = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    payment_terms = models.CharField(max_length=255)

    class Meta:
        db_table = 'supplier'  # Replace with your actual table name
        managed = False  # Since the table already exists

    def __str__(self):
        return self.supplier_name

class ProductSupplierCost(models.Model):
    product_id = models.CharField(primary_key=True, max_length=255)
    supplier_id = models.CharField(max_length=255)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    moq = models.IntegerField()

    class Meta:
        db_table = 'product_supplier_cost'  # Remove schema prefix
        managed = False
        unique_together = (('product_id', 'supplier_id'),)

    def __str__(self):
        return f"{self.product_id} - {self.supplier_id}"

class ProductCategory(models.Model):
    category_id = models.CharField(primary_key=True, max_length=255)
    category_name = models.CharField(max_length=255)
    category_description = models.CharField(max_length=255)

    class Meta:
        db_table = 'product_category'  # Replace with your actual table name
        managed = False  # Since the table already exists

    def __str__(self):
        return self.category_name

class Product(models.Model):
    product_id = models.CharField(primary_key=True, max_length=255)
    product_name = models.CharField(max_length=255)
    product_description = models.CharField(max_length=255)
    product_status = models.CharField(max_length=255)
    supplier_id = models.ForeignKey(Supplier, on_delete=models.CASCADE, db_column='supplier_id')
    category_id = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, db_column='category_id')
    shelf_life_days = models.IntegerField()
    uom = models.CharField(max_length=50, default='pcs')
    created_date = models.DateTimeField()
    updated_date = models.DateTimeField()
    added_by = models.CharField(max_length=255)
    modified_by = models.CharField(max_length=255)

    class Meta:
        db_table = 'product'  # Replace with your actual table name
        managed = False  # Since the table already exists

    def __str__(self):
        return self.product_name

class StoreDetails(models.Model):
    store_id = models.CharField(primary_key=True, max_length=255)
    store_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    my_store = models.CharField(max_length=50)

    class Meta:
        db_table = 'store_details'  # Replace with your actual table name
        managed = False  # Since the table already exists

    def __str__(self):
        return self.store_name

class POOrderHeader(models.Model):
    po_header_id = models.AutoField(primary_key=True)
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, db_column='supplier_id')  # ForeignKey to Supplier
    order_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField(null=True, blank=True)
    total_order_value = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_completed_date = models.DateTimeField(null=True, blank=True)
    actual_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50)
    reference_number = models.IntegerField()
    shipped_by = models.CharField(max_length=255)
    shippment_preference = models.CharField(max_length=255)
    created_by = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=50)

    class Meta:
        db_table = 'po_order_headers'
        managed = False  # Add this line to match other models

    def __str__(self):
        return self.po_number
    
class POOrderLines(models.Model):
    po_line_id = models.AutoField(primary_key=True)
    po_line_num = models.DecimalField(max_digits=10, decimal_places=1)
    po_header_id = models.IntegerField()
    po_number = models.CharField(max_length=50)
    product_id = models.CharField(max_length=120)
    product_name = models.CharField(max_length=255)
    priority = models.CharField(max_length=120)
    quantity_ordered = models.IntegerField()
    uom = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_invoice = models.IntegerField(default=0)
    quantity_received = models.IntegerField(default=0)
    quantity_accepted = models.IntegerField(default=0)
    quantity_rejected = models.IntegerField(default=0)
    status = models.CharField(max_length=50)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = '"pos_dev"."po_order_lines"'  # This explicitly tells Django to use "po_order_lines" table
        managed = False  # Since the table already exists

class PODrafts(models.Model):
    draft_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=50, default='Draft')
    # Supplier details
    supplier_name = models.CharField(max_length=255)
    supplier_address = models.CharField(max_length=255)
    supplier_city = models.CharField(max_length=255)
    supplier_region = models.CharField(max_length=255)
    supplier_phone_number = models.CharField(max_length=255)
    supplier_payment_terms = models.CharField(max_length=255)
    # Store details
    store_name = models.CharField(max_length=255)
    store_address = models.CharField(max_length=255)
    store_city = models.CharField(max_length=255)
    store_region = models.CharField(max_length=255)
    store_phone_number = models.CharField(max_length=255)
    # Order details
    reference_number = models.IntegerField(null=True)
    ordered_date = models.DateTimeField(null=True)
    expected_delivery_date = models.DateTimeField(null=True)
    shipped_by = models.CharField(max_length=255)
    shippment_preference = models.CharField(max_length=255)
    notes = models.CharField(max_length=255, null=True)
    # Product and cost details
    product_details = models.JSONField()
    cost_summary = models.JSONField()
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    other_adjustments = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'po_drafts'
        managed = False
