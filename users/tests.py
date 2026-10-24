from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from master.models import BusinessType, BusinessCategory
from users.models import Profile, OTPRecord, RegistrationToken
from users.services import hash_otp


class AuthViewTests(TestCase):
    """Tests for the unified POST /api/users/auth/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/auth/'
        self.plain_otp = '123456'
        self.otp_hash = hash_otp(self.plain_otp)

    def _create_otp(self, mobile='9876543210', purpose='login', expired=False, used=False):
        expires = timezone.now() + (timedelta(minutes=-1) if expired else timedelta(minutes=5))
        return OTPRecord.objects.create(
            mobile_number=mobile,
            otp_hash=self.otp_hash,
            purpose=purpose,
            expires_at=expires,
            is_used=used,
        )

    # ─── Step 1: Send mobile_number only ───

    def test_new_user_gets_register_action(self):
        resp = self.client.post(self.url, {'mobile_number': '9876543210'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['action'], 'register')
        self.assertTrue(OTPRecord.objects.filter(mobile_number='9876543210', purpose='register').exists())

    def test_existing_user_gets_login_action(self):
        user = User.objects.create_user(username='9876543210', password=None)
        Profile.objects.create(user=user, mobile_number='9876543210')

        resp = self.client.post(self.url, {'mobile_number': '9876543210'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['action'], 'login')

    def test_invalid_mobile_number(self):
        resp = self.client.post(self.url, {'mobile_number': '12345'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_cooldown(self):
        self.client.post(self.url, {'mobile_number': '9876543210'})
        resp = self.client.post(self.url, {'mobile_number': '9876543210'})
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    # ─── Step 2: Send mobile_number + otp ───

    def test_login_with_correct_otp(self):
        user = User.objects.create_user(username='9876543210', password=None)
        Profile.objects.create(user=user, mobile_number='9876543210')
        self._create_otp(purpose='login')

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': self.plain_otp,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['action'], 'login')
        self.assertIn('access_token', resp.data)
        self.assertIn('refresh_token', resp.data)
        self.assertIn('user', resp.data)

    def test_register_with_correct_otp(self):
        self._create_otp(purpose='register')

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': self.plain_otp,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['action'], 'complete_profile')
        self.assertIn('registration_token', resp.data)

    def test_invalid_otp(self):
        self._create_otp(purpose='login')
        user = User.objects.create_user(username='9876543210', password=None)
        Profile.objects.create(user=user, mobile_number='9876543210')

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': '000000',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['success'])

    def test_expired_otp(self):
        self._create_otp(purpose='login', expired=True)

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': self.plain_otp,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_used_otp(self):
        self._create_otp(purpose='login', used=True)

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': self.plain_otp,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_max_attempts_exceeded(self):
        otp_rec = self._create_otp(purpose='login')
        otp_rec.failed_attempts = 5
        otp_rec.save()
        user = User.objects.create_user(username='9876543210', password=None)
        Profile.objects.create(user=user, mobile_number='9876543210')

        resp = self.client.post(self.url, {
            'mobile_number': '9876543210',
            'otp': self.plain_otp,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Maximum', resp.data['message'])


class RegisterProfileTests(TestCase):
    """Tests for POST /api/users/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/register/'
        self.bt1 = BusinessType.objects.create(name='Manufacturer')
        self.bt2 = BusinessType.objects.create(name='Retailer')
        self.bc = BusinessCategory.objects.create(name='Technology')

    def _create_reg_token(self, mobile='9876543210', expired=False, used=False):
        expires = timezone.now() + (timedelta(minutes=-1) if expired else timedelta(minutes=15))
        return RegistrationToken.objects.create(
            mobile_number=mobile,
            expires_at=expires,
            is_used=used,
        )

    def test_successful_registration(self):
        reg_token = self._create_reg_token()
        resp = self.client.post(self.url, {
            'registration_token': str(reg_token.token),
            'first_name': 'Nihal',
            'last_name': 'Kumar',
            'email': 'nihal@example.com',
            'date_of_birth': '2005-05-15',
            'business_name': 'Nihal Technologies',
            'business_type_ids': [self.bt1.id, self.bt2.id],
            'business_category_id': self.bc.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['success'])
        self.assertIn('access_token', resp.data)
        self.assertEqual(resp.data['user']['first_name'], 'Nihal')
        self.assertEqual(len(resp.data['user']['business_types']), 2)
        reg_token.refresh_from_db()
        self.assertTrue(reg_token.is_used)

    def test_expired_registration_token(self):
        reg_token = self._create_reg_token(expired=True)
        resp = self.client.post(self.url, {
            'registration_token': str(reg_token.token),
            'first_name': 'Nihal',
            'last_name': 'Kumar',
            'email': 'nihal@example.com',
            'date_of_birth': '2005-05-15',
            'business_type_ids': [self.bt1.id],
            'business_category_id': self.bc.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_used_registration_token(self):
        reg_token = self._create_reg_token(used=True)
        resp = self.client.post(self.url, {
            'registration_token': str(reg_token.token),
            'first_name': 'Nihal',
            'last_name': 'Kumar',
            'email': 'nihal@example.com',
            'date_of_birth': '2005-05-15',
            'business_type_ids': [self.bt1.id],
            'business_category_id': self.bc.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_mobile(self):
        user = User.objects.create_user(username='9876543210', password=None)
        Profile.objects.create(user=user, mobile_number='9876543210')
        reg_token = self._create_reg_token()

        resp = self.client.post(self.url, {
            'registration_token': str(reg_token.token),
            'first_name': 'Nihal',
            'last_name': 'Kumar',
            'email': 'nihal@example.com',
            'date_of_birth': '2005-05-15',
            'business_type_ids': [self.bt1.id],
            'business_category_id': self.bc.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email(self):
        User.objects.create_user(username='other', email='nihal@example.com', password='pass')
        reg_token = self._create_reg_token()

        resp = self.client.post(self.url, {
            'registration_token': str(reg_token.token),
            'first_name': 'Nihal',
            'last_name': 'Kumar',
            'email': 'nihal@example.com',
            'date_of_birth': '2005-05-15',
            'business_type_ids': [self.bt1.id],
            'business_category_id': self.bc.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MasterDataTests(TestCase):
    """Tests for master data APIs."""

    def setUp(self):
        self.client = APIClient()
        BusinessType.objects.create(name='Manufacturer', is_active=True)
        BusinessType.objects.create(name='Inactive Type', is_active=False)
        BusinessCategory.objects.create(name='Technology', is_active=True)
        BusinessCategory.objects.create(name='Inactive Category', is_active=False)

    def test_business_types_returns_only_active(self):
        resp = self.client.get('/api/master/business-types/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(len(resp.data['data']), 1)

    def test_business_categories_returns_only_active(self):
        resp = self.client.get('/api/master/business-categories/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        self.assertEqual(len(resp.data['data']), 1)
