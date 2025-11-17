from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTests(APITestCase):
    def test_register(self):
        url = '/api/auth/register/'
        data = {
            'email': 'testuser@example.com',
            'password': 'strongpassword123',
            'name': 'Test User',
            'role': 'comptable',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', resp.data)
        self.assertIn('user', resp.data)
        self.assertEqual(resp.data['user']['email'], data['email'])

    def test_login(self):
        # Create user first
        user = User.objects.create_user(email='loginuser@example.com', password='mypassword123', name='Login', role='comptable')
        url = '/api/auth/login/'
        data = {
            'email': 'loginuser@example.com',
            'password': 'mypassword123',
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('token', resp.data)
        self.assertIn('user', resp.data)
