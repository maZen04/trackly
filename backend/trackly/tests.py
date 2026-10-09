from django.test import TestCase
from django.urls import reverse
from .models import User, Monitor
from rest_framework import status
from rest_framework.test import APITestCase
from .views import RegisterView, LoginView


class AuthTests(APITestCase):
    def setUp(self):
        # run before each one of the tests
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.refresh_url = reverse('refresh')
        self.logout_url = reverse('user-logout')

        RegisterView.throttle_classes = []

        self.data = {
            "email":"mazen1@test.com",
            "password":"StrongPass123"
        }
        self.invalid_data1 = {
            "email":"mazen1@test.com",
            "password":"123456"
        }
        self.invalid_data2 = {
            "email":"mazen1@",
            "password":"123456"
        }
        
    def test_register_success(self):
        response = self.client.post(self.register_url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'mazen1@test.com')

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="mazen1@test.com",
            password="StrongPass123"
        )
        response = self.client.post(self.register_url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_register_weak_password(self):
        response = self.client.post(self.register_url, self.invalid_data1, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
    
    def test_register_invalid_data(self):
        response = self.client.post(self.register_url, self.invalid_data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_login_success(self):
        User.objects.create_user(
            email="mazen1@test.com",
            password="StrongPass123"
        )
        response = self.client.post(self.login_url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_invalid_data(self):
        User.objects.create_user(
            email="mazen1@test.com",
            password="StrongPass111"
        )
        response = self.client.post(self.login_url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_success(self):
        refresh_token = self.client.post(self.register_url, self.data, format='json').data
        refresh_token = {
            "refresh":refresh_token['refresh']
        }
        response = self.client.post(self.refresh_url, refresh_token, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_refresh_invalid_data(self):
        refresh_token = self.client.post(self.register_url, self.data, format='json').data
        refresh_token = {
            "refresh":refresh_token['refresh'][:-2]
        }
        response = self.client.post(self.refresh_url, refresh_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout_success(self):
        token = self.client.post(self.register_url, self.data)
        access_token = token.data['access']
        refresh_token = token.data['refresh']
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        data = {
            "refresh":refresh_token
        }
        response = self.client.post(self.logout_url, data, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        def test_logout_non_registered(self):
                token = self.client.post(self.register_url, self.data)
                refresh_token = token.data['refresh']
                data = {
                    "refresh":refresh_token
                }
                response = self.client.post(self.logout_url, data, headers=headers)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



class MonitorTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('user-register')
        self.monitor_url = reverse('monitor')
        # self.snapshots_url = reverse('monitor-changes')

        RegisterView.throttle_classes = []
        LoginView.throttle_classes = []

        self.user = User.objects.create_user(
            email='mazen1@test.com',
            password='StrongPass123'
        )
        self.client.force_authenticate(user=self.user)

        monitor = Monitor.objects.create(
            url="https://example.com",
            user=self.user
        )
        self.monitor_details_url = reverse(
            'monitor-detail',
            kwargs={'pk': monitor.pk}
        )

        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="StrongPass123"
        )


    def test_create_monitor_success1(self):
        data = {"url":"https://chatgpt.com/c/6ac5d002-ee3c-83ea-aa36-8c88d36f3c3d"}
        response = self.client.post(self.monitor_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Monitor.objects.count(), 2)

    def test_create_monitor_success2(self):
        data = {
            "url":"https://chatgpt.com/c/6ac5d002-ee3c-83ea-aa36-8c88d36f3c3d",
            "check_interval":60
        }
        response = self.client.post(self.monitor_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Monitor.objects.count(), 2)
    
    def test_create_monitor_requires_url(self):
        data = {"check_interval":60}
        response = self.client.post(self.monitor_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Monitor.objects.count(), 1)

    def test_create_monitor_rejects_invalid_url(self):
        data = {
            "url":"https://chatgpt/c/6ac5d002-ee3c-83ea-aa36-8c88d36f3c3d",
            "check_interval":60
        }
        response = self.client.post(self.monitor_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_only_see_own_monitors(self):
        data = {
            "url":"https://chatgpt.com/c/6ac5d002-ee3c-83ea-aa36-8c88d36f3c3d",
            "check_interval":60
        }
        Monitor.objects.create(
            url=data['url'],
            user=self.other_user
        )

        response = self.client.get(self.monitor_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_duplicate_url_is_rejected(self):
        data = {
            "url":"https://chatgpt.com/c/6ac5d002-ee3c-83ea-aa36-8c88d36f3c3d",
            "check_interval":60
        }
        first_request =  self.client.post(self.monitor_url, data)
        self.assertEqual(Monitor.objects.count(), 2)
        response = self.client.post(self.monitor_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Monitor.objects.count(), 2)

    def test_user_cannot_update_other_user_monitor(self):
        monitor = Monitor.objects.create(
            url="https://example.com",
            check_interval=60,
            user=self.other_user
        )
        url = reverse(
            'monitor-detail',
            kwargs={'pk': monitor.pk}
        )

        data = {
            "url": "https://changed.com",
            "check_interval": 120
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        monitor.refresh_from_db()

        self.assertEqual(monitor.url, "https://example.com")
        self.assertEqual(monitor.check_interval, 60)