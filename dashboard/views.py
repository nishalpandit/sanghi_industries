from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

superuser_required = user_passes_test(is_superuser, login_url='/admin-dashboard/login/')

import json
from datetime import datetime
from users.models import Transaction, Subscription, Profile
from django.db.models import Sum
from django.utils import timezone
import calendar
from django.utils.timezone import make_aware

def get_monthly_chart_data():
    labels = []
    new_users_data = []
    active_users_data = []
    revenue_data = []
    
    now = timezone.now()
    months_list = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        months_list.append((y, m))

    for y, m in months_list:
        month_name = calendar.month_abbr[m]
        labels.append(month_name)
        
        start_date = make_aware(datetime(y, m, 1))
        next_m = m + 1
        next_y = y
        if next_m > 12:
            next_m = 1
            next_y += 1
        end_date = make_aware(datetime(next_y, next_m, 1))
        
        new_users = Profile.objects.filter(created_at__gte=start_date, created_at__lt=end_date).count()
        new_users_data.append(new_users)
        
        active_users = Profile.objects.filter(created_at__lt=end_date).count()
        active_users_data.append(active_users)
        
        revenue_dict = Transaction.objects.filter(
            status='completed', 
            created_at__gte=start_date, 
            created_at__lt=end_date
        ).aggregate(total=Sum('amount'))
        revenue_data.append(float(revenue_dict['total'] or 0))

    return {
        'labels': labels,
        'new_users': new_users_data,
        'active_users': active_users_data,
        'revenue': revenue_data,
    }

@superuser_required
def dashboard(request):
    chart_data = get_monthly_chart_data()
    
    from users.models import Profile, Transaction, Subscription, GeneratedPoster
    from master.models import Template
    total_users = Profile.objects.count()
    
    total_revenue_dict = Transaction.objects.filter(status='completed').aggregate(total=Sum('amount'))
    total_revenue = total_revenue_dict['total'] or 0
    
    active_subscriptions = Subscription.objects.filter(is_active=True, end_date__gt=timezone.now()).count()
    total_posters = GeneratedPoster.objects.count()
    
    top_templates = Template.objects.filter(status='published').order_by('-usage_count')[:5]
    
    context = {
        'total_users': total_users,
        'chart_data_json': json.dumps(chart_data),
        'total_revenue': total_revenue,
        'total_posters': total_posters,
        'active_subscriptions': active_subscriptions,
        'top_templates': top_templates,
    }
    return render(request, 'dashboard/pages/dashboard.html', context)

def login(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None and user.is_superuser:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'dashboard/pages/login.html', {'error': 'Invalid credentials or not a superuser'})
    return render(request, 'dashboard/pages/login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('login')

@superuser_required
def users(request):
    from users.models import Profile
    from django.contrib.auth.models import User
    from master.models import BusinessCategory, BusinessType
    from django.contrib import messages

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        mobile_number = request.POST.get('mobile_number', '')
        date_of_birth = request.POST.get('date_of_birth', '') or None
        business_name = request.POST.get('business_name', '')
        business_category_id = request.POST.get('business_category', '')
        business_type_ids = request.POST.getlist('business_type')
        password = request.POST.get('password', '')
        subscription_plan_name = request.POST.get('subscription_plan', '')

        profile_id = request.POST.get('profile_id', '')

        # Basic validation
        if profile_id:
            # Update existing user
            profile = Profile.objects.filter(id=profile_id).first()
            if profile:
                user = profile.user
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                if password:  # Only update password if provided
                    user.set_password(password)
                user.save()

                profile.mobile_number = mobile_number
                profile.date_of_birth = date_of_birth
                profile.business_name = business_name
                
                business_category = None
                if business_category_id:
                    business_category = BusinessCategory.objects.filter(id=business_category_id).first()
                profile.business_category = business_category
                
                profile.save()
                
                if business_type_ids:
                    profile.business_types.set(business_type_ids)
                else:
                    profile.business_types.clear()
                
                if subscription_plan_name:
                    from users.models import Subscription, Transaction
                    from master.models import SubscriptionPlan
                    from django.utils import timezone
                    from datetime import timedelta
                    
                    subscription, _ = Subscription.objects.get_or_create(profile=profile)
                    
                    # Check if a transaction exists to handle previously broken subscriptions
                    has_transaction = Transaction.objects.filter(profile=profile, plan_name=subscription_plan_name, status='completed').exists()
                    
                    if subscription.plan_name != subscription_plan_name or (subscription_plan_name.lower() != 'free' and not has_transaction):
                        old_plan = subscription.plan_name
                        subscription.plan_name = subscription_plan_name
                        
                        plan = SubscriptionPlan.objects.filter(name=subscription_plan_name).first()
                        if plan:
                            subscription.credits_available = plan.credits
                            if plan.duration_days > 0:
                                subscription.end_date = timezone.now() + timedelta(days=plan.duration_days)
                            else:
                                subscription.end_date = None
                                
                            Transaction.objects.create(
                                profile=profile,
                                plan_name=plan.name,
                                transaction_type='upgrade' if old_plan and old_plan.lower() != 'free' else 'subscription',
                                amount=plan.price,
                                status='completed',
                                payment_method='admin_manual'
                            )
                        subscription.save()
                
                messages.success(request, 'User updated successfully!')
            else:
                messages.error(request, 'User not found.')
        elif mobile_number and not Profile.objects.filter(mobile_number=mobile_number).exists():
            # Create user
            username = mobile_number  # using mobile number as username
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            business_category = None
            if business_category_id:
                business_category = BusinessCategory.objects.filter(id=business_category_id).first()

            profile = Profile.objects.create(
                user=user,
                mobile_number=mobile_number,
                date_of_birth=date_of_birth,
                business_name=business_name,
                business_category=business_category,
            )
            
            if business_type_ids:
                profile.business_types.set(business_type_ids)
            
            if subscription_plan_name:
                from users.models import Subscription, Transaction
                from master.models import SubscriptionPlan
                from django.utils import timezone
                from datetime import timedelta
                
                subscription, _ = Subscription.objects.get_or_create(profile=profile)
                subscription.plan_name = subscription_plan_name
                
                plan = SubscriptionPlan.objects.filter(name=subscription_plan_name).first()
                if plan:
                    subscription.credits_available = plan.credits
                    if plan.duration_days > 0:
                        subscription.end_date = timezone.now() + timedelta(days=plan.duration_days)
                    else:
                        subscription.end_date = None
                        
                    Transaction.objects.create(
                        profile=profile,
                        plan_name=plan.name,
                        transaction_type='subscription',
                        amount=plan.price,
                        status='completed',
                        payment_method='admin_manual'
                    )
                subscription.save()
            
            messages.success(request, 'User created successfully!')
        else:
            messages.error(request, 'User with this mobile number already exists or invalid data.')
        
        return redirect('users')

    profiles_qs = Profile.objects.select_related('user', 'business_category').prefetch_related('business_types').all().order_by('-created_at')
    
    total_users = profiles_qs.count()
    # For now, let's assume all profiles are active
    active_users = total_users
    
    paginator = Paginator(profiles_qs, 20)
    page_number = request.GET.get('page', 1)
    profiles = paginator.get_page(page_number)
    
    categories = BusinessCategory.objects.filter(is_active=True)
    business_types = BusinessType.objects.filter(is_active=True)
    
    from master.models import SubscriptionPlan
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True)
    
    context = {
        'profiles': profiles,
        'page_obj': profiles,
        'total_users': total_users,
        'active_users': active_users,
        'categories': categories,
        'business_types': business_types,
        'subscription_plans': subscription_plans,
    }
    return render(request, 'dashboard/pages/users.html', context)


@superuser_required
def brand_kits(request):
    from users.models import Profile, BrandKit
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    profiles_qs = Profile.objects.filter(brand_kits__isnull=False).annotate(
        kit_count=Count('brand_kits')
    ).select_related('user').prefetch_related('brand_kits').distinct().order_by('-created_at')
    
    paginator = Paginator(profiles_qs, 20)
    page_number = request.GET.get('page', 1)
    profiles = paginator.get_page(page_number)
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    total_kits = BrandKit.objects.count()
    users_with_kits = Profile.objects.filter(brand_kits__isnull=False).distinct().count()
    kits_this_month = BrandKit.objects.filter(created_at__gte=thirty_days_ago).count()
    
    context = {
        'profiles': profiles,
        'page_obj': profiles,
        'total_kits': total_kits,
        'users_with_kits': users_with_kits,
        'kits_this_month': kits_this_month,
    }
    return render(request, 'dashboard/pages/brand_kits.html', context)

@superuser_required
def templates(request):
    from master.models import TemplateCategory, Template
    from django.db.models import Count
    from django.contrib import messages
    from django.shortcuts import redirect
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name')
            category_id = request.POST.get('category')
            description = request.POST.get('description', '')
            status = request.POST.get('status', 'published')
            file = request.FILES.get('file')
            
            category = None
            if category_id:
                category = TemplateCategory.objects.filter(id=category_id).first()
                
            if file and name:
                Template.objects.create(
                    name=name,
                    category=category,
                    description=description,
                    status=status,
                    file=file
                )
                messages.success(request, 'Template created successfully!')
            else:
                messages.error(request, 'Name and file are required to create a template.')
            return redirect('templates')
        
        elif action == 'toggle_active':
            category_id = request.POST.get('category_id')
            if category_id:
                cat = TemplateCategory.objects.filter(id=category_id).first()
                if cat:
                    cat.is_active = not cat.is_active
                    cat.save()
                    status_text = 'activated' if cat.is_active else 'deactivated'
                    messages.success(request, f'Category "{cat.name}" {status_text} successfully!')
            return redirect('templates')
    
    # parent_categories - show ALL (active + inactive), active first, then inactive last
    from django.db.models import Q
    from django.core.paginator import Paginator
    parent_categories_qs = list(TemplateCategory.objects.filter(parent_category__isnull=True).order_by('-is_active', '-created_at'))
    
    # Calculate subcategory count and template count for each parent (direct + subcategory templates)
    for cat in parent_categories_qs:
        sub_ids = list(TemplateCategory.objects.filter(parent_category=cat, is_active=True).values_list('id', flat=True))
        cat.subcategory_count = len(sub_ids)
        cat.template_count = Template.objects.filter(Q(category=cat) | Q(category_id__in=sub_ids)).count()
    
    # Pagination - 20 per page
    paginator = Paginator(parent_categories_qs, 20)
    page_number = request.GET.get('page', 1)
    parent_categories = paginator.get_page(page_number)
    
    # We need subcategories too to display inside the category details
    all_subcategories = TemplateCategory.objects.filter(parent_category__isnull=False, is_active=True).order_by('name')
    
    # categories is used for the form dropdown (should include all categories)
    categories = TemplateCategory.objects.filter(is_active=True).order_by('name')
    
    import json
    categories_json_data = {}
    for cat in parent_categories_qs:
        if not cat.is_active:
            continue
        subs = []
        for sub in all_subcategories:
            if sub.parent_category_id == cat.id:
                subs.append({
                    'id': sub.id,
                    'name': sub.name,
                    'image_url': sub.image.url if sub.image else ''
                })
        categories_json_data[cat.name] = {
            'id': cat.id,
            'name': cat.name,
            'image_url': cat.image.url if cat.image else '',
            'subcategories': subs
        }
    
    # Category stats
    total_categories = TemplateCategory.objects.filter(parent_category__isnull=True).count()
    active_categories = TemplateCategory.objects.filter(parent_category__isnull=True, is_active=True).count()
    inactive_categories = total_categories - active_categories
    
    templates_list = Template.objects.all()
    
    context = {
        'parent_categories': parent_categories,
        'categories': categories,
        'categories_json': json.dumps(categories_json_data),
        'templates': templates_list,
        'total_categories': total_categories,
        'active_categories': active_categories,
        'inactive_categories': inactive_categories,
    }
    return render(request, 'dashboard/pages/categories.html', context)


@superuser_required
def category_templates(request, category_id):
    from master.models import Template, TemplateCategory
    from django.contrib import messages
    from django.shortcuts import get_object_or_404
    
    category = get_object_or_404(TemplateCategory, id=category_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create' or action == 'edit':
            template_id = request.POST.get('template_id')
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            status = request.POST.get('status', 'published')
            file = request.FILES.get('file')
                
            if template_id:
                # Edit
                template = Template.objects.filter(id=template_id).first()
                if template:
                    template.name = name
                    template.category = category
                    template.description = description
                    template.status = status
                    if file:
                        template.file = file
                    template.save()
                    messages.success(request, 'Template updated successfully!')
            else:
                # Create
                if file and name:
                    Template.objects.create(
                        name=name,
                        category=category,
                        description=description,
                        status=status,
                        file=file
                    )
                    messages.success(request, 'Template created successfully!')
                else:
                    messages.error(request, 'Name and file are required to create a template.')
            return redirect('category_templates', category_id=category.id)
            
        elif action == 'delete':
            template_id = request.POST.get('template_id')
            Template.objects.filter(id=template_id).delete()
            messages.success(request, 'Template deleted successfully!')
            return redirect('category_templates', category_id=category.id)

    templates_qs = Template.objects.filter(category=category).order_by('-created_at')
    
    total_templates = templates_qs.count()
    published_templates = templates_qs.filter(status='published').count()
    draft_templates = templates_qs.filter(status='draft').count()
    total_usage = sum(t.usage_count for t in templates_qs)
    
    paginator = Paginator(templates_qs, 20)
    page_number = request.GET.get('page', 1)
    templates_list = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'templates': templates_list,
        'page_obj': templates_list,
        'total_templates': total_templates,
        'published_templates': published_templates,
        'draft_templates': draft_templates,
        'total_usage': total_usage,
    }
    return render(request, 'dashboard/pages/category_templates.html', context)

@superuser_required
def analytics(request):
    import json
    from datetime import datetime, timedelta
    from django.utils import timezone
    from django.db.models import Count, Avg
    from django.db.models.functions import TruncDay
    from dashboard.models import UserSession, AnalyticsEvent
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    seven_days_ago = now - timedelta(days=7)
    
    # Base QuerySets excluding admins
    base_sessions = UserSession.objects.filter(user__is_staff=False, user__is_superuser=False)
    base_events = AnalyticsEvent.objects.filter(user__is_staff=False, user__is_superuser=False)

    # DAU Chart (Last 30 Days)
    dau_qs = base_sessions.filter(start_time__gte=thirty_days_ago).annotate(day=TruncDay('start_time')).values('day').annotate(users=Count('user', distinct=True)).order_by('day')
    dau_map = {item['day'].strftime('%d %b'): item['users'] for item in dau_qs}
    
    dau_labels = [(now - timedelta(days=i)).strftime('%d %b') for i in range(29, -1, -1)]
    dau_data = [dau_map.get(label, 0) for label in dau_labels]
    
    daily_active_users = dau_data[-1] if dau_data else 0
    yesterday_dau = dau_data[-2] if len(dau_data) > 1 else 0
    dau_change = round(((daily_active_users - yesterday_dau) / yesterday_dau * 100), 1) if yesterday_dau else 0

    # MAU
    monthly_active_users = base_sessions.filter(start_time__gte=thirty_days_ago).aggregate(users=Count('user', distinct=True))['users'] or 0
    last_month_mau = base_sessions.filter(start_time__gte=sixty_days_ago, start_time__lt=thirty_days_ago).aggregate(users=Count('user', distinct=True))['users'] or 0
    monthly_active_users_change = round(((monthly_active_users - last_month_mau) / last_month_mau * 100), 1) if last_month_mau else 0

    # Session Duration
    avg_session_seconds = base_sessions.filter(start_time__gte=seven_days_ago).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
    avg_session_duration = f"{int(avg_session_seconds // 60)}m {int(avg_session_seconds % 60)}s"

    session_qs = base_sessions.filter(start_time__gte=seven_days_ago).annotate(day=TruncDay('start_time')).values('day').annotate(avg=Avg('duration_seconds')).order_by('day')
    session_map = {item['day'].strftime('%A')[:3]: item['avg'] for item in session_qs}
    
    session_labels = [(now - timedelta(days=i)).strftime('%A')[:3] for i in range(6, -1, -1)]
    session_data = [round(session_map.get(label, 0)/60.0, 1) for label in session_labels]

    # Poster Creation Stats (Last 7 Days)
    poster_created_qs = base_events.filter(timestamp__gte=seven_days_ago, event_type='template_edit').annotate(day=TruncDay('timestamp')).values('day').annotate(c=Count('id')).order_by('day')
    poster_export_qs = base_events.filter(timestamp__gte=seven_days_ago, event_type='poster_export').annotate(day=TruncDay('timestamp')).values('day').annotate(c=Count('id')).order_by('day')
    
    pc_map = {item['day'].strftime('%A')[:3]: item['c'] for item in poster_created_qs}
    pe_map = {item['day'].strftime('%A')[:3]: item['c'] for item in poster_export_qs}
    
    poster_labels = session_labels
    poster_created = [pc_map.get(l, 0) for l in poster_labels]
    poster_exported = [pe_map.get(l, 0) for l in poster_labels]

    # Feature Usage
    feature_labels = ['Templates', 'Text Edit', 'Image Upload', 'Export', 'Sharing']
    f_keys = ['feature_templates', 'feature_text_edit', 'feature_image_upload', 'feature_export', 'feature_sharing']
    
    feature_this_month = [base_events.filter(timestamp__gte=thirty_days_ago, event_type=k).count() for k in f_keys]
    feature_last_month = [base_events.filter(timestamp__lt=thirty_days_ago, timestamp__gte=sixty_days_ago, event_type=k).count() for k in f_keys]
        
    # Conversion Funnel
    funnel_labels = ['Site Visits', 'Sign Ups', 'Viewed Templates', 'Edited Templates', 'Exports']
    f_events = ['site_visit', 'signup', 'template_view', 'template_edit', 'poster_export']
    funnel_data = [base_events.filter(timestamp__gte=thirty_days_ago, event_type=e).count() for e in f_events]
    
    conversion_rate = round((funnel_data[-1] / funnel_data[0] * 100), 1) if funnel_data and funnel_data[0] > 0 else 0
    last_funnel_data = [base_events.filter(timestamp__lt=thirty_days_ago, timestamp__gte=sixty_days_ago, event_type=e).count() for e in f_events]
    last_conversion_rate = round((last_funnel_data[-1] / last_funnel_data[0] * 100), 1) if last_funnel_data and last_funnel_data[0] > 0 else 0
    conversion_rate_change = round(conversion_rate - last_conversion_rate, 1)

    context = {
        'daily_active_users': daily_active_users,
        'daily_active_users_change': dau_change,
        'monthly_active_users': monthly_active_users,
        'monthly_active_users_change': monthly_active_users_change,
        'avg_session_duration': avg_session_duration,
        'avg_session_duration_change': 0, # Could calculate this if needed
        'conversion_rate': conversion_rate,
        'conversion_rate_change': conversion_rate_change,
        
        'chart_dau_labels': json.dumps(dau_labels),
        'chart_dau_data': json.dumps(dau_data),
        
        'chart_poster_labels': json.dumps(poster_labels),
        'chart_poster_created': json.dumps(poster_created),
        'chart_poster_exported': json.dumps(poster_exported),
        
        'chart_session_data': json.dumps(session_data),
        
        'chart_feature_labels': json.dumps(feature_labels),
        'chart_feature_this': json.dumps(feature_this_month),
        'chart_feature_last': json.dumps(feature_last_month),
        
        'chart_funnel_labels': json.dumps(funnel_labels),
        'chart_funnel_data': json.dumps(funnel_data),
    }
    
    return render(request, 'dashboard/pages/analytics.html', context)

@superuser_required
def subscriptions(request):
    from master.models import SubscriptionPlan
    from django.contrib import messages
    
    if request.method == 'POST':
        plan_id = request.POST.get('id')
        name = request.POST.get('name')
        
        # Read features from text area and convert to a list
        features_text = request.POST.get('features', '')
        features = [f.strip() for f in features_text.split('\n') if f.strip()]
        
        try:
            price = max(float(request.POST.get('price', 0.00) or 0.00), 0.00)
        except ValueError:
            price = 0.00
            
        try:
            duration_days = max(int(request.POST.get('duration_days', 30) or 1), 1)
        except ValueError:
            duration_days = 30
            
        try:
            credits = max(int(request.POST.get('credits', 0) or 0), 0)
        except ValueError:
            credits = 0
            
        is_active = request.POST.get('is_active') == 'on'
        
        if plan_id:
            plan = SubscriptionPlan.objects.filter(id=plan_id).first()
            if plan:
                plan.name = name
                plan.features = features
                plan.price = price
                plan.duration_days = duration_days
                plan.credits = credits
                plan.is_active = is_active
                plan.save()
                messages.success(request, 'Subscription Plan updated successfully!')
        else:
            SubscriptionPlan.objects.create(
                name=name, 
                features=features, 
                price=price,
                duration_days=duration_days,
                credits=credits,
                is_active=is_active
            )
            messages.success(request, 'Subscription Plan added successfully!')
        return redirect('subscriptions')

    plans = SubscriptionPlan.objects.all()
    
    from users.models import Transaction, Subscription
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta
    
    total_revenue_dict = Transaction.objects.filter(status='completed').aggregate(total=Sum('amount'))
    total_revenue = total_revenue_dict['total'] or 0
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    mrr_dict = Transaction.objects.filter(status='completed', created_at__gte=thirty_days_ago).aggregate(total=Sum('amount'))
    mrr = mrr_dict['total'] or 0
    
    active_subscriptions = Subscription.objects.filter(is_active=True, end_date__gt=timezone.now()).count()
    
    recent_transactions = Transaction.objects.all().order_by('-created_at')[:10]
    
    import json
    from dashboard.views import get_monthly_chart_data
    from django.db.models import Count
    
    chart_data = get_monthly_chart_data()
    
    plan_dist = list(Subscription.objects.filter(is_active=True).values('plan_name').annotate(count=Count('id')).order_by('-count'))
    chart_data['plan_labels'] = [item['plan_name'] for item in plan_dist]
    chart_data['plan_counts'] = [item['count'] for item in plan_dist]

    context = {
        'plans': plans,
        'total_revenue': total_revenue,
        'mrr': mrr,
        'active_subscriptions': active_subscriptions,
        'recent_transactions': recent_transactions,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'dashboard/pages/subscriptions.html', context)

@superuser_required
def reports(request):
    return render(request, 'dashboard/pages/reports.html')

@superuser_required
def notifications(request):
    return render(request, 'dashboard/pages/notifications.html')

@superuser_required
def master_business(request):
    from master.models import BusinessType
    from django.contrib import messages
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        if item_id:
            item = BusinessType.objects.filter(id=item_id).first()
            if item:
                item.name = name
                item.description = description
                item.is_active = is_active
                item.save()
                messages.success(request, 'Business Type updated!')
        else:
            BusinessType.objects.create(name=name, description=description, is_active=is_active)
            messages.success(request, 'Business Type added!')
        return redirect('masterBusiness')
    items_qs = BusinessType.objects.all().order_by('-created_at')
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page', 1)
    items = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/masterBusiness.html', {'items': items, 'page_obj': items})

@superuser_required
def master_category(request):
    from master.models import BusinessCategory
    from django.contrib import messages
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        if item_id:
            item = BusinessCategory.objects.filter(id=item_id).first()
            if item:
                item.name = name
                item.description = description
                item.is_active = is_active
                item.save()
                messages.success(request, 'Business Category updated!')
        else:
            BusinessCategory.objects.create(name=name, description=description, is_active=is_active)
            messages.success(request, 'Business Category added!')
        return redirect('masterCategory')
    items_qs = BusinessCategory.objects.all().order_by('-created_at')
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page', 1)
    items = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/masterCategory.html', {'items': items, 'page_obj': items})

@superuser_required
def master_city(request):
    from master.models import City
    from django.contrib import messages
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        state = request.POST.get('state', '')
        is_active = request.POST.get('is_active') == 'on'
        if item_id:
            item = City.objects.filter(id=item_id).first()
            if item:
                item.name = name
                item.state = state
                item.is_active = is_active
                item.save()
                messages.success(request, 'City updated!')
        else:
            City.objects.create(name=name, state=state, is_active=is_active)
            messages.success(request, 'City added!')
        return redirect('masterCity')
    items_qs = City.objects.all().order_by('-created_at')
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page', 1)
    items = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/masterCity.html', {'items': items, 'page_obj': items})

@superuser_required
def master_template_category(request):
    from master.models import TemplateCategory
    from django.contrib import messages
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        parent_category_id = request.POST.get('parent_category', '')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')
        clear_image = request.POST.get('clear_image') == 'on'
        parent_category = None
        if parent_category_id:
            parent_category = TemplateCategory.objects.filter(id=parent_category_id).first()
        
        if item_id:
            item = TemplateCategory.objects.filter(id=item_id).first()
            if item:
                item.name = name
                item.parent_category = None
                item.is_active = is_active
                if clear_image and not image:
                    item.image.delete(save=False)
                    item.image = None
                if image:
                    if item.image:
                        item.image.delete(save=False)
                    item.image = image
                item.save()
                messages.success(request, 'Template Category updated!')
        else:
            new_item = TemplateCategory(name=name, parent_category=None, is_active=is_active)
            if image:
                new_item.image = image
            new_item.save()
            messages.success(request, 'Template Category added!')
        return redirect('masterTemplateCategory')
    items_qs = TemplateCategory.objects.filter(parent_category__isnull=True).order_by('-created_at')
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page', 1)
    items = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/masterTemplateCategory.html', {'items': items, 'page_obj': items})

@superuser_required
def master_template_category_detail(request, category_id):
    from master.models import TemplateCategory
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect
    
    category = get_object_or_404(TemplateCategory, id=category_id, parent_category__isnull=True)
    
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')
        clear_image = request.POST.get('clear_image') == 'on'
        
        if item_id:
            item = TemplateCategory.objects.filter(id=item_id, parent_category=category).first()
            if item:
                item.name = name
                item.is_active = is_active
                if clear_image and not image:
                    item.image.delete(save=False)
                    item.image = None
                if image:
                    if item.image:
                        item.image.delete(save=False)
                    item.image = image
                item.save()
                messages.success(request, 'Template Subcategory updated!')
        else:
            new_item = TemplateCategory(name=name, parent_category=category, is_active=is_active)
            if image:
                new_item.image = image
            new_item.save()
            messages.success(request, 'Template Subcategory added!')
        return redirect('masterTemplateCategoryDetail', category_id=category.id)
        
    subcategories_qs = TemplateCategory.objects.filter(parent_category=category).order_by('-created_at')
    paginator = Paginator(subcategories_qs, 20)
    page_number = request.GET.get('page', 1)
    subcategories = paginator.get_page(page_number)
    
    return render(request, 'dashboard/pages/masterTemplateCategoryDetail.html', {
        'category': category,
        'subcategories': subcategories,
        'page_obj': subcategories
    })

@superuser_required
def master_template_subcategory(request):
    from master.models import TemplateCategory
    from django.contrib import messages
    if request.method == 'POST':
        item_id = request.POST.get('id')
        name = request.POST.get('name')
        parent_category_id = request.POST.get('parent_category', '')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')
        clear_image = request.POST.get('clear_image') == 'on'
        
        parent_category = None
        if parent_category_id:
            parent_category = TemplateCategory.objects.filter(id=parent_category_id).first()
        
        if item_id:
            item = TemplateCategory.objects.filter(id=item_id).first()
            if item:
                item.name = name
                item.parent_category = parent_category
                item.is_active = is_active
                if clear_image and not image:
                    item.image.delete(save=False)
                    item.image = None
                if image:
                    if item.image:
                        item.image.delete(save=False)
                    item.image = image
                item.save()
                messages.success(request, 'Template Subcategory updated!')
        else:
            new_item = TemplateCategory(name=name, parent_category=parent_category, is_active=is_active)
            if image:
                new_item.image = image
            new_item.save()
            messages.success(request, 'Template Subcategory added!')
        return redirect('masterTemplateSubcategory')
    
    items_qs = TemplateCategory.objects.filter(parent_category__isnull=False).order_by('-created_at')
    paginator = Paginator(items_qs, 20)
    page_number = request.GET.get('page', 1)
    items = paginator.get_page(page_number)
    parent_categories = TemplateCategory.objects.filter(parent_category__isnull=True).order_by('name')
    return render(request, 'dashboard/pages/masterTemplateSubcategory.html', {
        'items': items,
        'page_obj': items,
        'parent_categories': parent_categories
    })


@superuser_required
def trending_templates(request):
    from master.models import TrendingTemplate
    from django.contrib import messages
    from django.shortcuts import redirect

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            image = request.FILES.get('image')
            if name and image:
                TrendingTemplate.objects.create(name=name, image=image)
                messages.success(request, 'Trending Template added successfully!')
            else:
                messages.error(request, 'Name and Image are required.')
        elif action == 'delete':
            item_id = request.POST.get('id')
            if item_id:
                try:
                    item = TrendingTemplate.objects.get(id=item_id)
                    item.delete()
                    messages.success(request, 'Trending Template deleted successfully!')
                except TrendingTemplate.DoesNotExist:
                    messages.error(request, 'Trending Template not found.')
        return redirect('trending_templates')

    templates_qs = TrendingTemplate.objects.all().order_by('-created_at')
    paginator = Paginator(templates_qs, 20)
    page_number = request.GET.get('page', 1)
    templates = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/trending_templates.html', {'templates': templates, 'page_obj': templates})

@superuser_required
def flex_designs(request):
    from master.models import FlexDesign
    from django.contrib import messages
    from django.shortcuts import redirect

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            image = request.FILES.get('image')
            if name and image:
                FlexDesign.objects.create(name=name, image=image)
                messages.success(request, 'Flex Design added successfully!')
            else:
                messages.error(request, 'Name and Image are required.')
        elif action == 'delete':
            item_id = request.POST.get('id')
            if item_id:
                try:
                    item = FlexDesign.objects.get(id=item_id)
                    item.delete()
                    messages.success(request, 'Flex Design deleted successfully!')
                except FlexDesign.DoesNotExist:
                    messages.error(request, 'Flex Design not found.')
        return redirect('flex_designs')

    designs_qs = FlexDesign.objects.all().order_by('-created_at')
    paginator = Paginator(designs_qs, 20)
    page_number = request.GET.get('page', 1)
    designs = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/flex_designs.html', {'designs': designs, 'page_obj': designs})

@superuser_required
def feedback_page(request):
    from master.models import Feedback
    from django.contrib import messages
    from django.shortcuts import redirect

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            item_id = request.POST.get('id')
            if item_id:
                try:
                    item = Feedback.objects.get(id=item_id)
                    item.delete()
                    messages.success(request, 'Feedback deleted successfully!')
                except Feedback.DoesNotExist:
                    messages.error(request, 'Feedback not found.')
        return redirect('feedback')

    feedbacks_qs = Feedback.objects.select_related('user').all().order_by('-created_at')
    paginator = Paginator(feedbacks_qs, 20)
    page_number = request.GET.get('page', 1)
    feedbacks = paginator.get_page(page_number)
    return render(request, 'dashboard/pages/feedback.html', {'feedbacks': feedbacks, 'page_obj': feedbacks})

@superuser_required
def ai_generated_users(request):
    from users.models import Profile, GeneratedPoster
    from django.db.models import Count
    
    # Get all users who have generated posters or just all users.
    # We will list users annotated with their generated poster count.
    profiles_qs = Profile.objects.annotate(poster_count=Count('generated_posters')).order_by('-created_at')
    
    paginator = Paginator(profiles_qs, 20)
    page_number = request.GET.get('page', 1)
    profiles = paginator.get_page(page_number)
    
    context = {
        'profiles': profiles,
        'page_obj': profiles,
    }
    return render(request, 'dashboard/pages/ai_generated_users.html', context)


@superuser_required
def ai_generated_user_posters(request, profile_id):
    from users.models import Profile, GeneratedPoster
    from django.shortcuts import get_object_or_404
    
    profile = get_object_or_404(Profile, id=profile_id)
    posters_qs = profile.generated_posters.all().order_by('-created_at')
    
    paginator = Paginator(posters_qs, 20)
    page_number = request.GET.get('page', 1)
    posters = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'posters': posters,
        'page_obj': posters,
    }
    return render(request, 'dashboard/pages/ai_generated_user_posters.html', context)


@superuser_required
def payments_list(request):
    from users.models import Transaction
    from django.core.paginator import Paginator
    
    # We get all transactions which act as payments
    payments_qs = Transaction.objects.select_related('profile__user').order_by('-created_at')
    
    paginator = Paginator(payments_qs, 20)
    page_number = request.GET.get('page', 1)
    payments = paginator.get_page(page_number)
    
    context = {
        'payments': payments,
        'page_obj': payments,
    }
    return render(request, 'dashboard/pages/payments.html', context)
