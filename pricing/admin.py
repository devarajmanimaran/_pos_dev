from django.contrib import admin
from .models import Product, GST, PriceMaster, PricingHistory

admin.site.register(Product)
admin.site.register(GST)
admin.site.register(PriceMaster)
admin.site.register(PricingHistory)
