from django import forms
from .models import Product, PriceMaster

class PriceUpdateForm(forms.ModelForm):
    class Meta:
        model = PriceMaster
        fields = ['discount_price']

    def clean_discount_price(self):
        price = self.cleaned_data['discount_price']
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero")
        return price

class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'category_id']
