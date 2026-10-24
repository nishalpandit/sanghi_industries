from master.models import SubscriptionPlan

def subscription_plans_processor(request):
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    except Exception:
        plans = []
    return {'global_subscription_plans': plans}
