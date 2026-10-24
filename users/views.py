from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile, OTPRecord, RegistrationToken, Subscription
from .serializers import AuthSerializer, RegisterProfileSerializer, CheckUserSerializer
from .services import create_otp_record, can_resend_otp, verify_otp_hash


def _get_tokens_for_user(user):
    """Generate JWT access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }


def _build_user_response(user, profile, request=None):
    """Build the user profile dict for API responses."""
    from master.serializers import BusinessTypeSerializer, BusinessCategorySerializer, CitySerializer
    
    # In case we pass User as the object but want profile fields
    if not profile:
        profile = user.profile
        
    # Get subscription data
    from .serializers import SubscriptionSerializer
    subscription_data = None
    if hasattr(profile, 'subscription'):
        subscription_data = SubscriptionSerializer(profile.subscription).data

    from .models import GeneratedPoster
    from dashboard.models import AnalyticsEvent
    designs_count = GeneratedPoster.objects.filter(profile=profile).count() if profile else 0
    downloads_count = AnalyticsEvent.objects.filter(user=user, event_type='poster_export').count() if user else 0
    templates_count = AnalyticsEvent.objects.filter(user=user, event_type__in=['template_view', 'template_edit']).count() if user else 0

    return {
        'id': user.id,
        'mobile_number': profile.mobile_number,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'date_of_birth': str(profile.date_of_birth) if profile.date_of_birth else None,
        'business_name': profile.business_name,
        'business_types': BusinessTypeSerializer(profile.business_types.all(), many=True).data,
        'business_category': BusinessCategorySerializer(profile.business_category).data if profile.business_category else None,
        'city': CitySerializer(profile.city).data if profile.city else None,
        'profile_picture': request.build_absolute_uri(profile.profile_picture.url) if (profile.profile_picture and request) else (profile.profile_picture.url if profile.profile_picture else None),
        'subscription': subscription_data,
        'designs_count': designs_count,
        'templates_count': templates_count,
        'downloads_count': downloads_count,
    }


class CheckUserView(APIView):

    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # If the request reaches here, the JWT token is valid and the user exists.
        return Response({
            'success': True,
            'exists': True,
            'message': 'User exists and token is valid.'
        }, status=status.HTTP_200_OK)


class CheckSubscriptionView(APIView):
    """
    GET /api/users/check-subscription/
    
    Checks if the authenticated user is subscribed (has an active paid plan).
    Must pass JWT token in Authorization header.
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            subscription = profile.subscription
            is_subscribed = subscription.plan_name.lower() != 'free' and not subscription.is_expired and subscription.is_active
            
            return Response({
                'success': True,
                'is_subscribed': bool(is_subscribed),
                'plan_name': subscription.plan_name,
                'days_left': subscription.days_left,
                'credits_available': subscription.credits_available
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist: # fallback if somehow missing
            return Response({
                'success': True,
                'is_subscribed': False,
                'plan_name': 'Free',
                'days_left': 0,
                'credits_available': 0
            }, status=status.HTTP_200_OK)


class AuthView(APIView):
    """
    POST /api/users/auth/

    Single endpoint for mobile-number authentication:

    Step 1 — Send only mobile_number:
        → Checks if user exists (login/register)
        → Generates & sends OTP
        → Returns action: "login" or "register"

    Step 2 — Send mobile_number + otp:
        → Verifies OTP
        → If existing user: returns JWT tokens + user profile (login)
        → If new user: returns registration_token (complete_profile)
    """ 
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data['mobile_number']
        otp = (serializer.validated_data.get('otp') or '').strip()

        user_exists = Profile.objects.filter(mobile_number=mobile).exists()
        action = 'login' if user_exists else 'register'

        # ─── STEP 1: No OTP provided → Send OTP ───
        if not otp:
            if not can_resend_otp(mobile):
                cooldown = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
                return Response({
                    'success': False,
                    'message': f'Please wait {cooldown} seconds before requesting a new OTP.',
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            otp_record_val = create_otp_record(mobile, action)

            return Response({
                'success': True,
                'message': f'{"Login" if user_exists else "Registration"} OTP sent successfully.',
                'action': action,
                'mobile_number': mobile,
                'otp': otp_record_val, # Included for easier API testing
            })

        # ─── STEP 2: OTP provided → Verify OTP ───
        otp_record = OTPRecord.objects.filter(
            mobile_number=mobile,
            purpose=action,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        if not otp_record:
            return Response({
                'success': False,
                'message': 'OTP has expired or is invalid. Please request a new one.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check max attempts
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        if otp_record.failed_attempts >= max_attempts:
            return Response({
                'success': False,
                'message': 'Maximum OTP verification attempts exceeded. Please request a new OTP.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify OTP hash
        if not verify_otp_hash(otp, otp_record.otp_hash):
            otp_record.failed_attempts += 1
            otp_record.save(update_fields=['failed_attempts'])
            remaining = max_attempts - otp_record.failed_attempts
            return Response({
                'success': False,
                'message': f'Invalid OTP. {remaining} attempt(s) remaining.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        # ─── LOGIN ───
        if action == 'login':
            try:
                profile = Profile.objects.select_related('user').get(mobile_number=mobile)
            except Profile.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'User profile not found.',
                }, status=status.HTTP_404_NOT_FOUND)

            tokens = _get_tokens_for_user(profile.user)
            user_data = _build_user_response(profile.user, profile, request)
            return Response({
                'success': True,
                'message': 'Login successful.',
                'action': 'login',
                **tokens,
                'user': user_data,
            })

        # ─── REGISTER → issue registration token ───
        if Profile.objects.filter(mobile_number=mobile).exists():
            return Response({
                'success': False,
                'message': 'User with this mobile number already exists. Please login instead.',
            }, status=status.HTTP_400_BAD_REQUEST)

        expiry_minutes = getattr(settings, 'REGISTRATION_TOKEN_EXPIRY_MINUTES', 15)
        reg_token = RegistrationToken.objects.create(
            mobile_number=mobile,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )
        
        # Fetch dropdowns for the frontend
        from master.models import BusinessCategory, BusinessType
        from master.serializers import BusinessCategorySerializer, BusinessTypeSerializer
        
        categories = BusinessCategory.objects.filter(is_active=True)
        types = BusinessType.objects.filter(is_active=True)

        return Response({
            'success': True,
            'message': 'Mobile number verified successfully.',
            'action': 'complete_profile',
            'registration_token': str(reg_token.token),
            'dropdowns': {
                'business_categories': BusinessCategorySerializer(categories, many=True).data,
                'business_types': BusinessTypeSerializer(types, many=True).data,
            }
        })


class RegisterProfileView(APIView):
    """
    POST /api/users/register/
    Creates user profile after OTP-verified registration.
    Requires the temporary registration_token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate registration token
        try:
            reg_token = RegistrationToken.objects.get(token=data['registration_token'])
        except RegistrationToken.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid registration token.',
            }, status=status.HTTP_400_BAD_REQUEST)

        if reg_token.is_used:
            return Response({
                'success': False,
                'message': 'Registration token has already been used.',
            }, status=status.HTTP_400_BAD_REQUEST)

        if reg_token.expires_at < timezone.now():
            return Response({
                'success': False,
                'message': 'Registration token has expired. Please restart registration.',
            }, status=status.HTTP_400_BAD_REQUEST)

        mobile = reg_token.mobile_number

        # Prevent duplicate user
        if Profile.objects.filter(mobile_number=mobile).exists():
            return Response({
                'success': False,
                'message': 'User with this mobile number already exists.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create User + Profile inside a transaction
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=mobile,
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    password=None,
                )
                user.set_unusable_password()
                user.save()

                profile = Profile.objects.create(
                    user=user,
                    mobile_number=mobile,
                    date_of_birth=data['date_of_birth'],
                    business_name=data.get('business_name', ''),
                    business_category_id=data['business_category_id'],
                )
                profile.business_types.set(data['business_type_ids'])

                reg_token.is_used = True
                reg_token.save(update_fields=['is_used'])

        except Exception as e:
            return Response({
                'success': False,
                'message': f'Registration failed: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        tokens = _get_tokens_for_user(user)
        user_data = _build_user_response(user, profile, request)

        return Response({
            'success': True,
            'message': 'Profile created successfully.',
            **tokens,
            'user': user_data,
        }, status=status.HTTP_201_CREATED)


class ProfileView(APIView):
    """
    GET /api/users/profile/
    POST /api/users/profile/ (or PUT)
    
    Fetch and update user profile.
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        if not profile:
            return Response({
                'success': False,
                'message': 'Profile not found.',
            }, status=status.HTTP_404_NOT_FOUND)

        # We can reuse _build_user_response
        user_data = _build_user_response(user, profile, request)

        return Response({
            'success': True,
            'data': user_data,
        })

    def post(self, request):
        return self.put(request)

    def put(self, request):
        from .serializers import UserProfileUpdateSerializer
        user = request.user
        profile = getattr(user, 'profile', None)
        if not profile:
            return Response({
                'success': False,
                'message': 'Profile not found.',
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UserProfileUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update User fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'email' in data:
            user.email = data['email']
        user.save()

        # Update Profile fields
        if 'business_name' in data:
            profile.business_name = data['business_name']
        if 'city_id' in data:
            profile.city_id = data['city_id']
        
        # Profile Picture
        if 'profile_picture' in data:
            # If a new image is provided or cleared
            if data['profile_picture'] is None:
                if profile.profile_picture:
                    profile.profile_picture.delete(save=False)
                    profile.profile_picture = None
            else:
                if profile.profile_picture:
                    profile.profile_picture.delete(save=False)
                profile.profile_picture = data['profile_picture']

        profile.save()

        user_data = _build_user_response(user, profile, request)

        return Response({
            'success': True,
            'message': 'Profile updated successfully.',
            'data': user_data,
        })


from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from .models import BrandKit
from .serializers import BrandKitSerializer

class BrandKitView(APIView):
    """
    API endpoint for getting and creating the user's Brand Kits.
    Supports multipart form data for image uploads.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        brand_kits = BrandKit.objects.filter(profile=profile).order_by('-created_at')
        serializer = BrandKitSerializer(brand_kits, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
        })

    def post(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BrandKitSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(profile=profile)
            return Response({
                'success': True,
                'message': 'Brand kit created successfully.',
                'data': serializer.data,
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Failed to create brand kit.',
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

class BrandKitDetailView(APIView):
    """
    API endpoint for retrieving, updating or deleting a specific Brand Kit.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk, profile):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(BrandKit, pk=pk, profile=profile)

    def get(self, request, pk):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        brand_kit = self.get_object(pk, profile)
        serializer = BrandKitSerializer(brand_kit, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    def put(self, request, pk):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        brand_kit = self.get_object(pk, profile)
        serializer = BrandKitSerializer(brand_kit, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Brand kit updated successfully.',
                'data': serializer.data,
            })
        return Response({
            'success': False,
            'message': 'Failed to update brand kit.',
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        brand_kit = self.get_object(pk, profile)
        brand_kit.delete()
        return Response({'success': True, 'message': 'Brand kit deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class SubscriptionView(APIView):
    """
    GET /api/users/subscription/
    Fetch the current user's subscription details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if not hasattr(profile, 'subscription'):
            return Response({'success': False, 'message': 'Subscription not found for this profile.'}, status=status.HTTP_404_NOT_FOUND)
            
        from .serializers import SubscriptionSerializer
        serializer = SubscriptionSerializer(profile.subscription)
        
        return Response({
            'success': True,
            'data': serializer.data,
        })
        
    def post(self, request):
        """
        POST /api/users/subscription/
        Purchase a subscription plan.
        Requires 'plan_id' in request data.
        """
        from master.models import SubscriptionPlan
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({'success': False, 'message': 'plan_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'success': False, 'message': 'Invalid or inactive plan.'}, status=status.HTTP_404_NOT_FOUND)
            
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        subscription = getattr(profile, 'subscription', None)
        if not subscription:
            from .models import Subscription
            subscription = Subscription.objects.create(profile=profile)
            
        subscription.plan_name = plan.name
        subscription.credits_available += plan.credits
        
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        # If active and not expired, extend the end date
        if subscription.end_date and subscription.end_date > now:
            subscription.end_date = subscription.end_date + datetime.timedelta(days=plan.duration_days)
        else:
            subscription.end_date = now + datetime.timedelta(days=plan.duration_days)
            
        subscription.is_active = True
        subscription.save()
        
        # Record the transaction
        from .models import Transaction
        Transaction.objects.create(
            profile=profile,
            plan_name=plan.name,
            transaction_type='subscription',
            amount=plan.price,
            status='completed',
            payment_method='api'
        )
        
        from .serializers import SubscriptionSerializer
        return Response({
            'success': True,
            'message': 'Subscription purchased successfully.',
            'data': SubscriptionSerializer(subscription).data
        })


class GeneratedPosterCreateView(APIView):
    """
    POST /api/users/generated-posters/
    Upload a generated poster.
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .serializers import GeneratedPosterSerializer
        serializer = GeneratedPosterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(profile=request.user.profile)
            return Response({
                'success': True,
                'message': 'Poster saved successfully.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class GeneratedPosterListView(APIView):
    """
    GET /api/users/generated-posters/list/
    List generated posters for the authenticated user.
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import GeneratedPosterSerializer
        from .models import GeneratedPoster
        posters = GeneratedPoster.objects.filter(profile=request.user.profile).order_by('-created_at')
        serializer = GeneratedPosterSerializer(posters, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })


class PaymentAPIView(APIView):
    """
    POST /api/users/payment/
    Submit a payment to activate a subscription.
    Expected data:
    - plan_id (int)
    - amount (float)
    - payment_mode (str)
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from master.models import SubscriptionPlan
        
        plan_id = request.data.get('plan_id')
        amount = request.data.get('amount')
        payment_mode = request.data.get('payment_mode')
        
        if not all([plan_id, amount, payment_mode]):
            return Response({
                'success': False,
                'message': 'plan_id, amount, and payment_mode are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'success': False, 'message': 'Invalid or inactive plan.'}, status=status.HTTP_404_NOT_FOUND)
            
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({'success': False, 'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        subscription = getattr(profile, 'subscription', None)
        if not subscription:
            from .models import Subscription
            subscription = Subscription.objects.create(profile=profile)
            
        subscription.plan_name = plan.name
        subscription.credits_available += plan.credits
        
        from django.utils import timezone
        import datetime
        now = timezone.now()
        
        if subscription.end_date and subscription.end_date > now:
            subscription.end_date = subscription.end_date + datetime.timedelta(days=plan.duration_days)
        else:
            subscription.end_date = now + datetime.timedelta(days=plan.duration_days)
            
        subscription.is_active = True
        subscription.save()
        
        from .models import Transaction
        Transaction.objects.create(
            profile=profile,
            plan_name=plan.name,
            transaction_type='subscription',
            amount=amount,
            status='completed',
            payment_method=payment_mode
        )
        
        from .serializers import SubscriptionSerializer
        return Response({
            'success': True,
            'message': 'Payment successful and subscription activated.',
            'data': SubscriptionSerializer(subscription).data
        })