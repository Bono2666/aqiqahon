from datetime import timedelta
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.utils import timezone
from .forms import LoginForm
from django.views.decorators.cache import cache_control


def _auto_schedule_confirmed_orders(user):
    from apps.models import Order, AreaUser

    three_months_ago = timezone.now() - timedelta(days=90)
    area_ids = AreaUser.objects.filter(user=user).values_list('area_id', flat=True)

    unscheduled_orders = Order.objects.filter(
        order_status='CONFIRMED',
        schedule_status='UNSCHEDULED',
        delivery_date__gte=three_months_ago,
        regional_id__in=area_ids,
    )

    return unscheduled_orders.count()


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_view(request):
    form = LoginForm(request.POST or None)

    msg = None

    if request.method == "POST":

        if form.is_valid():
            user_id = form.cleaned_data.get("user_id")
            password = form.cleaned_data.get("password")
            user = authenticate(user_id=user_id, password=password)
            if user is not None:
                login(request, user)
                _auto_schedule_confirmed_orders(user)
                return redirect(request.GET.get('next', 'home'))
            else:
                msg = 'Invalid User ID/Password'
        else:
            msg = 'Error validating the form.'

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


def forbidden_view(request):
    return render(request, "home/forbidden.html")
