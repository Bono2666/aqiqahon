from datetime import date, timedelta
from .models import Order, AreaUser
from django.db import connection


def order_notification(request):
    drafts = Order.objects.filter(regional_id__in=AreaUser.objects.filter(user_id=request.user.user_id).values_list(
        'area_id', flat=True), order_status='draft', delivery_date__gte=date.today() - timedelta(days=90)).order_by('-order_id', 'regional')

    return len(list(drafts)) if drafts else 0
