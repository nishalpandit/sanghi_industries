from django.shortcuts import render
from master.models import SubscriptionPlan

def index(request):
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    context = {
        'subscription_plans': subscription_plans,
    }
    return render(request, 'webportal/index.html', context)
