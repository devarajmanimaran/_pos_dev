from django.test import TestCase, Client
from django.urls import reverse
import json
from decimal import Decimal
from datetime import datetime, timedelta

class PriceHistoryViewTests(TestCase):
    fixtures = ['test_products.json', 'test_prices.json', 'test_gst.json']

    def setUp(self):
        self.client = Client()
        
    def test_price_history_basic(self):
        response = self.client.get(reverse('pricing:pricing_index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pricing/history.html')

    def test_price_history_filters(self):
        # Test exact product ID match
        response = self.client.get(reverse('pricing:pricing_index'), {'product_id': '1000'})
        self.assertEqual(response.status_code, 200)
        
        # Test LIKE product name match
        response = self.client.get(reverse('pricing:pricing_index'), {'product_name': 'Test'})
        self.assertEqual(response.status_code, 200)
        
        # Test exact category match
        response = self.client.get(reverse('pricing:pricing_index'), {'category_id': 'CAT1'})
        self.assertEqual(response.status_code, 200)

    def test_price_history_pagination(self):
        response = self.client.get(reverse('pricing:pricing_index'), {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertIn('pagination', response.context)
        self.assertEqual(response.context['pagination']['per_page'], 100)

class UpdatePriceViewTests(TestCase):
    fixtures = ['test_products.json', 'test_prices.json']

    def setUp(self):
        self.client = Client()
        self.update_url = reverse('pricing:update_price')

    def test_update_price_valid(self):
        data = {
            'product_id': '1000',
            'discount_price': '50.00'
        }
        response = self.client.post(
            self.update_url,
            data=json.dumps([data]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])

    def test_update_price_invalid_product(self):
        data = {
            'product_id': 'INVALID',
            'discount_price': '50.00'
        }
        response = self.client.post(
            self.update_url,
            data=json.dumps([data]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

class ExcelExportImportTests(TestCase):
    fixtures = ['test_products.json', 'test_prices.json']

    def setUp(self):
        self.client = Client()

    def test_download_excel(self):
        response = self.client.get(reverse('pricing:download_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_upload_excel_valid(self):
        # Create a test Excel file in memory
        import pandas as pd
        from io import BytesIO

        # Create test data
        df = pd.DataFrame({
            'Product ID': ['1000'],
            'Discount Price': [50.00]
        })

        # Save to buffer
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        # Upload the file
        response = self.client.post(
            reverse('pricing:upload_excel'),
            {'file': buffer},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
