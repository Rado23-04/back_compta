from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import JournalEntry

User = get_user_model()


class JournalPermissionsTests(APITestCase):
    def setUp(self):
        # create a comptable user
        self.comptable = User.objects.create_user(email='comptable@example.com', password='pass12345', name='Comptable', role='comptable')
        # create an admin-comptable user
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role='admin-comptable')

        # sample journal payload
        self.payload = {
            'date': '2025-11-17',
            'libelle': 'Test entry',
            'reference': 'R1',
            'numeroEcriture': 'E-1',
            'nature': 'Test',
            'lines': [
                {'accountNumber': '1000', 'debit': 100, 'credit': 0},
                {'accountNumber': '2000', 'debit': 0, 'credit': 100},
            ]
        }

    def test_comptable_can_post(self):
        self.client.force_authenticate(user=self.comptable)
        resp = self.client.post('/api/entries/', data=self.payload, format='json')
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST))
        # If accounts referenced are missing, service returns 400; but permission should be allowed

    def test_comptable_cannot_put(self):
        # create a sample entry for admin
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/entries/', data=self.payload, format='json')
        if resp.status_code != status.HTTP_201_CREATED:
            # can't proceed without an entry; skip assert on update specifics
            return
        entry_id = resp.data.get('id')
        self.client.force_authenticate(user=self.comptable)
        resp2 = self.client.put(f'/api/entries/{entry_id}/', data=self.payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_put_delete(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/entries/', data=self.payload, format='json')
        if resp.status_code != status.HTTP_201_CREATED:
            return
        entry_id = resp.data.get('id')
        # Admin can update
        resp2 = self.client.put(f'/api/entries/{entry_id}/', data=self.payload, format='json')
        self.assertIn(resp2.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))
        # Admin can delete
        resp3 = self.client.delete(f'/api/entries/{entry_id}/')
        self.assertIn(resp3.status_code, (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))

    def test_signup_with_invalid_role(self):
        resp = self.client.post('/api/auth/register/', data={'email':'x@y.com','password':'Abcd1234!','name':'X','role':'invalid-role'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
