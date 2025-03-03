from django.db import models
from django.apps import apps
from django.utils import timezone  # Add this import
from datetime import datetime
from .managers import PriceMasterManager  # Add this import


def get_model(model_name):
    try:
        return apps.get_model('pricing', model_name)
    except LookupError:
        return None


class GST(models.Model):
    category_id = models.CharField(max_length=50, primary_key=True)
    hsn_code = models.CharField(max_length=50)
    cgst = models.FloatField()  # Changed to FloatField for double precision
    sgst = models.FloatField()  # Changed to FloatField for double precision

    class Meta:
        db_table = 'gst'
        managed = False

    def save(self, *args, **kwargs):
        # Remove decimal point from category_id if present
        if self.category_id and '.' in self.category_id:
            self.category_id = self.category_id.split('.')[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.category_id).split('.')[0]


class Product(models.Model):
    product_id = models.CharField(max_length=50, primary_key=True)
    product_name = models.CharField(max_length=255)
    product_description = models.CharField(max_length=500)  # Added missing field
    product_status = models.CharField(max_length=50)  # Added missing field
    supplier_id = models.CharField(max_length=50)  # Added missing field
    category_id = models.ForeignKey(GST, on_delete=models.SET_NULL, null=True, db_column='category_id')
    shelf_life_days = models.IntegerField()  # Added missing field
    created_date = models.DateTimeField()
    updated_date = models.DateTimeField()  # Added missing field
    added_by = models.CharField(max_length=50)
    modified_by = models.CharField(max_length=50)

    class Meta:
        db_table = 'product'
        managed = False

    def __str__(self):
        return f"{self.product_id} - {self.product_name}"

    def get_category_id(self):
        """Return clean category ID without decimal"""
        if self.category_id:
            return str(self.category_id.category_id).split('.')[0]
        return None


class PriceMaster(models.Model):
    product = models.OneToOneField(Product, primary_key=True, on_delete=models.CASCADE, db_column='product_id')
    unit_cost = models.FloatField()  # Changed to FloatField for double precision
    unit_price = models.FloatField()  # Changed to FloatField for double precision
    discount_price = models.FloatField()  # Changed to FloatField for double precision
    added_by = models.CharField(max_length=50)
    modified_by = models.CharField(max_length=50)
    updated_on = models.DateTimeField()

    objects = PriceMasterManager()  # Replace the default manager with our custom one

    def save(self, *args, **kwargs):
        # Always use current system time without timezone
        self.updated_on = datetime.now().replace(microsecond=0)
        super().save(*args, **kwargs)

    def formatted_timestamp(self):
        return self.updated_on.strftime('%Y-%m-%d %H:%M:%S') if self.updated_on else ''

    class Meta:
        db_table = 'price_master'
        managed = False


class PricingHistory(models.Model):
    history_id = models.CharField(max_length=100, primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id')
    unit_cost = models.FloatField()  # Changed to FloatField for double precision
    unit_price = models.FloatField()  # Changed to FloatField for double precision
    discount_price = models.FloatField()  # Changed to FloatField for double precision
    discount_price_old = models.FloatField()  # Changed to FloatField for double precision
    updated_on = models.DateTimeField()
    added_by = models.CharField(max_length=50)
    modified_by = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        self.updated_on = datetime.now().replace(microsecond=0)
        super().save(*args, **kwargs)

    def formatted_timestamp(self):
        return self.updated_on.strftime('%Y-%m-%d %H:%M:%S') if self.updated_on else ''

    class Meta:
        db_table = 'pricing_history'
        managed = False