from django.db import models

class Supplier(models.Model):
    supplier_id = models.CharField(primary_key=True, max_length=255)
    supplier_name = models.CharField(max_length=255)
    landline_number = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    payment_terms = models.CharField(max_length=50)
    is_active = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'supplier'

class GeoLocation(models.Model):
    state = models.CharField(primary_key=True, max_length=255)  # Make state the primary key
    city = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'geo_location'
        unique_together = ('state', 'city')  # Ensure state-city combination is unique
