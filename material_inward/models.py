from django.db import models

# Create your models here.
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
        managed = False
