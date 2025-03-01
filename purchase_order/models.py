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
    
class Product(models.Model):
    product_id = models.CharField(primary_key=True, max_length=255)
    product_name = models.CharField(max_length=255)
    product_description = models.CharField(max_length=255)
    product_status = models.CharField(max_length=255)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, db_column='supplier_id')
    category_id = models.CharField(max_length=255)
    shelf_life_days = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    added_by = models.CharField(max_length=255)
    modified_by = models.CharField(max_length=255)

    class Meta:
        db_table = 'product'  # Changed from 'Product' to lowercase 'product'
        managed = False

    def __str__(self):
        return self.product_name

class ProductCategory(models.Model):
    category_id = models.CharField(primary_key=True, max_length=255)
    category_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'product_category'  # Changed from 'Product_Category' to lowercase 'product_category'
        managed = False

    def __str__(self):
        return self.category_name

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
    created_by = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'po_order_headers'
        managed = False

    def __str__(self):
        return self.po_number

class POOrderLines(models.Model):
    po_line_id = models.AutoField(primary_key=True)
    po_line_num = models.DecimalField(max_digits=10, decimal_places=2)
    po_header_id = models.IntegerField()
    po_number = models.CharField(max_length=50)
    priority = models.CharField(max_length=120)
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255)
    quantity_ordered = models.IntegerField()
    uom = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_invoice = models.IntegerField(null=True)
    quantity_received = models.IntegerField(null=True)
    quantity_accepted = models.IntegerField(null=True)
    quantity_rejected = models.IntegerField(null=True)
    status = models.CharField(max_length=50)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = '"pos_dev"."po_order_lines"'
        managed = False

    def __str__(self):
        return f"{self.po_number} - {self.product_name}"

class ProductSupplierCost(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id', related_name='supplier_costs')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, db_column='supplier_id', related_name='product_costs')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, db_column='unit_cost')
    last_updated = models.DateTimeField(db_column='last_updated')
    moq = models.IntegerField(db_column='moq')
    
    class Meta:
        db_table = 'product_supplier_cost'
        managed = False
        unique_together = ('product', 'supplier')
        abstract = False

    def __str__(self):
        return f"{self.product.product_name} - {self.supplier.supplier_name}"