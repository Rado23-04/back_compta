from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
import io
import pandas as pd

User = get_user_model()


class ExcelImportTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(email='u@example.com', password='pass', role='comptable')
		self.client.force_authenticate(self.user)

	def make_excel_bytes(self, rows):
		df = pd.DataFrame(rows)
		buf = io.BytesIO()
		df.to_excel(buf, index=False, engine='openpyxl')
		buf.seek(0)
		return buf

	def test_import_success(self):
		rows = [
			{'date':'2025-01-01','reference':'REF1','numeroEcriture':'ECR001','libelle':'Vente','nature':'Opération','account':'50','accountName':'Sales','debit':100.0,'credit':0.0,'calculatedAmount':100.0,'percentage':0,'lineNature':'something'},
			{'date':'2025-01-01','reference':'REF1','numeroEcriture':'ECR001','libelle':'Vente','nature':'Opération','account':'51','accountName':'Other','debit':0.0,'credit':100.0,'calculatedAmount':100.0,'percentage':0,'lineNature':'something'},
		]
		buf = self.make_excel_bytes(rows)
		resp = self.client.post('/api/entries/import-excel/', {'file': buf}, format='multipart')
		self.assertEqual(resp.status_code, 201)
		self.assertIn('created_entries', resp.data)

	def test_empty_sheet(self):
		# empty df
		buf = self.make_excel_bytes([])
		resp = self.client.post('/api/entries/import-excel/', {'file': buf}, format='multipart')
		self.assertEqual(resp.status_code, 400)

	def test_missing_columns(self):
		rows = [{'a':1,'b':2}]
		buf = self.make_excel_bytes(rows)
		resp = self.client.post('/api/entries/import-excel/', {'file': buf}, format='multipart')
		self.assertEqual(resp.status_code, 400)

	def test_grouping_of_lines(self):
		rows = [
			{'date':'2025-01-02','reference':'R2','numeroEcriture':'E2','libelle':'L1','nature':'N','account':'60','accountName':'A','debit':50,'credit':0,'calculatedAmount':50,'percentage':0,'lineNature':'x'},
			{'date':'2025-01-02','reference':'R2','numeroEcriture':'E2','libelle':'L1','nature':'N','account':'61','accountName':'B','debit':0,'credit':50,'calculatedAmount':50,'percentage':0,'lineNature':'y'},
			{'date':'2025-01-03','reference':'R3','numeroEcriture':'E3','libelle':'L2','nature':'N','account':'62','accountName':'C','debit':20,'credit':0,'calculatedAmount':20,'percentage':0,'lineNature':'z'},
		]
		buf = self.make_excel_bytes(rows)
		resp = self.client.post('/api/entries/import-excel/', {'file': buf}, format='multipart')
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(resp.data['created_entries'], 2)
