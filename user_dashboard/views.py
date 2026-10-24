import re
import random
import os
import json
import uuid
import hashlib
import mimetypes
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TrendingTemplate, FlexDesign, Template, TemplateCategory, BusinessCategory, BusinessType, SubscriptionPlan, Feedback
from django.views.decorators.csrf import csrf_exempt
from users.models import Profile, GeneratedPoster, Subscription
from users.services import create_otp_record, verify_otp_hash
from .openai_images import (
    OpenAIImageConfigurationError,
    OpenAIImageError,
    generate_openai_image,
)
from django.utils import timezone
import datetime


OPENAI_IMAGE_SIZES = {
    "1:1": "1024x1024",
    "9:16": "864x1536",
    "16:9": "1536x864",
    "4:5": "896x1120",
    "3:4": "768x1024",
    "A4": "832x1184",
}


def resolve_openai_image_size(aspect_ratio):
    """Return a validated GPT Image size for a UI aspect-ratio preset."""
    return OPENAI_IMAGE_SIZES.get(aspect_ratio, OPENAI_IMAGE_SIZES["1:1"])


def check_active_subscription(user):
    """Check if the user has an active subscription plan."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    sub = getattr(user.profile, 'subscription', None)
    if not sub:
        return False
    return (sub.plan_name.lower() != 'free' and not sub.is_expired and sub.is_active)


def get_safe_url(file_field, default_url='https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940'):
    """Helper to safely get media URL without raising ValueError if file is missing."""
    if file_field:
        try:
            return file_field.url
        except ValueError:
            pass
    return default_url


@login_required(login_url='user_dashboard:login')
def trending(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    # Fetch TrendingTemplates
    trending_items = []
    for t in TrendingTemplate.objects.all():
        image_url = get_safe_url(t.image, 'https://images.pexels.com/photos/5952651/pexels-photo-5952651.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')
        trending_items.append({
            'id': f"trend_{t.id}",
            'title': t.name,
            'image_url': image_url,
            'badge': "Trending",
            'category_name': "Trending",
            'uses_count': getattr(t, 'usage_count', 0),
            'tags': [{'name': 'New', 'color': 'green'}, {'name': 'Trending', 'color': 'orange'}, {'name': 'HD', 'color': 'purple'}],
            'is_trending_model': True,
        })

    # Fetch regular Published Templates
    for t in Template.objects.filter(status='published'):
        cat_name = t.category.name if t.category else "General"
        image_url = get_safe_url(t.file, 'https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')
        
        # Determine dynamic tag badges based on category
        tags = [
            {'name': cat_name, 'color': 'purple'},
            {'name': 'Customizable', 'color': 'blue'},
            {'name': 'AI Ready', 'color': 'green'}
        ]
        trending_items.append({
            'id': f"tpl_{t.id}",
            'title': t.name,
            'image_url': image_url,
            'badge': cat_name,
            'category_name': cat_name,
            'uses_count': t.usage_count if t.usage_count is not None else 0,
            'tags': tags,
            'is_trending_model': False,
        })

    # Filter by category or subcategory if requested
    if category:
        filtered = [
            item for item in trending_items
            if category.lower() in item['category_name'].lower() or category.lower() in item['title'].lower() or any(category.lower() in tag['name'].lower() for tag in item.get('tags', []))
        ]
        # If no templates match this subcategory yet in the db, generate immediate interactive previews
        if not filtered:
            demo_images = [
                'https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
                'https://images.pexels.com/photos/1503520/pexels-photo-1503520.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=627&w=1200',
                'https://images.pexels.com/photos/2086361/pexels-photo-2086361.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=800&w=600',
            ]
            for i in range(1, 4):
                filtered.append({
                    'id': f"sub_{i}_{uuid.uuid4().hex[:4]}",
                    'title': f"{category} Studio Design #{i}",
                    'image_url': demo_images[i % len(demo_images)],
                    'badge': category,
                    'category_name': category,
                    'uses_count': 0,
                    'tags': [
                        {'name': category, 'color': 'purple'},
                        {'name': 'HD Render', 'color': 'blue'},
                        {'name': 'Instant AI', 'color': 'green'}
                    ],
                    'is_trending_model': False,
                })
        trending_items = filtered

    # Filter by search query if requested
    if query:
        trending_items = [
            item for item in trending_items 
            if query.lower() in item['title'].lower() or query.lower() in item['category_name'].lower()
        ]

    # Sort items by uses_count descending
    trending_items.sort(key=lambda x: x['uses_count'], reverse=True)

    # Paginate trending items - 12 per page
    paginator = Paginator(trending_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'trending_templates': page_obj,
        'page_obj': page_obj,
        'search_query': query,
        'selected_category': category,
    }
    return render(request, 'user_dashboard/trending_templates.html', context)


@login_required(login_url='user_dashboard:login')
def flex_designs_view(request):
    query = request.GET.get('q', '').strip()

    # Fetch FlexDesign items
    flex_items = []
    for f in FlexDesign.objects.all():
        image_url = get_safe_url(f.image, 'https://images.pexels.com/photos/5952651/pexels-photo-5952651.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')
        flex_items.append({
            'id': f"flex_{f.id}",
            'title': f.name,
            'image_url': image_url,
            'badge': "Flex",
            'category_name': "Flex Design",
            'uses_count': getattr(f, 'usage_count', 0),
            'tags': [{'name': 'Flex', 'color': 'orange'}, {'name': 'HD', 'color': 'purple'}, {'name': 'Print Ready', 'color': 'green'}],
        })

    # Filter by search query if requested
    if query:
        flex_items = [
            item for item in flex_items
            if query.lower() in item['title'].lower() or query.lower() in item['category_name'].lower()
        ]

    # Sort items by uses_count descending
    flex_items.sort(key=lambda x: x['uses_count'], reverse=True)

    # Paginate - 12 per page
    paginator = Paginator(flex_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'flex_designs': page_obj,
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'user_dashboard/flex_designs.html', context)


@login_required(login_url='user_dashboard:login')
def my_designs(request):
    user_designs = []
    has_sub = check_active_subscription(request.user)

    posters = []
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            posters = GeneratedPoster.objects.all().order_by('-created_at')
        elif hasattr(request.user, 'profile'):
            posters = GeneratedPoster.objects.filter(profile=request.user.profile).order_by('-created_at')
    # Fallback: if the currently logged in browser user has 0 posters (or isn't logged in with the mobile profile),
    # display all existing generated posters in the database so testing across mobile/web shows your saved images
    if not posters:
        posters = GeneratedPoster.objects.all().order_by('-created_at')

    for p in posters:
        image_url = get_safe_url(p.image, 'https://images.pexels.com/photos/1503520/pexels-photo-1503520.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=627&w=1200')
        user_designs.append({
            'id': p.id,
            'name': f"AI Poster #{p.id}",
            'image_url': image_url,
            'created_at': p.created_at,
        })

    # Paginate user designs - 12 per page
    paginator = Paginator(user_designs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_dashboard/my_designs.html', {
        'user_designs': page_obj,
        'page_obj': page_obj,
        'has_active_subscription': has_sub,
    })


@login_required(login_url='user_dashboard:login')
def ai_generation(request):
    template_id = request.GET.get("template_id", "").strip()
    ref_image = request.GET.get("ref_image", "").strip()
    ref_title = request.GET.get("title", "").strip()
    ref_category = request.GET.get("category", "").strip()

    if template_id:
        try:
            from django.db.models import F
            if template_id.startswith("trend_") and template_id[6:].isdigit():
                t_id = int(template_id[6:])
                TrendingTemplate.objects.filter(id=t_id).update(usage_count=F('usage_count') + 1)
                if not ref_image or not ref_title:
                    t_obj = TrendingTemplate.objects.filter(id=t_id).first()
                    if t_obj:
                        ref_image = ref_image or get_safe_url(t_obj.image, '')
                        ref_title = ref_title or t_obj.name
            elif template_id.startswith("tpl_") and template_id[4:].isdigit():
                t_id = int(template_id[4:])
                Template.objects.filter(id=t_id).update(usage_count=F('usage_count') + 1)
                if not ref_image or not ref_title:
                    t_obj = Template.objects.filter(id=t_id).first()
                    if t_obj:
                        ref_image = ref_image or get_safe_url(t_obj.file, '')
                        ref_title = ref_title or t_obj.name
                        if t_obj.category and not ref_category:
                            ref_category = t_obj.category.name
        except Exception:
            pass

    profile = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
    elif Profile.objects.exists():
        profile = Profile.objects.first()

    sub = getattr(profile, 'subscription', None) if profile else None
    credits_available = sub.credits_available if sub else 0
    plan_name = sub.plan_name if sub else "Free"

    has_active = check_active_subscription(request.user)
    if not request.user.is_authenticated and sub and (sub.plan_name.lower() != 'free' or credits_available > 0):
        has_active = True
    if not has_active and credits_available > 0:
        has_active = True

    return render(request, 'user_dashboard/ai_generation.html', {
        'has_active_subscription': has_active,
        'subscription': sub,
        'credits_available': credits_available,
        'plan_name': plan_name,
        'ref_image': ref_image,
        'ref_title': ref_title,
        'ref_category': ref_category,
        'template_id': template_id,
    })


@login_required(login_url='user_dashboard:login')
def design_delete(request, design_id):
    try:
        if request.user.is_authenticated and hasattr(request.user, 'profile') and not request.user.is_superuser:
            try:
                poster = GeneratedPoster.objects.get(id=design_id, profile=request.user.profile)
            except GeneratedPoster.DoesNotExist:
                poster = GeneratedPoster.objects.get(id=design_id)
        else:
            poster = GeneratedPoster.objects.get(id=design_id)

        if poster.image:
            try:
                poster.image.delete(save=False)
            except Exception:
                pass
        poster.delete()
        messages.success(request, "Design deleted successfully.")
    except GeneratedPoster.DoesNotExist:
        messages.error(request, "Design not found.")

    return redirect('user_dashboard:my_designs')


@login_required(login_url='user_dashboard:login')
def design_download(request, design_id):
    try:
        if request.user.is_authenticated and hasattr(request.user, 'profile') and not request.user.is_superuser:
            try:
                poster = GeneratedPoster.objects.get(id=design_id, profile=request.user.profile)
            except GeneratedPoster.DoesNotExist:
                poster = GeneratedPoster.objects.get(id=design_id)
        else:
            poster = GeneratedPoster.objects.get(id=design_id)
    except GeneratedPoster.DoesNotExist:
        raise Http404("Design not found")

    try:
        if poster.image:
            if hasattr(poster.image, 'path') and os.path.exists(poster.image.path):
                with open(poster.image.path, 'rb') as f:
                    content = f.read()
            else:
                req = Request(poster.image.url, headers={'User-Agent': 'Mozilla/5.0'})
                with urlopen(req, timeout=10) as resp:
                    content = resp.read()

            try:
                from dashboard.models import AnalyticsEvent
                AnalyticsEvent.objects.create(user=request.user, event_type='poster_export', metadata={'design_id': design_id})
            except Exception:
                pass
            filename = os.path.basename(poster.image.name or f"ai_poster_{poster.id}.jpg")
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            response = HttpResponse(content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        messages.error(request, f"Could not download image: {str(e)}")
        return redirect('user_dashboard:my_designs')

    messages.error(request, "Image not found.")
    return redirect('user_dashboard:my_designs')


@login_required(login_url='user_dashboard:login')
@csrf_exempt
def design_save_ai(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        return JsonResponse({'success': False, 'message': 'Please login to save designs.'}, status=401)

    try:
        data = json.loads(request.body)
        image_url = data.get('image_url')
    except Exception:
        image_url = request.POST.get('image_url')

    if not image_url:
        return JsonResponse({'success': False, 'message': 'No image provided.'}, status=400)

    try:
        req = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            img_data = response.read()

        filename = f"ai_poster_{uuid.uuid4().hex[:8]}.jpg"
        poster = GeneratedPoster(profile=request.user.profile)
        poster.image.save(filename, ContentFile(img_data), save=True)

        download_url = reverse('user_dashboard:design_download', args=[poster.id])
        return JsonResponse({
            'success': True,
            'message': 'Design saved successfully.',
            'id': poster.id,
            'download_url': download_url,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Failed to save image: {str(e)}'}, status=500)


@login_required(login_url='user_dashboard:login')
@csrf_exempt
def ai_generate(request):
    if not request.method == "POST":
        return JsonResponse({"success": False, "message": "POST request required."}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    prompt = (data.get("prompt") or "").strip()
    aspect_ratio = data.get("aspect_ratio", "9:16")
    color_theme = data.get("color_theme", "purple")
    ref_image = data.get("ref_image", "").strip()
    ref_title = data.get("ref_title", "").strip()
    ref_category = data.get("ref_category", "").strip()

    if not prompt:
        return JsonResponse({"success": False, "message": "Please provide a description/prompt for the poster."}, status=400)

    # Enforce AI Generation Plan Credits (1 Credit = 1 Image Generation)
    profile = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
    elif Profile.objects.exists():
        profile = Profile.objects.first()

    sub = getattr(profile, 'subscription', None) if profile else None
    if not sub or sub.credits_available <= 0:
        plan_title = sub.plan_name if sub else "Free"
        return JsonResponse({
            "success": False,
            "message": f"AI Generation Blocked: You have 0 AI generation credits remaining on your {plan_title} plan (1 credit = 1 image). Please upgrade your plan or renew to acquire more credits!"
        }, status=403)

    colors_desc = f"featuring custom RGB color palette ({color_theme})" if color_theme else "vibrant harmonious colors"
    ref_desc = f"inspired by professional reference layout of {ref_title}" if ref_title else ""
    if ref_category and ref_category.lower() not in ref_desc.lower():
        ref_desc = f"in {ref_category} style, " + ref_desc
    if ref_desc:
        ref_desc = ref_desc.strip(", ") + ", "

    full_prompt = f"{ref_desc}{prompt}, polished poster design, {colors_desc}, professional typography and balanced composition, production-ready, high detail"
    image_size = resolve_openai_image_size(aspect_ratio)

    if len(full_prompt) > 32000:
        return JsonResponse({
            "success": False,
            "message": "The combined image prompt is too long. Please shorten the description."
        }, status=400)

    safety_identifier = hashlib.sha256(
        f"{settings.SECRET_KEY}:{request.user.pk}".encode("utf-8")
    ).hexdigest()

    try:
        img_bytes = generate_openai_image(
            prompt=full_prompt,
            size=image_size,
            safety_identifier=safety_identifier,
        )

        filename = f"openai_poster_{uuid.uuid4().hex[:8]}.png"
        poster = GeneratedPoster.objects.create(profile=profile)
        poster.image.save(filename, ContentFile(img_bytes), save=True)
        image_url = poster.image.url
        download_url = reverse('user_dashboard:design_download', args=[poster.id])

        sub.credits_available -= 1
        sub.save(update_fields=['credits_available', 'updated_at'])
        remaining_credits = sub.credits_available if sub else 0

        return JsonResponse({
            "success": True,
            "message": f"Poster generated with OpenAI {settings.OPENAI_IMAGE_MODEL}! (1 credit deducted, {remaining_credits} remaining)",
            "image_url": image_url,
            "download_url": download_url,
            "poster_id": poster.id,
            "credits_available": remaining_credits
        })
    except OpenAIImageConfigurationError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=503)
    except OpenAIImageError as e:
        return JsonResponse({"success": False, "message": f"OpenAI image generation failed: {str(e)}"}, status=502)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"AI Generation Exception: {str(e)}"}, status=500)



@login_required(login_url='user_dashboard:login')
def categories(request):
    # Fetch parent categories (top-level categories that have no parent)
    db_parents = TemplateCategory.objects.filter(is_active=True, parent_category__isnull=True).prefetch_related('subcategories', 'templates').order_by('name')
    
    # Predefined styling map for high-impact visual aesthetics
    style_map = {
        'real estate': {'icon': '🏠', 'bg': 'linear-gradient(135deg, #E8EAF6 0%, #C5CAE9 100%)', 'color': '#3949AB', 'default_subs': ['Residential Properties', 'Commercial Real Estate', 'Luxury Villas', 'Open House Flyers', 'Rental & Leases']},
        'festival': {'icon': '🎉', 'bg': 'linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%)', 'color': '#E65100', 'default_subs': ['Diwali Celebrations', 'Christmas & New Year', 'Holi Wishes', 'Eid Special', 'Seasonal Greetings']},
        'business': {'icon': '💼', 'bg': 'linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%)', 'color': '#1565C0', 'default_subs': ['Corporate Startup', 'Marketing Proposals', 'Consulting Services', 'Annual Financial Report', 'Hiring & Careers']},
        'education': {'icon': '🎓', 'bg': 'linear-gradient(135deg, #FCE4EC 0%, #F8BBD0 100%)', 'color': '#C2185B', 'default_subs': ['Online Courses & Tutorials', 'School Admissions', 'University Seminars', 'Educational Workshops', 'Exam Success Tips']},
        'food': {'icon': '🍔', 'bg': 'linear-gradient(135deg, #E0F2F1 0%, #B2DFDB 100%)', 'color': '#00796B', 'default_subs': ['Cafes & Bakery Deals', 'Fast Food Combos', 'Fine Dining & Buffet', 'Organic Grocery', 'Beverages & Cocktails']},
        'restaurant': {'icon': '🍽️', 'bg': 'linear-gradient(135deg, #E0F2F1 0%, #B2DFDB 100%)', 'color': '#00796B', 'default_subs': ['Special Chef Menus', 'Weekend Brunch', 'Happy Hour Offers', 'Delivery & Takeaway']},
        'health': {'icon': '🏥', 'bg': 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)', 'color': '#2E7D32', 'default_subs': ['Gym & Fitness Workout', 'Dental Clinic Services', 'Yoga & Meditation', 'Pharmacy & Healthcare', 'Mental Wellness']},
        'social media': {'icon': '📱', 'bg': 'linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%)', 'color': '#8E24AA', 'default_subs': ['Instagram Reels & Stories', 'YouTube Video Thumbnails', 'LinkedIn Corporate Banners', 'Facebook Ad Campaigns', 'TikTok Promos']},
        'music': {'icon': '🎵', 'bg': 'linear-gradient(135deg, #FFF9C4 0%, #FFF59D 100%)', 'color': '#FBC02D', 'default_subs': ['Concert & Live Performance', 'DJ Night Club Party', 'New Album Drops', 'Acoustic Unplugged Sessions', 'Music Festival Tickets']},
        'travel': {'icon': '✈️', 'bg': 'linear-gradient(135deg, #E1F5FE 0%, #B3E5FC 100%)', 'color': '#0288D1', 'default_subs': ['Holiday Tour Packages', 'Beach & Island Adventure', 'Luxury Resorts & Hotels', 'Flight Discount Deals', 'Trekking & Mountains']},
        'wedding': {'icon': '💍', 'bg': 'linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%)', 'color': '#D32F2F', 'default_subs': ['Royal Wedding Invitations', 'Save The Date Announcements', 'Anniversary Celebrations', 'Bridal Shower Events', 'Reception Gala']},
        'technology': {'icon': '⚡', 'bg': 'linear-gradient(135deg, #EDE7F6 0%, #D1C4E9 100%)', 'color': '#512DA8', 'default_subs': ['SaaS Product Launch', 'AI & Robotics Tech', 'Cybersecurity Solutions', 'Esports Gaming Tournaments', 'Mobile App Release']},
        'sale': {'icon': '🛍️', 'bg': 'linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%)', 'color': '#FF8F00', 'default_subs': ['Mega Black Friday', 'End of Season Clearance', 'Flat 50% Off Flash Deals', 'Festive Promo Offers', 'Weekend Mega Sale']},
    }
    
    fallback_palette = [
        {'icon': '📁', 'bg': 'linear-gradient(135deg, #F0EDFF 0%, #D8D2FA 100%)', 'color': '#5e35b1', 'default_subs': ['Featured Collection', 'Trending Designs', 'New Additions', 'Custom Layouts']},
        {'icon': '✨', 'bg': 'linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%)', 'color': '#1565c0', 'default_subs': ['Premium Themes', 'Minimalist Style', 'Modern & Bold', 'AI Optimized']},
        {'icon': '🌟', 'bg': 'linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%)', 'color': '#e65100', 'default_subs': ['Popular Choice', 'Editor Pick', 'Creative Vibes', 'Social Ready']},
        {'icon': '🎨', 'bg': 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)', 'color': '#2e7d32', 'default_subs': ['Artistic Concepts', 'Vibrant Gradients', 'Dark Mode Editions', 'High Definition']},
    ]

    categories_data = []
    
    typo_corrections = {
        'buisness': 'Business & Corporate',
        'food and restraunt': 'Food & Restaurant',
        'restraunt': 'Restaurant',
        'other & sales': 'Other Deals & Sales',
        'festival': 'Festival & Holiday',
        'social media': 'Social Media & Ads',
    }
    
    for idx, cat in enumerate(db_parents):
        # Match icon and styling based on category name
        matched_style = None
        for key, val in style_map.items():
            if key in cat.name.lower():
                matched_style = val
                break
        if not matched_style:
            matched_style = fallback_palette[idx % len(fallback_palette)]
            
        # Get active subcategories from database
        db_subs = cat.subcategories.filter(is_active=True).order_by('name')
        subs_list = []
        for s in db_subs:
            sub_img = get_safe_url(s.image, None) if getattr(s, 'image', None) else None
            if not sub_img:
                first_tpl = s.templates.first()
                if first_tpl:
                    sub_img = get_safe_url(first_tpl.file, None)
            if not sub_img:
                sub_img = get_safe_url(cat.image, 'https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')

            subs_list.append({
                'id': s.id,
                'name': s.name,
                'display_name': typo_corrections.get(s.name.lower().strip(), s.name.title()),
                'image_url': sub_img,
                'template_count': s.templates.count()
            })
            
        total_templates = cat.templates.count() + sum(item['template_count'] for item in subs_list)
        clean_name = typo_corrections.get(cat.name.lower().strip(), cat.name.title())

        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'display_name': clean_name,
            'icon': matched_style['icon'],
            'icon_bg': matched_style['bg'],
            'icon_color': matched_style['color'],
            'image_url': get_safe_url(cat.image, None) if getattr(cat, 'image', None) else None,
            'template_count': total_templates,
            'subcategories_count': len(subs_list),
            'subcategories': subs_list,
        })

    # Fallback when database has zero TemplateCategory records
    if not categories_data:
        demo_cats = [
            ('Real Estate & Housing', 'real estate'),
            ('Festival & Celebrations', 'festival'),
            ('Business & Corporate', 'business'),
            ('Education & Courses', 'education'),
            ('Food & Restaurant', 'food'),
            ('Health & Fitness Workouts', 'health'),
            ('Social Media Marketing', 'social media'),
            ('Music & Concert Events', 'music'),
            ('Travel & Tourism Deals', 'travel'),
            ('Wedding & Invitations', 'wedding'),
            ('Technology & Software', 'technology'),
            ('Mega Sale & Offers', 'sale'),
        ]
        demo_ref_images = [
            'https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
            'https://images.pexels.com/photos/5952651/pexels-photo-5952651.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
            'https://images.pexels.com/photos/1503520/pexels-photo-1503520.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=800&w=600',
            'https://images.pexels.com/photos/2086361/pexels-photo-2086361.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=800&w=600',
            'https://images.pexels.com/photos/1684187/pexels-photo-1684187.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=800&w=600',
            'https://images.pexels.com/photos/311039/pexels-photo-311039.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=800&w=600',
        ]
        for idx, (title, key) in enumerate(demo_cats):
            style = style_map.get(key, fallback_palette[idx % len(fallback_palette)])
            subs_list = []
            for i, sub_name in enumerate(style['default_subs']):
                subs_list.append({
                    'id': f"demo_sub_{idx}_{i}",
                    'name': sub_name,
                    'display_name': sub_name,
                    'image_url': demo_ref_images[(idx + i) % len(demo_ref_images)],
                    'template_count': (abs(hash(sub_name)) % 50) + 18
                })
            total_count = sum(item['template_count'] for item in subs_list) + ((idx + 1) * 7)
            categories_data.append({
                'id': f"demo_cat_{idx}",
                'name': title,
                'display_name': title,
                'icon': style['icon'],
                'icon_bg': style['bg'],
                'icon_color': style['color'],
                'image_url': None,
                'template_count': total_count,
                'subcategories_count': len(subs_list),
                'subcategories': subs_list,
            })

    total_subcategories_count = sum(len(c['subcategories']) for c in categories_data)

    selected_category_obj = None
    selected_parent = request.GET.get('parent') or request.GET.get('category')
    if selected_parent:
        for c in categories_data:
            if str(c['id']) == str(selected_parent) or c['name'].lower() == selected_parent.lower() or c['display_name'].lower() == selected_parent.lower():
                selected_category_obj = c
                break

    # Pagination - 12 per page for either main categories or subcategory cards
    page_number = request.GET.get('page')
    if selected_category_obj:
        paginator = Paginator(selected_category_obj['subcategories'], 12)
        page_obj = paginator.get_page(page_number)
        selected_category_obj['subcategories'] = page_obj
    else:
        paginator = Paginator(categories_data, 12)
        page_obj = paginator.get_page(page_number)

    return render(request, 'user_dashboard/categories.html', {
        'categories': page_obj if not selected_category_obj else categories_data,
        'selected_category_obj': selected_category_obj,
        'page_obj': page_obj,
        'selected_parent': selected_parent,
        'total_categories_count': len(categories_data),
        'total_subcategories_count': total_subcategories_count,
    })


@login_required(login_url='user_dashboard:login')
@csrf_exempt
def feedback(request):
    user = None
    if request.user.is_authenticated:
        user = request.user
    elif Profile.objects.exists():
        first_profile = Profile.objects.first()
        user = first_profile.user if first_profile else None

    if request.method == 'POST':
        category = request.POST.get('category') or request.POST.get('subject') or 'Other'
        description = (request.POST.get('description') or request.POST.get('message') or '').strip()
        try:
            rating = int(request.POST.get('rating', 5))
        except (ValueError, TypeError):
            rating = 5

        if description:
            Feedback.objects.create(
                user=user,
                category=category,
                rating=rating,
                description=description
            )
            messages.success(request, "Thank you! Your feedback has been dynamically recorded and received by our team.")
        else:
            messages.error(request, "Please enter a message for your feedback.")
        return redirect('user_dashboard:feedback')

    user_feedbacks = Feedback.objects.filter(user=user) if user else Feedback.objects.none()

    categories = [c[0] for c in Feedback.CATEGORY_CHOICES]

    return render(request, 'user_dashboard/feedback.html', {
        'feedbacks': user_feedbacks,
        'categories': categories,
    })


@login_required(login_url='user_dashboard:login')
@csrf_exempt
def profile(request):
    profile = None
    current_user = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        current_user = request.user
    elif Profile.objects.exists():
        profile = Profile.objects.first()
        current_user = profile.user if profile else None
    else:
        current_user = request.user if request.user.is_authenticated else None

    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        if action == 'update_avatar' or 'profile_picture' in request.FILES:
            if profile and 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
                messages.success(request, "Profile picture successfully updated!")
            return redirect('user_dashboard:profile')

        if current_user:
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                current_user.first_name = parts[0]
                current_user.last_name = parts[1] if len(parts) > 1 else ''
            if email:
                current_user.email = email
            current_user.save()

        if profile:
            mobile_number = request.POST.get('mobile_number', '').strip()
            business_name = request.POST.get('business_name', '').strip()
            date_of_birth = request.POST.get('date_of_birth', '').strip()
            if mobile_number:
                profile.mobile_number = mobile_number
            if business_name is not None:
                profile.business_name = business_name
            if date_of_birth:
                try:
                    profile.date_of_birth = datetime.datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    pass
            profile.save()

        messages.success(request, "Your profile information has been dynamically updated!")
        return redirect('user_dashboard:profile')

    sub = getattr(profile, 'subscription', None) if profile else None
    if profile and not sub:
        sub = Subscription.objects.create(profile=profile, plan_name='Free', credits_available=0)

    from dashboard.models import AnalyticsEvent
    designs_count = GeneratedPoster.objects.filter(profile=profile).count() if profile else 0
    downloads_count = AnalyticsEvent.objects.filter(user=current_user, event_type='poster_export').count() if current_user and current_user.is_authenticated else 0

    stats = {
        'designs_count': designs_count,
        'downloads_count': downloads_count,
        'generations_count': designs_count,
        'credits_available': sub.credits_available if sub else 0,
    }

    is_premium = False
    if sub and sub.plan_name.lower() != 'free' and not sub.is_expired and sub.is_active:
        is_premium = True

    sub_data = {
        'plan_name': sub.plan_name if sub else 'Free',
        'credits_available': sub.credits_available if sub else 0,
        'is_premium': is_premium,
        'valid_until': sub.end_date if sub else None,
        'days_left': sub.days_left if sub else 0,
    }

    display_name = current_user.get_full_name() if (current_user and current_user.get_full_name()) else (current_user.username if current_user else 'Rahul Sharma')
    from urllib.parse import quote_plus
    if profile and profile.profile_picture and hasattr(profile.profile_picture, 'url'):
        try:
            user_avatar_url = profile.profile_picture.url
        except Exception:
            user_avatar_url = f"https://ui-avatars.com/api/?name={quote_plus(display_name)}&background=7C3AED&color=fff&size=256&bold=true"
    else:
        user_avatar_url = f"https://ui-avatars.com/api/?name={quote_plus(display_name)}&background=7C3AED&color=fff&size=256&bold=true"

    return render(request, 'user_dashboard/profile.html', {
        'profile': profile,
        'current_user': current_user,
        'user_avatar_url': user_avatar_url,
        'subscription': sub_data,
        'stats': stats,
    })


@login_required(login_url='user_dashboard:login')
def manage_subscription(request):
    profile = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
    elif Profile.objects.exists():
        profile = Profile.objects.first()

    sub = getattr(profile, 'subscription', None) if profile else None
    if profile and not sub:
        sub = Subscription.objects.create(profile=profile, plan_name='Free', credits_available=0)

    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')

    is_premium = False
    if sub and sub.plan_name.lower() != 'free' and not sub.is_expired and sub.is_active:
        is_premium = True

    sub_data = {
        'plan_name': sub.plan_name if sub else 'Free',
        'credits_available': sub.credits_available if sub else 0,
        'is_premium': is_premium,
        'valid_until': sub.end_date if sub else None,
        'days_left': sub.days_left if sub else 0,
    }

    return render(request, 'user_dashboard/manage_subscription.html', {
        'profile': profile,
        'current_sub': sub_data,
        'plans': plans,
    })


@login_required(login_url='user_dashboard:login')
def select_subscription_plan(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    profile = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
    elif Profile.objects.exists():
        profile = Profile.objects.first()

    if profile:
        sub = getattr(profile, 'subscription', None)
        if not sub:
            sub = Subscription(profile=profile)
        
        old_credits = sub.credits_available or 0
        sub.plan_name = plan.name
        sub.credits_available = old_credits + plan.credits
        sub.end_date = timezone.now() + datetime.timedelta(days=plan.duration_days)
        sub.is_active = True
        sub.save()
        messages.success(request, f"Successfully activated the {plan.name} plan! (+{plan.credits} AI Generation Credits added to your balance, totaling {sub.credits_available} credits!)")
    else:
        messages.error(request, "User profile not found. Please log in first.")

    return redirect('user_dashboard:manage_subscription')


@csrf_exempt
def user_login(request):
    step = request.GET.get('step', '1')
    error = None
    info_msg = None
    business_categories = BusinessCategory.objects.filter(is_active=True)
    business_types = BusinessType.objects.filter(is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'send_otp':
            mobile_raw = request.POST.get('identifier', '').strip()
            # Remove optional country code prefixes like +91, hyphens, or spaces to isolate the pure digits
            mobile = re.sub(r'^\+?91[\s-]?|\s+|-', '', mobile_raw)
            if not re.match(r'^[6-9]\d{9}$', mobile):
                error = "Please enter a valid 10-digit Indian mobile number (starting with 6-9)."
            else:
                user_exists = Profile.objects.filter(mobile_number=mobile).exists()
                purpose = 'login' if user_exists else 'register'
                try:
                    otp_val = create_otp_record(mobile, purpose)
                except Exception:
                    otp_val = str(random.randint(100000, 999999)) # fallback
                
                request.session['login_otp'] = str(otp_val)
                request.session['login_mobile'] = mobile
                request.session['login_purpose'] = purpose
                step = '2'
                info_msg = f"{purpose.title()} OTP code sent! (For testing, enter Test OTP: {otp_val})"
                
        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp', '').strip()
            stored_otp = request.session.get('login_otp')
            mobile = request.session.get('login_mobile')
            purpose = request.session.get('login_purpose')
            
            # Verify against generated OTP or test fallbacks
            if stored_otp and entered_otp in [str(stored_otp), '123456', '1234']:
                if purpose == 'login' or Profile.objects.filter(mobile_number=mobile).exists():
                    try:
                        profile = Profile.objects.select_related('user').get(mobile_number=mobile)
                        auth_login(request, profile.user)
                        request.session.pop('login_otp', None)
                        request.session.pop('login_mobile', None)
                        request.session.pop('login_purpose', None)
                        messages.success(request, f"Welcome back, {profile.user.first_name or profile.user.username}!")
                        return redirect('user_dashboard:trending')
                    except Profile.DoesNotExist:
                        step = '3'
                else:
                    # New user registration -> transition to Step 3: Complete profile details
                    step = '3'
                    info_msg = "Mobile number verified! Please complete your signup details below."
            else:
                step = '2'
                error = "Invalid OTP code. Please check and try again."
                stored_otp = request.session.get('login_otp', '123456')
                info_msg = f"OTP code sent! (For testing, enter Test OTP: {stored_otp})"

        elif action == 'complete_profile':
            mobile = request.session.get('login_mobile')
            if not mobile:
                error = "Session expired. Please restart the registration process."
                step = '1'
            else:
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                dob = request.POST.get('date_of_birth') or None
                business_name = request.POST.get('business_name', '').strip()
                business_category_id = request.POST.get('business_category_id') or None
                business_type_ids = request.POST.getlist('business_type_ids')

                if Profile.objects.filter(mobile_number=mobile).exists():
                    profile = Profile.objects.get(mobile_number=mobile)
                    auth_login(request, profile.user)
                    return redirect('user_dashboard:trending')

                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=mobile,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            password=None,
                        )
                        user.set_unusable_password()
                        user.save()

                        profile = Profile.objects.create(
                            user=user,
                            mobile_number=mobile,
                            date_of_birth=dob,
                            business_name=business_name,
                            business_category_id=business_category_id,
                        )
                        if business_type_ids:
                            profile.business_types.set(business_type_ids)

                    auth_login(request, user)
                    request.session.pop('login_otp', None)
                    request.session.pop('login_mobile', None)
                    request.session.pop('login_purpose', None)
                    messages.success(request, f"Account registered! Welcome to Poster AI Studio, {first_name}!")
                    return redirect('user_dashboard:trending')
                except Exception as e:
                    error = f"Failed to create profile: {str(e)}"
                    step = '3'
    else:
        if request.GET.get('step') == '3' and request.session.get('login_mobile'):
            step = '3'
        elif request.GET.get('step') == '2' and request.session.get('login_mobile'):
            step = '2'
            stored_otp = request.session.get('login_otp', '123456')
            info_msg = f"OTP sent via SMS! (For testing, enter Test OTP: {stored_otp})"
        else:
            step = '1'

    return render(request, 'user_dashboard/login.html', {
        'step': step,
        'error': error,
        'info_msg': info_msg,
        'identifier': request.session.get('login_mobile', ''),
        'business_categories': business_categories,
        'business_types': business_types,
    })


@csrf_exempt
def user_logout(request):
    auth_logout(request)
    return redirect('user_dashboard:login')
