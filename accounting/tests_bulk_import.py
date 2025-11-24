from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from .models import Account, JournalEntry, TransactionLine

User = get_user_model()

class BulkImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='u2@example.com', password='pass', role='comptable')
        self.client.force_authenticate(self.user)
        # create an account that will be linked
        self.account = Account.objects.create(owner=self.user, numero='411000', intitule='Clients', classe=4, type='Actif')

    def test_import_simple(self):
        payload = {
            'entries': [
                {
                    'date':'2025-01-15',
                    'reference':'FAC001',
                    'numeroEcriture':'ECR001',
                    'libelle':'Vente test',
                    'nature':'Vente',
                    'lines': [
                        {'accountNumber':'411000','accountName':'Clients','debit':12000,'credit':0,'calculatedAmount':12000,'percentage':100,'nature':'V'},
                        {'accountNumber':'701000','accountName':'Prod','debit':0,'credit':12000,'calculatedAmount':12000,'percentage':100,'nature':'P'},
                    ]
                }
            ]
        }
        resp = self.client.post('/api/entries/bulk-import/', payload, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['created'], 1)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(TransactionLine.objects.count(), 2)

    def test_duplicate(self):
        # create existing entry
        je = JournalEntry.objects.create(date='2025-02-01', libelle='L', reference='R', numeroEcriture='E_DUP')
        payload = {
            'entries': [
                {'date':'2025-02-01','reference':'R2','numeroEcriture':'E_DUP','libelle':'L2','nature':'N','lines':[{'accountNumber':'411000','debit':10,'credit':0}]}
            ]
        }
        resp = self.client.post('/api/entries/bulk-import/', payload, format='json')
        self.assertEqual(resp.status_code, 409)

    def test_invalid_line(self):
        payload = {'entries':[{'date':'2025-03-01','reference':'R','numeroEcriture':'E3','libelle':'L3','lines':[{'accountNumber':'411000','debit':0,'credit':0}]}]}
        resp = self.client.post('/api/entries/bulk-import/', payload, format='json')
        self.assertEqual(resp.status_code, 400)
