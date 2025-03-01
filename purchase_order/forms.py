from django import forms
from .models import POOrderHeader, Product, Supplier

class POOrderHeaderForm(forms.ModelForm):
    PRIORITY_CHOICES = [
        ('None', 'None'),
        ('Critical', 'Critical'),
        ('Non Critical', 'Non Critical'),
    ]

    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, initial='None')
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=False, widget=forms.HiddenInput())
    order_date = forms.DateTimeField(required=False, widget=forms.HiddenInput())
    total_order_value = forms.DecimalField(max_digits=10, decimal_places=2, initial=0.00, required=False, widget=forms.HiddenInput())

    class Meta:
        model = POOrderHeader
        fields = ['po_number', 'supplier', 'order_date', 'total_order_value', 'priority']

class ProductForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), label="Product Name")
    category = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'readonly': True}), label="Category")
    order_qty = forms.IntegerField(min_value=1, label="Order Qty")