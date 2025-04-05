from django.db import models

class Product(models.Model):
    product_id = models.CharField(primary_key=True, max_length=255)
    product_name = models.CharField(max_length=255)
    product_description = models.CharField(max_length=255)
    product_status = models.CharField(max_length=255)
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

class Location(models.Model):
    location_id = models.CharField(primary_key=True, max_length=50)
    location_name = models.CharField(max_length=50)
    location_type = models.CharField(max_length=50)
    description = models.TextField(null=True)
    store_id = models.IntegerField()
    capacity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'location'

class PutawayIntransist(models.Model):
    putaway_id = models.AutoField(primary_key=True)
    po_line_id = models.IntegerField()
    location_name = models.CharField(max_length=50)
    # Changed from ForeignKey to CharField to match product table's type
    product_id = models.CharField(max_length=255)
    quantity = models.IntegerField()
    status = models.CharField(max_length=50)

    # Add property to get related product
    @property
    def product(self):
        return Product.objects.get(product_id=self.product_id)

    class Meta:
        managed = False
        db_table = 'putaway_intransist'
