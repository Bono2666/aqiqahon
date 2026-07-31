import datetime as dt
from datetime import date, timedelta
import glob
import io
import json
import os
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import connection, IntegrityError
from django.http import HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import render
from django.urls import reverse
from django.forms.models import modelformset_factory
from apps.forms import *
from apps.mail import send_email
from apps.models import *
from authentication.decorators import role_required
from tablib import Dataset
from django.utils import timezone
import xlwt
from django.http import HttpResponse
import xlsxwriter
from django.db.models import F, Sum, Q, Count, Max, Min
from django.db.models.functions import Coalesce
from . import host
from django.core.paginator import Paginator
from PyPDF2 import PdfMerger
from django.conf import settings
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.utils.text import Truncator
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.utils import simpleSplit
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from crum import get_current_user
from apps.notifications import order_notification
import re
from xml.sax.saxutils import escape
from django.contrib.staticfiles import finders

BULAN_ID = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
    7: 'Jul', 8: 'Agu', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'
}


def format_tanggal_id(tgl):
    return f"{tgl.day} {BULAN_ID[tgl.month]} {tgl.year}"


@login_required(login_url='/login/')
def home(request):
    return HttpResponseRedirect(reverse('dashboard'))


@login_required(login_url='/login/')
def dashboard(request):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    user_id = request.user.user_id

    filter_branch_list = request.GET.getlist('branch', [])
    filter_branch_list = [b for b in filter_branch_list if b and b != 'all']
    filter_date = request.GET.get('date', '')

    if filter_date:
        try:
            filter_date_obj = dt.datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            filter_date_obj = today
    else:
        filter_date_obj = today

    filter_date_tomorrow = filter_date_obj + timedelta(days=1)

    areas = AreaUser.objects.filter(user_id=user_id).values_list('area_id', flat=True)
    branches = AreaSales.objects.filter(area_id__in=areas).order_by('area_name')

    today_orders = Order.objects.filter(
        delivery_date__date=filter_date_obj,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])
    if filter_branch_list:
        today_orders = today_orders.filter(regional_id__in=filter_branch_list)

    total_today = today_orders.count()
    unscheduled = today_orders.filter(schedule_status='UNSCHEDULED').count()
    cooking = today_orders.filter(schedule_status__in=['SCHEDULED', 'COOKING']).count()
    packing = today_orders.filter(schedule_status='PACKING').count()
    ready = today_orders.filter(schedule_status='READY').count()
    on_delivery = today_orders.filter(schedule_status='ON_DELIVERY').count()
    completed = today_orders.filter(schedule_status='COMPLETED').count()

    order_packages = OrderPackage.objects.filter(
        order__delivery_date__date=filter_date_obj,
        order__regional_id__in=areas
    ).exclude(order__order_status__in=['PENDING', 'DRAFT', 'BATAL'])
    if filter_branch_list:
        order_packages = order_packages.filter(order__regional_id__in=filter_branch_list)

    total_kambing = order_packages.annotate(
        calculated_kambing=F('package__quantity') * F('quantity')
    ).aggregate(total=Sum('calculated_kambing'))['total'] or 0
    total_box = order_packages.annotate(
        calculated_box=F('box_qty') * F('quantity')
    ).aggregate(total=Sum('calculated_box'))['total'] or 0

    order_addons = OrderPackageAddon.objects.filter(
        order__delivery_date__date=filter_date_obj,
        order__regional_id__in=areas
    ).exclude(order__order_status__in=['PENDING', 'DRAFT', 'BATAL'])
    if filter_branch_list:
        order_addons = order_addons.filter(order__regional_id__in=filter_branch_list)

    addon_kemasan = order_addons.filter(
        equipment__tipe='Kemasan Dan Souvenir'
    ).values('equipment__equipment_name').annotate(
        total=Sum('quantity')
    ).filter(total__gt=0)

    addon_masakan = order_addons.filter(
        equipment__tipe='Masakan'
    ).values('equipment__equipment_name').annotate(
        total=Sum('quantity')
    ).filter(total__gt=0)

    addon_olahan = order_addons.filter(
        equipment__tipe='Olahan Dan Pendamping'
    ).values('equipment__equipment_name').annotate(
        total=Sum('quantity')
    ).filter(total__gt=0)

    box_paket_by_order_pkg = order_addons.filter(
        equipment__tipe='Box Paket'
    ).values('order_id', 'package_id').annotate(box_qty=Sum('quantity'))

    box_paket_lookup = {}
    for item in box_paket_by_order_pkg:
        try:
            op = OrderPackage.objects.select_related('package').get(
                order_id=item['order_id'], package_id=item['package_id']
            )
        except OrderPackage.DoesNotExist:
            continue
        qty = item['box_qty']
        for field in ['main_cuisine', 'sub_cuisine', 'side_cuisine1', 'side_cuisine2',
                      'side_cuisine3', 'side_cuisine4', 'side_cuisine5', 'rice',
                      'box_type', 'bag']:
            val = getattr(op, field, None)
            if val:
                box_paket_lookup[val] = box_paket_lookup.get(val, 0) + qty

    addon_box_paket_qty = sum(item['box_qty'] for item in box_paket_by_order_pkg)

    total_box_paket = total_box + addon_box_paket_qty

    dashboard_recap = order_packages.filter(
        package__dashboard__isnull=False
    ).values(
        'package__dashboard__dashboard_name'
    ).annotate(
        total=Sum('quantity')
    ).filter(total__gt=0).order_by('package__dashboard__display_order')

    recap_box_items = []
    box_type_values = order_packages.exclude(box_type__isnull=True).exclude(box_type='').values('box_type').annotate(
        total=Sum(F('package__box') * F('quantity'))
    ).order_by('box_type')
    for item in box_type_values:
        if (item['total'] or 0) > 0:
            recap_box_items.append({
                'name': item['box_type'],
                'count': item['total'] or 0,
            })
    bag_values = order_packages.exclude(bag__isnull=True).exclude(bag='').values('bag').annotate(
        total=Sum(F('package__box') * F('quantity'))
    ).order_by('bag')
    for item in bag_values:
        if (item['total'] or 0) > 0:
            recap_box_items.append({
                'name': item['bag'],
                'count': item['total'] or 0,
            })
    souvenir_values = order_packages.exclude(souvenir__isnull=True).exclude(souvenir='').values('souvenir').annotate(
        total=Sum('quantity')
    ).order_by('souvenir')
    for item in souvenir_values:
        if (item['total'] or 0) > 0:
            recap_box_items.append({
                'name': item['souvenir'],
                'count': item['total'] or 0,
            })

    for item in recap_box_items:
        item['count'] += box_paket_lookup.get(item['name'], 0)

    recap_masakan = order_packages.exclude(main_cuisine__isnull=True).exclude(main_cuisine='').values(
        'main_cuisine'
    ).annotate(total=Sum(F('package__box') * F('quantity'))).filter(total__gt=0).order_by('main_cuisine')

    recap_masakan = list(recap_masakan)
    for item in recap_masakan:
        item['total'] += box_paket_lookup.get(item['main_cuisine'], 0)

    menu_olahan_counter = {}
    for op in order_packages:
        for field_name in ['sub_cuisine', 'side_cuisine1', 'side_cuisine2', 'side_cuisine3', 'side_cuisine4', 'side_cuisine5', 'beverage']:
            val = getattr(op, field_name, None)
            if val:
                menu_olahan_counter[val] = menu_olahan_counter.get(val, 0) + (op.package.box * op.quantity)
        if op.rice:
            menu_olahan_counter[op.rice] = menu_olahan_counter.get(op.rice, 0) + (op.package.box * op.quantity)
    recap_menu_olahan = [{'name': k, 'count': v + box_paket_lookup.get(k, 0)} for k, v in sorted(menu_olahan_counter.items()) if v > 0 or box_paket_lookup.get(k, 0) > 0]

    dekorasi_per_order = order_packages.filter(
        package__dashboard__dashboard_name='Dekorasi'
    ).values('order_id').annotate(
        order_qty=Sum('quantity')
    ).filter(order_qty__gt=0)

    recap_dekorasi_laki = 0
    recap_dekorasi_perempuan = 0
    dekorasi_order_ids = [item['order_id'] for item in dekorasi_per_order]
    if dekorasi_order_ids:
        dekorasi_qty_map = {item['order_id']: item['order_qty'] for item in dekorasi_per_order}
        child_sex_map = {}
        for child in OrderChild.objects.filter(order_id__in=dekorasi_order_ids).order_by('id').values('order_id', 'child_sex'):
            child_sex_map.setdefault(child['order_id'], child['child_sex'])
        for order_id, qty in dekorasi_qty_map.items():
            sex = child_sex_map.get(order_id)
            if sex == '1':
                recap_dekorasi_laki += qty
            elif sex == '2':
                recap_dekorasi_perempuan += qty

    recap_nasi_box = list(order_packages.filter(
        package__dashboard__dashboard_name__icontains='nasi box'
    ).values(
        'package__package_name'
    ).annotate(
        total=Sum('quantity')
    ).filter(total__gt=0))
    total_nasi_box = sum(item['total'] for item in recap_nasi_box)

    kambing_packages = order_packages.filter(
        package__dashboard__dashboard_name__icontains='paket kambing'
    )
    daging_counter = {}
    olahan_counter = {}
    for op in kambing_packages:
        if op.main_cuisine:
            mc = MainCuisine.objects.filter(
                package=op.package, cuisine__cuisine_name=op.main_cuisine
            ).first()
            if mc:
                daging_counter[op.main_cuisine] = daging_counter.get(op.main_cuisine, 0) + (mc.porsi * op.quantity)
        for field_name in ['sub_cuisine', 'side_cuisine1', 'side_cuisine2', 'side_cuisine3', 'side_cuisine4', 'side_cuisine5']:
            val = getattr(op, field_name, None)
            if val:
                sc = SubCuisine.objects.filter(
                    package=op.package, cuisine__cuisine_name=val
                ).first()
                porsi = sc.porsi if sc else 0
                olahan_counter[val] = olahan_counter.get(val, 0) + (porsi * op.quantity)
    recap_paket_kambing_daging = [{'name': k, 'count': v} for k, v in sorted(daging_counter.items()) if v > 0]
    recap_paket_kambing_olahan = [{'name': k, 'count': v} for k, v in sorted(olahan_counter.items()) if v > 0]

    goat_types = GoatType.objects.filter(active=True).order_by('display_order')
    goat_type_recap_jantan = []
    goat_type_recap_betina = []
    total_type_kambing_jantan = 0
    total_type_kambing_betina = 0
    for gt in goat_types:
        count_jantan = (
            order_packages.filter(
                package__goat_type=gt, package__goat_type2__isnull=True, type='Jantan'
            ).annotate(calculated=F('package__quantity') * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        ) + (
            order_packages.filter(
                package__goat_type=gt, package__goat_type2__isnull=False, type='Jantan'
            ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        ) + (
            order_packages.filter(
                package__goat_type2=gt, package__goat_type2__isnull=False, type='Jantan'
            ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        )
        count_betina = (
            order_packages.filter(
                package__goat_type=gt, package__goat_type2__isnull=True, type='Betina'
            ).annotate(calculated=F('package__quantity') * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        ) + (
            order_packages.filter(
                package__goat_type=gt, package__goat_type2__isnull=False, type='Betina'
            ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        ) + (
            order_packages.filter(
                package__goat_type2=gt, package__goat_type2__isnull=False, type='Betina'
            ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
        )
        total_type_kambing_jantan += count_jantan
        total_type_kambing_betina += count_betina
        if count_jantan > 0:
            goat_type_recap_jantan.append({
                'name': gt.goat_type_name,
                'count': count_jantan,
            })
        if count_betina > 0:
            goat_type_recap_betina.append({
                'name': gt.goat_type_name,
                'count': count_betina,
            })

    recap_kambing_guling = []
    total_kambing_guling = 0
    kambing_guling_packages = order_packages.filter(
        package__dashboard__dashboard_name__icontains='kambing guling'
    )
    for gt in goat_types:
        for tipe in ['Jantan', 'Betina']:
            count = (
                kambing_guling_packages.filter(
                    package__goat_type=gt, package__goat_type2__isnull=True, type=tipe
                ).annotate(calculated=F('package__quantity') * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
            ) + (
                kambing_guling_packages.filter(
                    package__goat_type=gt, package__goat_type2__isnull=False, type=tipe
                ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
            ) + (
                kambing_guling_packages.filter(
                    package__goat_type2=gt, package__goat_type2__isnull=False, type=tipe
                ).annotate(calculated=1 * F('quantity')).aggregate(total=Sum('calculated'))['total'] or 0
            )
            if count > 0:
                recap_kambing_guling.append({
                    'name': gt.goat_type_name,
                    'tipe': tipe,
                    'count': count,
                })
            total_kambing_guling += count

    recap_nampan = list(order_packages.filter(
        package__dashboard__dashboard_name__icontains='nampan'
    ).values(
        'package__package_name'
    ).annotate(
        total=Sum('quantity')
    ).filter(total__gt=0))
    total_nampan = sum(item['total'] for item in recap_nampan)

    recap_qurban = list(order_packages.filter(
        package__dashboard__dashboard_name__icontains='qurban'
    ).values(
        'package__package_name'
    ).annotate(
        total=Sum('quantity')
    ).filter(total__gt=0))
    total_qurban = sum(item['total'] for item in recap_qurban)

    driver_name = request.user.username
    today_driver = today_orders.exclude(schedule_status='COMPLETED')
    tomorrow_orders = Order.objects.filter(
        delivery_date__date=filter_date_tomorrow,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])
    if filter_branch_list:
        tomorrow_orders = tomorrow_orders.filter(regional_id__in=filter_branch_list)
    history_driver = today_orders.filter(
        schedule_status='COMPLETED'
    )

    context = {
        'notif': order_notification(request),
        'segment': 'dashboard',
        'group_segment': 'dashboard',
        'role': Auth.objects.filter(user_id=user_id).values_list('menu_id', flat=True),
        'total_today': total_today,
        'unscheduled': unscheduled,
        'cooking': cooking,
        'packing': packing,
        'ready': ready,
        'on_delivery': on_delivery,
        'completed': completed,
        'total_kambing': total_kambing,
        'total_box': total_box,
        'total_box_paket': total_box_paket,
        'dashboard_recap': dashboard_recap,
        'recap_box_items': recap_box_items,
        'recap_masakan': recap_masakan,
        'recap_menu_olahan': recap_menu_olahan,
        'recap_dekorasi_laki': recap_dekorasi_laki,
        'recap_dekorasi_perempuan': recap_dekorasi_perempuan,
        'recap_nasi_box': recap_nasi_box,
        'total_nasi_box': total_nasi_box,
        'recap_paket_kambing_daging': recap_paket_kambing_daging,
        'recap_paket_kambing_olahan': recap_paket_kambing_olahan,
        'recap_kambing_guling': recap_kambing_guling,
        'total_kambing_guling': total_kambing_guling,
        'recap_nampan': recap_nampan,
        'total_nampan': total_nampan,
        'recap_qurban': recap_qurban,
        'total_qurban': total_qurban,

        'goat_type_recap_jantan': goat_type_recap_jantan,
        'goat_type_recap_betina': goat_type_recap_betina,
        'total_type_kambing_jantan': total_type_kambing_jantan,
        'total_type_kambing_betina': total_type_kambing_betina,
        'today_driver': today_driver,
        'tomorrow_orders': tomorrow_orders,
        'history_driver': history_driver,
        'branches': branches,
        'filter_branch_list': filter_branch_list,
        'filter_date': filter_date if filter_date else today.isoformat(),
        'filter_date_label': format_tanggal_id(filter_date_obj) if filter_date_obj != today else '',
        'filter_date_tomorrow_label': format_tanggal_id(filter_date_tomorrow) if filter_date_obj != today else '',
        'is_filter_active': filter_date_obj != today or bool(filter_branch_list),
    }
    return render(request, 'home/dashboard.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_index(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, username, email, position_name FROM apps_user INNER JOIN apps_position ON apps_user.position_id = apps_position.position_id")
        users = cursor.fetchall()

    context = {
        'data': users,
        'notif': order_notification(request),
        'segment': 'user',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/user_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_add(request):
    position = Position.objects.all()
    if request.POST:
        form = FormUser(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            if not settings.DEBUG and form.instance.signature:
                user = User.objects.get(user_id=form.instance.user_id)
                my_file = user.signature
                filename = '../aqiqahon.sahabataqiqah.co.id/apps/media/' + my_file.name
                with open(filename, 'wb+') as temp_file:
                    for chunk in my_file.chunks():
                        temp_file.write(chunk)

            return HttpResponseRedirect(reverse('user-view', args=[form.instance.user_id, ]))
        else:
            message = form.errors
            context = {
                'form': form,
                'position': position,
                'notif': order_notification(request),
                'segment': 'user',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/user_add.html', context)
    else:
        form = FormUser()
        context = {
            'form': form,
            'position': position,
            'notif': order_notification(request),
            'segment': 'user',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/user_add.html', context)


# View User
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_view(request, _id):
    users = User.objects.get(user_id=_id)
    auth = Auth.objects.filter(user_id=_id)
    area = AreaUser.objects.filter(user_id=_id)
    form = FormUserView(instance=users)
    position = Position.objects.all()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_menu.menu_id, menu_name, q_auth.menu_id FROM apps_menu LEFT JOIN (SELECT * FROM apps_auth WHERE user_id = '" + str(_id) + "') AS q_auth ON apps_menu.menu_id = q_auth.menu_id WHERE q_auth.menu_id IS NULL")
        menu = cursor.fetchall()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_areasales.area_id, area_name, q_area.area_id FROM apps_areasales LEFT JOIN (SELECT * FROM apps_areauser WHERE user_id = '" + str(_id) + "') AS q_area ON apps_areasales.area_id = q_area.area_id WHERE q_area.area_id IS NULL")
        item_area = cursor.fetchall()

    if request.POST:
        check = request.POST.getlist('checks[]')
        for i in menu:
            if str(i[0]) in check:
                try:
                    auth = Auth(user_id=_id, menu_id=i[0])
                    auth.save()
                except IntegrityError:
                    continue
            else:
                Auth.objects.filter(user_id=_id, menu_id=i[0]).delete()

        return HttpResponseRedirect(reverse('user-view', args=[_id, ]))

    context = {
        'form': form,
        'formAuth': form,
        'data': users,
        'auth': auth,
        'menu': menu,
        'area': area,
        'item_area': item_area,
        'positions': position,
        'notif': order_notification(request),
        'segment': 'user',
        'group_segment': 'master',
        'tab': 'auth',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/user_view.html', context)


# View User Area
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_area_view(request, _id):
    users = User.objects.get(user_id=_id)
    auth = Auth.objects.filter(user_id=_id)
    area = AreaUser.objects.filter(user_id=_id)
    form = FormUserView(instance=users)
    position = Position.objects.all()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_menu.menu_id, menu_name, q_auth.menu_id FROM apps_menu LEFT JOIN (SELECT * FROM apps_auth WHERE user_id = '" + str(_id) + "') AS q_auth ON apps_menu.menu_id = q_auth.menu_id WHERE q_auth.menu_id IS NULL")
        menu = cursor.fetchall()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_areasales.area_id, area_name, q_area.area_id FROM apps_areasales LEFT JOIN (SELECT * FROM apps_areauser WHERE user_id = '" + str(_id) + "') AS q_area ON apps_areasales.area_id = q_area.area_id WHERE q_area.area_id IS NULL")
        item_area = cursor.fetchall()

    if request.POST:
        area_check = request.POST.getlist('area[]')
        for i in item_area:
            if str(i[0]) in area_check:
                try:
                    area = AreaUser(user_id=_id, area_id=i[0])
                    area.save()
                except IntegrityError:
                    continue
            else:
                AreaUser.objects.filter(user_id=_id, area_id=i[0]).delete()

        return HttpResponseRedirect(reverse('user-area-view', args=[_id, ]))

    context = {
        'form': form,
        'formAuth': form,
        'data': users,
        'auth': auth,
        'menu': menu,
        'area': area,
        'item_area': item_area,
        'positions': position,
        'notif': order_notification(request),
        'segment': 'user',
        'group_segment': 'master',
        'tab': 'area',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/user_view.html', context)


# Update Auth
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def auth_update(request, _id, _menu):
    auth = Auth.objects.get(user=_id, menu=_menu)

    if request.POST:
        auth.add = 1 if request.POST.get('add') else 0
        auth.edit = 1 if request.POST.get('edit') else 0
        auth.delete = 1 if request.POST.get('delete') else 0
        auth.save()

        return HttpResponseRedirect(reverse('user-view', args=[_id, ]))

    return render(request, 'home/user_view.html')


# Delete Auth
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def auth_delete(request, _id, _menu):
    auth = Auth.objects.filter(user=_id, menu=_menu)

    auth.delete()
    return HttpResponseRedirect(reverse('user-view', args=[_id, ]))


# Delete AreaUser
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def area_user_delete(request, _id, _area):
    area = AreaUser.objects.filter(user=_id, area=_area)

    area.delete()
    return HttpResponseRedirect(reverse('user-area-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def remove_signature(request, _id):
    users = User.objects.get(user_id=_id)
    users.signature = None
    users.save()
    return HttpResponseRedirect(reverse('user-view', args=[_id, ]))


# Update User
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_update(request, _id):
    users = User.objects.get(user_id=_id)
    position = Position.objects.all()
    auth = Auth.objects.filter(user_id=_id)
    area = AreaUser.objects.filter(user_id=_id)

    if request.POST:
        form = FormUserUpdate(request.POST, request.FILES, instance=users)
        if form.is_valid():
            form.save()
            if not settings.DEBUG and users.signature:
                my_file = users.signature
                filename = '../aqiqahon.sahabataqiqah.co.id/apps/media/' + my_file.name
                with open(filename, 'wb+') as temp_file:
                    for chunk in my_file.chunks():
                        temp_file.write(chunk)
            return HttpResponseRedirect(reverse('user-view', args=[_id, ]))
    else:
        form = FormUserUpdate(instance=users)

    message = form.errors
    context = {
        'form': form,
        'data': users,
        'positions': position,
        'auth': auth,
        'area': area,
        'notif': order_notification(request),
        'segment': 'user',
        'group_segment': 'master',
        'crud': 'update',
        'tab': 'auth',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/user_view.html', context)


# Delete User
@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def user_delete(request, _id):
    users = User.objects.get(user_id=_id)

    users.delete()
    return HttpResponseRedirect(reverse('user-index'))


@login_required(login_url='/login/')
def change_password(request):
    if request.POST:
        form = FormChangePassword(data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return HttpResponseRedirect(reverse('home'))
    else:
        form = FormChangePassword(user=request.user)

    message = form.errors
    context = {
        'form': form,
        'data': request.user,
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
    }
    return render(request, 'home/user_change_password.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='USER')
def set_password(request, _id):
    users = User.objects.get(user_id=_id)
    if request.POST:
        form = FormSetPassword(data=request.POST, user=users)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return HttpResponseRedirect(reverse('user-view', args=[_id, ]))
    else:
        form = FormSetPassword(user=users)

    message = form.errors
    context = {
        'form': form,
        'data': users,
        'notif': order_notification(request),
        'segment': 'user',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='USER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/user_set_password.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_index(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT promo_id, promo_name, promo_limit FROM apps_promo")
        promos = cursor.fetchall()

    context = {
        'data': promos,
        'notif': order_notification(request),
        'segment': 'promo',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PROMO') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/promo_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_add(request):
    if request.POST:
        form = FormPromo(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('promo-view', args=[form.instance.promo_id, ]))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'promo',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PROMO') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/promo_add.html', context)
    else:
        form = FormPromo()
        error = form.errors
        context = {
            'form': form,
            'notif': order_notification(request),
            'message': error,
            'segment': 'promo',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PROMO') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/promo_add.html', context)


# View Promo
@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_view(request, _id):
    promos = Promo.objects.get(promo_id=_id)
    form = FormPromoView(instance=promos)
    detail = PromoDetail.objects.filter(promo_id=_id)

    if request.POST:
        gift = PromoDetail(promo_id=_id, gift=request.POST.get(
            'gift'), nominal=request.POST.get('nominal'))
        gift.save()
        return HttpResponseRedirect(reverse('promo-view', args=[_id, ]))

    context = {
        'form': form,
        'data': promos,
        'detail': detail,
        'notif': order_notification(request),
        'segment': 'promo',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PROMO') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/promo_view.html', context)


# Update Promo
@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_update(request, _id):
    promos = Promo.objects.get(promo_id=_id)
    if request.POST:
        form = FormPromoUpdate(
            request.POST, request.FILES, instance=promos)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('promo-view', args=[_id, ]))
    else:
        form = FormPromoUpdate(instance=promos)

    message = form.errors
    context = {
        'form': form,
        'data': promos,
        'notif': order_notification(request),
        'segment': 'promo',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PROMO') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/promo_view.html', context)


# Delete Promo
@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_delete(request, _id):
    promos = Promo.objects.get(promo_id=_id)

    promos.delete()
    return HttpResponseRedirect(reverse('promo-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_detail_update(request, _id):
    promo_detail = PromoDetail.objects.get(id=_id)
    if request.POST:
        promo_detail.gift = request.POST.get('gift')
        promo_detail.nominal = request.POST.get('nominal')
        promo_detail.save()
        return HttpResponseRedirect(reverse('promo-view', args=[promo_detail.promo_id, ]))

    return render(request, 'home/promo_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PROMO')
def promo_detail_delete(request, _id):
    promo_detail = PromoDetail.objects.get(id=_id)

    promo_detail.delete()
    return HttpResponseRedirect(reverse('promo-view', args=[promo_detail.promo_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='AREA')
def area_sales_index(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT area_id, area_name, username FROM apps_areasales INNER JOIN apps_user ON apps_areasales.manager = apps_user.user_id")
        area_sales = cursor.fetchall()

    context = {
        'data': area_sales,
        'notif': order_notification(request),
        'segment': 'area_sales',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='AREA') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/area_sales_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='AREA')
def area_sales_add(request):
    manager = User.objects.filter(position_id='ASM')

    if request.POST:
        form = FormAreaSales(request.POST, request.FILES)

        if form.is_valid():
            new = form.save(commit=False)
            new.area_id = form.cleaned_data.get('area_id').replace(' ', '')
            new.form = host.url + 'order/new/' + new.area_id
            new.save()
            return HttpResponseRedirect(reverse('area-sales-view', args=[form.instance.area_id, ]))
        else:
            message = form.errors
            context = {
                'form': form,
                'manager': manager,
                'notif': order_notification(request),
                'segment': 'area_sales',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='AREA') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/area_sales_add.html', context)
    else:
        form = FormAreaSales()
        message = form.errors

        context = {
            'form': form,
            'manager': manager,
            'notif': order_notification(request),
            'segment': 'area_sales',
            'group_segment': 'master',
            'crud': 'add',
            'message': message,
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='AREA') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/area_sales_add.html', context)


# View Area Sales
@login_required(login_url='/login/')
@role_required(allowed_roles='AREA')
def area_sales_view(request, _id):
    area_sales = AreaSales.objects.get(area_id=_id)
    form = FormAreaSalesView(instance=area_sales)
    managers = User.objects.filter(position_id='ASM')

    context = {
        'form': form,
        'data': area_sales,
        'managers': managers,
        'notif': order_notification(request),
        'segment': 'area_sales',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='AREA') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/area_sales_view.html', context)


# Update Area Sales
@login_required(login_url='/login/')
@role_required(allowed_roles='AREA')
def area_sales_update(request, _id):
    area_sales = AreaSales.objects.get(area_id=_id)
    managers = User.objects.filter(position_id='ASM')

    if request.POST:
        form = FormAreaSalesUpdate(
            request.POST, request.FILES, instance=area_sales)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('area-sales-view', args=[_id, ]))
    else:
        form = FormAreaSalesUpdate(instance=area_sales)

    message = form.errors
    context = {
        'form': form,
        'data': area_sales,
        'managers': managers,
        'notif': order_notification(request),
        'segment': 'area_sales',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='AREA') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/area_sales_view.html', context)


# Delete Area Sales
@login_required(login_url='/login/')
@role_required(allowed_roles='AREA')
def area_sales_delete(request, _id):
    area_sales = AreaSales.objects.get(area_id=_id)

    area_sales.delete()
    return HttpResponseRedirect(reverse('area-sales-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='POSITION')
def position_add(request):
    if request.POST:
        form = FormPosition(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('position-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'position',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='POSITION') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/position_add.html', context)
    else:
        form = FormPosition()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'position',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='POSITION') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/position_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='POSITION')
def position_index(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT position_id, position_name FROM apps_position")
        positions = cursor.fetchall()

    context = {
        'data': positions,
        'notif': order_notification(request),
        'segment': 'position',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='POSITION') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/position_index.html', context)


# Update Position
@login_required(login_url='/login/')
@role_required(allowed_roles='POSITION')
def position_update(request, _id):
    positions = Position.objects.get(position_id=_id)
    if request.POST:
        form = FormPositionUpdate(
            request.POST, request.FILES, instance=positions)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('position-view', args=[_id, ]))
    else:
        form = FormPositionUpdate(instance=positions)

    message = form.errors
    context = {
        'form': form,
        'data': positions,
        'notif': order_notification(request),
        'segment': 'position',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='POSITION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/position_view.html', context)


# Delete Position
@login_required(login_url='/login/')
@role_required(allowed_roles='POSITION')
def position_delete(request, _id):
    positions = Position.objects.get(position_id=_id)

    positions.delete()
    return HttpResponseRedirect(reverse('position-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='POSITION')
def position_view(request, _id):
    positions = Position.objects.get(position_id=_id)
    form = FormPositionView(instance=positions)

    context = {
        'form': form,
        'data': positions,
        'notif': order_notification(request),
        'segment': 'position',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='POSITION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/position_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='MENU')
def menu_add(request):
    if request.POST:
        form = FormMenu(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('menu-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'menu',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='MENU') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/menu_add.html', context)
    else:
        form = FormMenu()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'menu',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='MENU') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/menu_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='MENU')
def menu_index(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT menu_id, menu_name, menu_remark FROM apps_menu")
        menus = cursor.fetchall()

    context = {
        'data': menus,
        'notif': order_notification(request),
        'segment': 'menu',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='MENU') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/menu_index.html', context)


# Update Menu
@login_required(login_url='/login/')
@role_required(allowed_roles='MENU')
def menu_update(request, _id):
    menus = Menu.objects.get(menu_id=_id)
    if request.POST:
        form = FormMenuUpdate(request.POST, request.FILES, instance=menus)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('menu-view', args=[_id, ]))
    else:
        form = FormMenuUpdate(instance=menus)

    message = form.errors
    context = {
        'form': form,
        'data': menus,
        'notif': order_notification(request),
        'segment': 'menu',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='MENU') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/menu_view.html', context)


# Delete Menu
@login_required(login_url='/login/')
@role_required(allowed_roles='MENU')
def menu_delete(request, _id):
    menus = Menu.objects.get(menu_id=_id)

    menus.delete()
    return HttpResponseRedirect(reverse('menu-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='MENU')
def menu_view(request, _id):
    menus = Menu.objects.get(menu_id=_id)
    form = FormMenuView(instance=menus)

    context = {
        'form': form,
        'data': menus,
        'notif': order_notification(request),
        'segment': 'menu',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='MENU') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/menu_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CHANNEL')
def channel_add(request):
    if request.POST:
        form = FormChannel(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('channel-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'channel',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CHANNEL') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/channel_add.html', context)
    else:
        form = FormChannel()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'channel',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CHANNEL') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/channel_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CHANNEL')
def channel_index(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT channel_id, channel_name FROM apps_channel")
        channels = cursor.fetchall()

    context = {
        'data': channels,
        'notif': order_notification(request),
        'segment': 'channel',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CHANNEL') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/channel_index.html', context)


# Update Channel
@login_required(login_url='/login/')
@role_required(allowed_roles='CHANNEL')
def channel_update(request, _id):
    channels = Channel.objects.get(channel_id=_id)
    if request.POST:
        form = FormChannelUpdate(
            request.POST, request.FILES, instance=channels)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('channel-view', args=[_id, ]))
    else:
        form = FormChannelUpdate(instance=channels)

    message = form.errors
    context = {
        'form': form,
        'data': channels,
        'notif': order_notification(request),
        'segment': 'channel',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CHANNEL') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/channel_view.html', context)


# Delete Channel
@login_required(login_url='/login/')
@role_required(allowed_roles='CHANNEL')
def channel_delete(request, _id):
    channels = Channel.objects.get(channel_id=_id)

    channels.delete()
    return HttpResponseRedirect(reverse('channel-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='CHANNEL')
def channel_view(request, _id):
    channels = Channel.objects.get(channel_id=_id)
    form = FormChannelView(instance=channels)

    context = {
        'form': form,
        'data': channels,
        'notif': order_notification(request),
        'segment': 'channel',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CHANNEL') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/channel_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUISINE')
def cuisine_index(request):
    cuisines = Cuisine.objects.all()

    context = {
        'data': cuisines,
        'notif': order_notification(request),
        'segment': 'cuisine',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUISINE') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/cuisine_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUISINE')
def cuisine_add(request):
    if request.POST:
        form = FormCuisine(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('cuisine-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'cuisine',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUISINE') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/cuisine_add.html', context)
    else:
        form = FormCuisine()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'cuisine',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUISINE') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/cuisine_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUISINE')
def cuisine_view(request, _id):
    cuisines = Cuisine.objects.get(cuisine_id=_id)
    form = FormCuisineView(instance=cuisines)

    context = {
        'form': form,
        'data': cuisines,
        'notif': order_notification(request),
        'segment': 'cuisine',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUISINE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/cuisine_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUISINE')
def cuisine_update(request, _id):
    cuisines = Cuisine.objects.get(cuisine_id=_id)
    if request.POST:
        form = FormCuisineUpdate(
            request.POST, request.FILES, instance=cuisines)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('cuisine-view', args=[_id, ]))
    else:
        form = FormCuisineUpdate(instance=cuisines)

    message = form.errors
    context = {
        'form': form,
        'data': cuisines,
        'notif': order_notification(request),
        'segment': 'cuisine',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUISINE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/cuisine_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUISINE')
def cuisine_delete(request, _id):
    cuisines = Cuisine.objects.get(cuisine_id=_id)

    cuisines.delete()
    return HttpResponseRedirect(reverse('cuisine-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='EQUIPMENT')
def equipment_index(request):
    equipments = Equipment.objects.all()

    context = {
        'data': equipments,
        'notif': order_notification(request),
        'segment': 'equipment',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='EQUIPMENT') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/equipment_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='EQUIPMENT')
def equipment_add(request):
    if request.POST:
        form = FormEquipment(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('equipment-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'equipment',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='EQUIPMENT') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/equipment_add.html', context)
    else:
        form = FormEquipment()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'equipment',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='EQUIPMENT') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/equipment_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='EQUIPMENT')
def equipment_view(request, _id):
    equipments = Equipment.objects.get(equipment_id=_id)
    form = FormEquipmentView(instance=equipments)

    context = {
        'form': form,
        'data': equipments,
        'notif': order_notification(request),
        'segment': 'equipment',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='EQUIPMENT') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/equipment_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='EQUIPMENT')
def equipment_update(request, _id):
    equipments = Equipment.objects.get(equipment_id=_id)
    if request.POST:
        form = FormEquipmentUpdate(
            request.POST, request.FILES, instance=equipments)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('equipment-view', args=[_id, ]))
    else:
        form = FormEquipmentUpdate(instance=equipments)

    message = form.errors
    context = {
        'form': form,
        'data': equipments,
        'notif': order_notification(request),
        'segment': 'equipment',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='EQUIPMENT') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/equipment_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='EQUIPMENT')
def equipment_delete(request, _id):
    equipments = Equipment.objects.get(equipment_id=_id)

    equipments.delete()
    return HttpResponseRedirect(reverse('equipment-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='CATEGORY')
def category_index(request):
    categories = Category.objects.all()

    context = {
        'data': categories,
        'notif': order_notification(request),
        'segment': 'category',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CATEGORY') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/category_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CATEGORY')
def category_add(request):
    if request.POST:
        form = FormCategory(request.POST, request.FILES)
        if form.is_valid():
            add = form.save(commit=False)
            add.active = True if request.POST.get('active') else False
            add.save()
            return HttpResponseRedirect(reverse('category-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'category',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CATEGORY') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/category_add.html', context)
    else:
        form = FormCategory()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'category',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CATEGORY') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/category_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CATEGORY')
def category_view(request, _id):
    categories = Category.objects.get(category_id=_id)
    form = FormCategoryView(instance=categories)

    context = {
        'form': form,
        'data': categories,
        'notif': order_notification(request),
        'segment': 'category',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CATEGORY') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/category_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CATEGORY')
def category_update(request, _id):
    categories = Category.objects.get(category_id=_id)
    if request.POST:
        form = FormCategoryUpdate(
            request.POST, request.FILES, instance=categories)
        if form.is_valid():
            update = form.save(commit=False)
            update.active = True if request.POST.get('active') else False
            update.save()
            return HttpResponseRedirect(reverse('category-view', args=[_id, ]))
    else:
        form = FormCategoryUpdate(instance=categories)

    message = form.errors
    context = {
        'form': form,
        'data': categories,
        'notif': order_notification(request),
        'segment': 'category',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CATEGORY') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/category_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CATEGORY')
def category_delete(request, _id):
    categories = Category.objects.get(category_id=_id)

    categories.delete()
    return HttpResponseRedirect(reverse('category-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='GOATTYPE')
def goat_type_index(request):
    goat_types = GoatType.objects.all()

    context = {
        'data': goat_types,
        'notif': order_notification(request),
        'segment': 'goat_type',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='GOATTYPE') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/goat_type_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='GOATTYPE')
def goat_type_add(request):
    if request.POST:
        form = FormGoatType(request.POST, request.FILES)
        if form.is_valid():
            add = form.save(commit=False)
            add.active = True if request.POST.get('active') else False
            add.save()
            return HttpResponseRedirect(reverse('goat-type-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'goat_type',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='GOATTYPE') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/goat_type_add.html', context)
    else:
        form = FormGoatType()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'goat_type',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='GOATTYPE') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/goat_type_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='GOATTYPE')
def goat_type_view(request, _id):
    goat_types = GoatType.objects.get(goat_type_id=_id)
    form = FormGoatTypeView(instance=goat_types)

    context = {
        'form': form,
        'data': goat_types,
        'notif': order_notification(request),
        'segment': 'goat_type',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='GOATTYPE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/goat_type_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='GOATTYPE')
def goat_type_update(request, _id):
    goat_types = GoatType.objects.get(goat_type_id=_id)
    if request.POST:
        form = FormGoatTypeUpdate(
            request.POST, request.FILES, instance=goat_types)
        if form.is_valid():
            update = form.save(commit=False)
            update.active = True if request.POST.get('active') else False
            update.save()
            return HttpResponseRedirect(reverse('goat-type-view', args=[_id, ]))
    else:
        form = FormGoatTypeUpdate(instance=goat_types)

    message = form.errors
    context = {
        'form': form,
        'data': goat_types,
        'notif': order_notification(request),
        'segment': 'goat_type',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='GOATTYPE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/goat_type_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='GOATTYPE')
def goat_type_delete(request, _id):
    goat_types = GoatType.objects.get(goat_type_id=_id)

    goat_types.delete()
    return HttpResponseRedirect(reverse('goat-type-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='DASHBOARD')
def dashboard_card_index(request):
    dashboards = Dashboard.objects.all()

    context = {
        'data': dashboards,
        'notif': order_notification(request),
        'segment': 'dashboard_card',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='DASHBOARD') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/dashboard_card_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='DASHBOARD')
def dashboard_card_add(request):
    if request.POST:
        form = FormDashboard(request.POST, request.FILES)
        if form.is_valid():
            add = form.save(commit=False)
            add.active = True if request.POST.get('active') else False
            add.save()
            return HttpResponseRedirect(reverse('dashboard-card-index'))
        else:
            message = form.errors
            context = {
                'form': form,
                'notif': order_notification(request),
                'segment': 'dashboard_card',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='DASHBOARD') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/dashboard_card_add.html', context)
    else:
        form = FormDashboard()
        context = {
            'form': form,
            'notif': order_notification(request),
            'segment': 'dashboard_card',
            'group_segment': 'master',
            'crud': 'add',
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='DASHBOARD') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/dashboard_card_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='DASHBOARD')
def dashboard_card_view(request, _id):
    dashboards = Dashboard.objects.get(dashboard_id=_id)
    form = FormDashboardView(instance=dashboards)

    context = {
        'form': form,
        'data': dashboards,
        'notif': order_notification(request),
        'segment': 'dashboard_card',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='DASHBOARD') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/dashboard_card_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='DASHBOARD')
def dashboard_card_update(request, _id):
    dashboards = Dashboard.objects.get(dashboard_id=_id)
    if request.POST:
        form = FormDashboardUpdate(
            request.POST, request.FILES, instance=dashboards)
        if form.is_valid():
            update = form.save(commit=False)
            update.active = True if request.POST.get('active') else False
            update.save()
            return HttpResponseRedirect(reverse('dashboard-card-view', args=[_id, ]))
    else:
        form = FormDashboardUpdate(instance=dashboards)

    message = form.errors
    context = {
        'form': form,
        'data': dashboards,
        'notif': order_notification(request),
        'segment': 'dashboard_card',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='DASHBOARD') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/dashboard_card_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='DASHBOARD')
def dashboard_card_delete(request, _id):
    dashboards = Dashboard.objects.get(dashboard_id=_id)

    dashboards.delete()
    return HttpResponseRedirect(reverse('dashboard-card-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_index(request):
    packages = Package.objects.all()

    context = {
        'data': packages,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/package_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_add(request):
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    if request.POST:
        form = FormPackage(request.POST, request.FILES)
        if form.is_valid():
            new = form.save(commit=False)
            new.category_id = request.POST.get('category')
            new.type = request.POST.get('type')
            new.active = True if request.POST.get('active') else False
            new.promo = True if request.POST.get('promo') else False
            goat_type_id = request.POST.get('goat_type')
            if goat_type_id:
                new.goat_type_id = goat_type_id
            goat_type2_id = request.POST.get('goat_type2')
            if goat_type2_id:
                new.goat_type2_id = goat_type2_id
            dashboard_id = request.POST.get('dashboard')
            if dashboard_id:
                new.dashboard_id = dashboard_id
            new.save()
            return HttpResponseRedirect(reverse('package-view', args=[new.package_id, ]))
        else:
            message = form.errors
            context = {
                'form': form,
                'categories': categories,
                'goat_types': goat_types,
                'dashboards': dashboards,
                'notif': order_notification(request),
                'segment': 'package',
                'group_segment': 'master',
                'crud': 'add',
                'message': message,
                'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
            }
            return render(request, 'home/package_add.html', context)
    else:
        form = FormPackage()
        message = form.errors
        context = {
            'form': form,
            'categories': categories,
            'goat_types': goat_types,
            'dashboards': dashboards,
            'notif': order_notification(request),
            'segment': 'package',
            'group_segment': 'master',
            'crud': 'add',
            'message': message,
            'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
            'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
        }
        return render(request, 'home/package_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_rice_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('rice[]')
        for i in rices:
            if str(i.cuisine_id) in check:
                try:
                    rice = Rice(
                        package=packages, cuisine=i)
                    rice.save()
                except IntegrityError:
                    continue
            else:
                Rice.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-rice-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'beverage',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('main_cuisine[]')
        for i in main_cuisines:
            if str(i.cuisine_id) in check:
                try:
                    main_cuisine = MainCuisine(
                        package=packages, cuisine=i)
                    main_cuisine.save()
                except IntegrityError:
                    continue
            else:
                MainCuisine.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'beverage',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_subcuisine_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('sub_cuisine[]')
        for i in sub_cuisines:
            if str(i.cuisine_id) in check:
                try:
                    sub_cuisine = SubCuisine(
                        package=packages, cuisine=i)
                    sub_cuisine.save()
                except IntegrityError:
                    continue
            else:
                SubCuisine.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-subcuisine-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'sub_cuisine',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine1_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('side_cuisine1[]')
        for i in side_cuisines1:
            if str(i.cuisine_id) in check:
                try:
                    side_cuisine1 = SideCuisine1(
                        package=packages, cuisine=i)
                    side_cuisine1.save()
                except IntegrityError:
                    continue
            else:
                SideCuisine1.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-sidecuisine1-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'side_cuisine1',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine2_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('side_cuisine2[]')
        for i in side_cuisines2:
            if str(i.cuisine_id) in check:
                try:
                    side_cuisine2 = SideCuisine2(
                        package=packages, cuisine=i)
                    side_cuisine2.save()
                except IntegrityError:
                    continue
            else:
                SideCuisine2.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-sidecuisine2-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenir': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'side_cuisine2',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine3_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('side_cuisine3[]')
        for i in side_cuisines3:
            if str(i.cuisine_id) in check:
                try:
                    side_cuisine3 = SideCuisine3(
                        package=packages, cuisine=i)
                    side_cuisine3.save()
                except IntegrityError:
                    continue
            else:
                SideCuisine3.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-sidecuisine3-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'side_cuisine3',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine4_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('side_cuisine4[]')
        for i in side_cuisines4:
            if str(i.cuisine_id) in check:
                try:
                    side_cuisine4 = SideCuisine4(
                        package=packages, cuisine=i)
                    side_cuisine4.save()
                except IntegrityError:
                    continue
            else:
                SideCuisine4.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-sidecuisine4-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'side_cuisine4',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine5_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('side_cuisine5[]')
        for i in side_cuisines5:
            if str(i.cuisine_id) in check:
                try:
                    side_cuisine5 = SideCuisine5(
                        package=packages, cuisine=i)
                    side_cuisine5.save()
                except IntegrityError:
                    continue
            else:
                SideCuisine5.objects.filter(
                    package_id=_id, cuisine_id=i.cuisine_id).delete()

        return HttpResponseRedirect(reverse('package-sidecuisine5-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'side_cuisine5',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_beverage_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('beverage[]')
        for i in beverages:
            if str(i.equipment_id) in check:
                try:
                    beverage = Beverage(
                        package=packages, equipment=i)
                    beverage.save()
                except IntegrityError:
                    continue
            else:
                Beverage.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-beverage-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'beverage',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_bag_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('equipment[]')
        for i in eqs:
            if str(i.equipment_id) in check:
                try:
                    eq = Bag(
                        package=packages, equipment=i)
                    eq.save()
                except IntegrityError:
                    continue
            else:
                Bag.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-bag-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'bag',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_box_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('box[]')
        for i in box:
            if str(i.equipment_id) in check:
                try:
                    pack = Pack(
                        package=packages, equipment=i)
                    pack.save()
                except IntegrityError:
                    continue
            else:
                Pack.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-box-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'box',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_souvenir_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('souvenirs[]')
        for i in souvenirs:
            if str(i.equipment_id) in check:
                try:
                    souvenir = Souvenir(
                        package=packages, equipment=i)
                    souvenir.save()
                except IntegrityError:
                    continue
            else:
                Souvenir.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-souvenirs-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'souvenir',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_other_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('other[]')
        for i in others:
            if str(i.equipment_id) in check:
                try:
                    other = Other(
                        package=packages, equipment=i)
                    other.save()
                except IntegrityError:
                    continue
            else:
                Other.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-other-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'other',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_addon_view(request, _id):
    packages = Package.objects.get(package_id=_id)
    packages.male_price = '{:,}'.format(packages.male_price)
    packages.female_price = '{:,}'.format(packages.female_price)
    form = FormPackageView(instance=packages)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))

    if request.POST:
        check = request.POST.getlist('addon[]')
        for i in addons:
            if str(i.equipment_id) in check:
                try:
                    addon = Addon(
                        package=packages, equipment=i)
                    addon.save()
                except IntegrityError:
                    continue
            else:
                Addon.objects.filter(
                    package_id=_id, equipment_id=i.equipment_id).delete()

        return HttpResponseRedirect(reverse('package-addon-view', args=[_id, ]))

    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'tab': 'main_cuisine',
        'eq_tab': 'addon',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_maincuisine_update(request, _id, _cuisine):
    cuisine = MainCuisine.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.porsi = request.POST.get('porsi', 0)
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-view', args=[_id, ]))

    return render(request, 'home/package_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_subcuisine_update(request, _id, _cuisine):
    cuisine = SubCuisine.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.porsi = request.POST.get('porsi', 0)
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-subcuisine-view', args=[_id, ]))

    return render(request, 'home/package_subcuisine_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine1_update(request, _id, _cuisine):
    cuisine = SideCuisine1.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-sidecuisine1-view', args=[_id, ]))

    return render(request, 'home/package_sidecuisine1_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine2_update(request, _id, _cuisine):
    cuisine = SideCuisine2.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-sidecuisine2-view', args=[_id, ]))

    return render(request, 'home/package_sidecuisine2_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine3_update(request, _id, _cuisine):
    cuisine = SideCuisine3.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-sidecuisine3-view', args=[_id, ]))

    return render(request, 'home/package_sidecuisine3_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine4_update(request, _id, _cuisine):
    cuisine = SideCuisine4.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-sidecuisine4-view', args=[_id, ]))

    return render(request, 'home/package_sidecuisine4_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine5_update(request, _id, _cuisine):
    cuisine = SideCuisine5.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        cuisine.extra_price = request.POST.get('price')
        cuisine.default = 1 if request.POST.get('default') else 0
        cuisine.save()

        return HttpResponseRedirect(reverse('package-sidecuisine5-view', args=[_id, ]))

    return render(request, 'home/package_sidecuisine5_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_rice_update(request, _id, _cuisine):
    rice = Rice.objects.get(package=_id, cuisine=_cuisine)

    if request.POST:
        rice.extra_price = request.POST.get('price')
        rice.default = 1 if request.POST.get('default') else 0
        rice.save()

        return HttpResponseRedirect(reverse('package-rice-view', args=[_id, ]))

    return render(request, 'home/package_rice_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_beverage_update(request, _id, _eq):
    beverage = Beverage.objects.get(package=_id, equipment=_eq)

    if request.POST:
        beverage.extra_price = request.POST.get('price')
        beverage.default = 1 if request.POST.get('default') else 0
        beverage.save()

        return HttpResponseRedirect(reverse('package-beverage-view', args=[_id, ]))

    return render(request, 'home/package_beverage_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_bag_update(request, _id, _eq):
    bag = Bag.objects.get(package=_id, equipment=_eq)

    if request.POST:
        bag.extra_price = request.POST.get('price')
        bag.default = 1 if request.POST.get('default') else 0
        bag.save()

        return HttpResponseRedirect(reverse('package-bag-view', args=[_id, ]))

    return render(request, 'home/package_bag_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_box_update(request, _id, _eq):
    box = Pack.objects.get(package=_id, equipment=_eq)

    if request.POST:
        box.extra_price = request.POST.get('price')
        box.default = 1 if request.POST.get('default') else 0
        box.save()

        return HttpResponseRedirect(reverse('package-box-view', args=[_id, ]))

    return render(request, 'home/package_box_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_souvenir_update(request, _id, _eq):
    souvenir = Souvenir.objects.get(package=_id, equipment=_eq)

    if request.POST:
        souvenir.extra_price = request.POST.get('price')
        souvenir.default = 1 if request.POST.get('default') else 0
        souvenir.save()

        return HttpResponseRedirect(reverse('package-souvenirs-view', args=[_id, ]))

    return render(request, 'home/package_souvenir_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_other_update(request, _id, _eq):
    other = Other.objects.get(package=_id, equipment=_eq)

    if request.POST:
        other.extra_price = request.POST.get('price')
        other.default = 1 if request.POST.get('default') else 0
        other.save()

        return HttpResponseRedirect(reverse('package-other-view', args=[_id, ]))

    return render(request, 'home/package_other_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_addon_update(request, _id, _eq):
    addon = Addon.objects.get(package=_id, equipment=_eq)

    if request.POST:
        addon.extra_price = request.POST.get('price')
        addon.save()

        return HttpResponseRedirect(reverse('package-addon-view', args=[_id, ]))

    return render(request, 'home/package_addon_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_maincuisine_delete(request, _id, _cuisine):
    MainCuisine.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_subcuisine_delete(request, _id, _cuisine):
    SubCuisine.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-subcuisine-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine1_delete(request, _id, _cuisine):
    SideCuisine1.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-sidecuisine1-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine2_delete(request, _id, _cuisine):
    SideCuisine2.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-sidecuisine2-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine3_delete(request, _id, _cuisine):
    SideCuisine3.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-sidecuisine3-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine4_delete(request, _id, _cuisine):
    SideCuisine4.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-sidecuisine4-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_sidecuisine5_delete(request, _id, _cuisine):
    SideCuisine5.objects.filter(
        package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-sidecuisine5-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_rice_delete(request, _id, _cuisine):
    Rice.objects.filter(package_id=_id, cuisine_id=_cuisine).delete()
    return HttpResponseRedirect(reverse('package-rice-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_beverage_delete(request, _id, _eq):
    Beverage.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-beverage-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_bag_delete(request, _id, _eq):
    Bag.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-bag-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_box_delete(request, _id, _eq):
    Pack.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-box-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_souvenir_delete(request, _id, _eq):
    Souvenir.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-souvenirs-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_other_delete(request, _id, _eq):
    Other.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-other-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_addon_delete(request, _id, _eq):
    Addon.objects.filter(package_id=_id, equipment_id=_eq).delete()
    return HttpResponseRedirect(reverse('package-addon-view', args=[_id, ]))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_update(request, _id):
    packages = Package.objects.get(package_id=_id)
    categories = Category.objects.all()
    goat_types = GoatType.objects.filter(active=True).order_by('display_order', 'goat_type_id')
    dashboards = Dashboard.objects.filter(active=True).order_by('display_order', 'dashboard_id')
    selected_rice = Rice.objects.filter(package_id=_id)
    selected_cuisine = MainCuisine.objects.filter(package_id=_id)
    selected_subcuisine = SubCuisine.objects.filter(package_id=_id)
    selected_sidecuisine1 = SideCuisine1.objects.filter(package_id=_id)
    selected_sidecuisine2 = SideCuisine2.objects.filter(package_id=_id)
    selected_sidecuisine3 = SideCuisine3.objects.filter(package_id=_id)
    selected_sidecuisine4 = SideCuisine4.objects.filter(package_id=_id)
    selected_sidecuisine5 = SideCuisine5.objects.filter(package_id=_id)
    selected_beverage = Beverage.objects.filter(package_id=_id)
    selected_eq = Bag.objects.filter(package_id=_id)
    selected_pack = Pack.objects.filter(package_id=_id)
    selected_souvenirs = Souvenir.objects.filter(package_id=_id)
    selected_other = Other.objects.filter(package_id=_id)
    selected_addon = Addon.objects.filter(package_id=_id)
    rices = Cuisine.objects.all().exclude(
        cuisine_id__in=Rice.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    main_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=MainCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    sub_cuisines = Cuisine.objects.all().exclude(
        cuisine_id__in=SubCuisine.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines1 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine1.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines2 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine2.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines3 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine3.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines4 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine4.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    side_cuisines5 = Cuisine.objects.all().exclude(
        cuisine_id__in=SideCuisine5.objects.filter(package_id=_id).values_list('cuisine_id', flat=True))
    eqs = Equipment.objects.all().exclude(equipment_id__in=Bag.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    box = Equipment.objects.all().exclude(equipment_id__in=Pack.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    addons = Equipment.objects.all().exclude(equipment_id__in=Addon.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    beverages = Equipment.objects.all().exclude(equipment_id__in=Beverage.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    souvenirs = Equipment.objects.all().exclude(equipment_id__in=Souvenir.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    others = Equipment.objects.all().exclude(equipment_id__in=Other.objects.filter(
        package_id=_id).values_list('equipment_id', flat=True))
    if request.POST:
        form = FormPackageUpdate(
            request.POST, request.FILES, instance=packages)
        if form.is_valid():
            update = form.save(commit=False)
            update.category_id = request.POST.get('category')
            update.active = 1 if request.POST.get('active') else 0
            update.promo = 1 if request.POST.get('promo') else 0
            update.type = request.POST.get('type')
            goat_type_id = request.POST.get('goat_type')
            if goat_type_id:
                update.goat_type_id = goat_type_id
            else:
                update.goat_type = None
            goat_type2_id = request.POST.get('goat_type2')
            if goat_type2_id:
                update.goat_type2_id = goat_type2_id
            else:
                update.goat_type2 = None
            dashboard_id = request.POST.get('dashboard')
            if dashboard_id:
                update.dashboard_id = dashboard_id
            else:
                update.dashboard = None
            update.male_price = request.POST.get('male_price')
            update.female_price = request.POST.get('female_price')
            update.save()
            return HttpResponseRedirect(reverse('package-view', args=[_id, ]))
    else:
        form = FormPackageUpdate(instance=packages)

    message = form.errors
    context = {
        'form': form,
        'data': packages,
        'categories': categories,
        'goat_types': goat_types,
        'dashboards': dashboards,
        'selected_rice': selected_rice,
        'selected_cuisine': selected_cuisine,
        'selected_subcuisine': selected_subcuisine,
        'selected_sidecuisine1': selected_sidecuisine1,
        'selected_sidecuisine2': selected_sidecuisine2,
        'selected_sidecuisine3': selected_sidecuisine3,
        'selected_sidecuisine4': selected_sidecuisine4,
        'selected_sidecuisine5': selected_sidecuisine5,
        'selected_beverage': selected_beverage,
        'selected_eq': selected_eq,
        'selected_pack': selected_pack,
        'selected_souvenirs': selected_souvenirs,
        'selected_other': selected_other,
        'selected_addon': selected_addon,
        'rices': rices,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'beverages': beverages,
        'eqs': eqs,
        'box': box,
        'souvenirs': souvenirs,
        'others': others,
        'addons': addons,
        'notif': order_notification(request),
        'segment': 'package',
        'group_segment': 'master',
        'crud': 'update',
        'tab': 'main_cuisine',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/package_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_delete(request, _id):
    packages = Package.objects.get(package_id=_id)

    packages.delete()
    return HttpResponseRedirect(reverse('package-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='PACKAGE')
def package_duplicate(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    original_id = request.POST.get('original_package_id', '').strip()
    new_id = request.POST.get('new_package_id', '').strip()

    if not original_id or not new_id:
        return JsonResponse({'status': 'error', 'message': 'ID Paket tidak boleh kosong'}, status=400)

    if not request.user.is_superuser:
        try:
            auth = Auth.objects.get(user_id=request.user.user_id, menu_id='PACKAGE')
            if not auth.add:
                return JsonResponse({'status': 'error', 'message': 'Anda tidak memiliki akses'}, status=403)
        except Auth.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Anda tidak memiliki akses'}, status=403)

    try:
        original = Package.objects.get(package_id=original_id)
    except Package.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Paket asli tidak ditemukan'}, status=404)

    if Package.objects.filter(package_id=new_id).exists():
        return JsonResponse({'status': 'error', 'message': 'ID Paket baru sudah digunakan'}, status=400)

    now = timezone.now()
    user_id = request.user.user_id

    new_package = Package.objects.create(
        package_id=new_id.upper(),
        package_name=original.package_name,
        category=original.category,
        promo=original.promo,
        active=False,
        male_price=original.male_price,
        female_price=original.female_price,
        box=original.box,
        quantity=original.quantity,
        type=original.type,
        goat_type=original.goat_type,
        goat_type2=original.goat_type2,
        dashboard=original.dashboard,
        entry_date=now,
        entry_by=user_id,
        update_date=now,
        update_by=user_id,
    )

    rice_items = Rice.objects.filter(package=original)
    Rice.objects.bulk_create([
        Rice(
            package=new_package,
            cuisine=r.cuisine,
            extra_price=r.extra_price,
            default=r.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for r in rice_items
    ])

    main_cuisine_items = MainCuisine.objects.filter(package=original)
    MainCuisine.objects.bulk_create([
        MainCuisine(
            package=new_package,
            cuisine=m.cuisine,
            porsi=m.porsi,
            extra_price=m.extra_price,
            default=m.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for m in main_cuisine_items
    ])

    sub_cuisine_items = SubCuisine.objects.filter(package=original)
    SubCuisine.objects.bulk_create([
        SubCuisine(
            package=new_package,
            cuisine=s.cuisine,
            porsi=s.porsi,
            extra_price=s.extra_price,
            default=s.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for s in sub_cuisine_items
    ])

    side_cuisine_models = [SideCuisine1, SideCuisine2, SideCuisine3, SideCuisine4, SideCuisine5]
    for model in side_cuisine_models:
        items = model.objects.filter(package=original)
        model.objects.bulk_create([
            model(
                package=new_package,
                cuisine=item.cuisine,
                extra_price=item.extra_price,
                default=item.default,
                entry_date=now,
                entry_by=user_id,
                update_date=now,
                update_by=user_id,
            ) for item in items
        ])

    bag_items = Bag.objects.filter(package=original)
    Bag.objects.bulk_create([
        Bag(
            package=new_package,
            equipment=b.equipment,
            extra_price=b.extra_price,
            default=b.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for b in bag_items
    ])

    beverage_items = Beverage.objects.filter(package=original)
    Beverage.objects.bulk_create([
        Beverage(
            package=new_package,
            equipment=b.equipment,
            extra_price=b.extra_price,
            default=b.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for b in beverage_items
    ])

    pack_items = Pack.objects.filter(package=original)
    Pack.objects.bulk_create([
        Pack(
            package=new_package,
            equipment=p.equipment,
            extra_price=p.extra_price,
            default=p.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for p in pack_items
    ])

    souvenir_items = Souvenir.objects.filter(package=original)
    Souvenir.objects.bulk_create([
        Souvenir(
            package=new_package,
            equipment=s.equipment,
            extra_price=s.extra_price,
            default=s.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for s in souvenir_items
    ])

    other_items = Other.objects.filter(package=original)
    Other.objects.bulk_create([
        Other(
            package=new_package,
            equipment=o.equipment,
            extra_price=o.extra_price,
            default=o.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for o in other_items
    ])

    addon_items = Addon.objects.filter(package=original)
    Addon.objects.bulk_create([
        Addon(
            package=new_package,
            equipment=a.equipment,
            extra_price=a.extra_price,
            default=a.default,
            entry_date=now,
            entry_by=user_id,
            update_date=now,
            update_by=user_id,
        ) for a in addon_items
    ])

    return JsonResponse({
        'status': 'success',
        'message': f'Paket berhasil diduplikasi sebagai {new_package.package_id}',
        'redirect': reverse('package-view', args=[new_package.package_id])
    })


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_index(request):
    regions = Region.objects.all()

    context = {
        'data': regions,
        'notif': order_notification(request),
        'segment': 'region',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='REGION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/region_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_add(request):
    if request.POST:
        form = FormRegion(request.POST)
        if form.is_valid():
            region = form.save(commit=False)
            region.region_id = form.cleaned_data['region_id'].replace(' ', '')
            region.save()

            return HttpResponseRedirect(reverse('region-view', args=[region.region_id]))
    else:
        form = FormRegion()

    message = form.errors
    context = {
        'form': form,
        'notif': order_notification(request),
        'segment': 'region',
        'group_segment': 'master',
        'crud': 'add',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='REGION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/region_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_view(request, _id):
    region = Region.objects.get(region_id=_id)
    form = FormRegionView(instance=region)
    details = RegionDetail.objects.filter(region_id=_id)
    areas = AreaSales.objects.exclude(regiondetail__region_id=_id).values_list(
        'area_id', 'area_name', 'regiondetail__region_id')

    if request.POST:
        check = request.POST.getlist('checks[]')
        for area in areas:
            if str(area[0]) in check:
                try:
                    detail = RegionDetail(region_id=_id, area_id=area[0])
                    detail.save()
                except IntegrityError:
                    continue
            else:
                RegionDetail.objects.filter(
                    region_id=_id, area_id=area[0]).delete()

    context = {
        'form': form,
        'data': region,
        'areas': areas,
        'detail': details,
        'notif': order_notification(request),
        'segment': 'region',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='REGION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/region_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_update(request, _id):
    region = Region.objects.get(region_id=_id)
    detail = RegionDetail.objects.filter(region_id=_id)

    if request.POST:
        form = FormRegionUpdate(request.POST, instance=region)
        if form.is_valid():
            region = form.save(commit=False)
            region.save()

            return HttpResponseRedirect(reverse('region-view', args=[_id]))
    else:
        form = FormRegionUpdate(instance=region)

    message = form.errors
    context = {
        'form': form,
        'data': region,
        'detail': detail,
        'notif': order_notification(request),
        'segment': 'region',
        'group_segment': 'master',
        'crud': 'update',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='REGION') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/region_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_delete(request, _id):
    region = Region.objects.get(region_id=_id)
    region.delete()

    return HttpResponseRedirect(reverse('region-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='REGION')
def region_detail_delete(request, _id, _area):
    detail = RegionDetail.objects.get(region_id=_id, area_id=_area)
    detail.delete()

    return HttpResponseRedirect(reverse('region-view', args=[_id]))


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_index(request):
    customers = Customer.objects.all()

    context = {
        'data': customers,
        'notif': order_notification(request),
        'segment': 'customer',
        'group_segment': 'master',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CUSTOMER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/customer_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_add(request):
    if request.POST:
        form = FormCustomer(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.save()

            return HttpResponseRedirect(reverse('customer-view', args=[customer.customer_id, '0']))
    else:
        form = FormCustomer()

    message = form.errors
    context = {
        'form': form,
        'notif': order_notification(request),
        'segment': 'customer',
        'group_segment': 'master',
        'crud': 'add',
        'message': message,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='CUSTOMER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/customer_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_view(request, _id, _msg):
    customer = Customer.objects.get(customer_id=_id)
    form = FormCustomerView(instance=customer)
    form_detail = FormCustomerDetail(
        initial={'child_birth': datetime.date.today()})
    details = CustomerDetail.objects.filter(customer_id=_id)
    msg = _msg

    if request.POST:
        form_detail = FormCustomerDetail(request.POST)
        if form_detail.is_valid():
            try:
                detail = form_detail.save(commit=False)
                detail.customer_id = _id
                detail.child_sex = request.POST.get('child_sex')
                detail.save()
            except IntegrityError:
                msg = 'Nama anak sudah ada.'

            return HttpResponseRedirect(reverse('customer-view', args=[_id, msg]))

    context = {
        'form': form,
        'form_detail': form_detail,
        'data': customer,
        'details': details,
        'msg': msg,
        'notif': order_notification(request),
        'segment': 'customer',
        'group_segment': 'master',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='CUSTOMER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/customer_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_update(request, _id):
    customer = Customer.objects.get(customer_id=_id)

    if request.POST:
        form = FormCustomerUpdate(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.save()

            return HttpResponseRedirect(reverse('customer-view', args=[_id, '0']))
    else:
        form = FormCustomerUpdate(instance=customer)

    context = {
        'form': form,
        'data': customer,
        'msg': '0',
        'notif': order_notification(request),
        'segment': 'customer',
        'group_segment': 'master',
        'crud': 'update',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list(
            'menu_id', flat=True),
        'btn': Auth.objects.get(
            user_id=request.user.user_id, menu_id='CUSTOMER') if not request.user.is_superuser else Auth.objects.all(),
    }
    return render(request, 'home/customer_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_delete(request, _id):
    customer = Customer.objects.get(customer_id=_id)
    customer.delete()

    return HttpResponseRedirect(reverse('customer-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_detail_update(request, _id, _child):
    detail = CustomerDetail.objects.get(id=_child)

    if request.POST:
        detail.child_name = request.POST.get('child_name')
        detail.child_birth = request.POST.get('child_birth')
        detail.child_sex = request.POST.get('child_sex')
        detail.child_father = request.POST.get('child_father')
        detail.child_mother = request.POST.get('child_mother')
        detail.save()

        return HttpResponseRedirect(reverse('customer-view', args=[_id, '0']))

    return render(request, 'home/customer_view.html')


@login_required(login_url='/login/')
@role_required(allowed_roles='CUSTOMER')
def customer_detail_delete(request, _id):
    detail = CustomerDetail.objects.get(id=_id)
    detail.delete()

    return HttpResponseRedirect(reverse('customer-view', args=[_id, '0']))


def order_add(request, _reg):
    num = _reg.split('/')[1] if '/' in _reg else '0'

    if num == '0':
        try:
            _no = Order.objects.filter(
                order_date__year=datetime.datetime.now().year).latest('seq_number')
        except Order.DoesNotExist:
            _no = None

        if _no is None:
            format_no = '{:05d}'.format(1)
            num = 1
        else:
            format_no = '{:05d}'.format(_no.seq_number + 1)
            _no.seq_number += 1
            _no.save()
            num = _no.seq_number

        _id = 'INV-1' + format_no + '/' + _reg.upper() + '/SA/' + str(datetime.datetime.now().strftime('%m')) + \
            '/' + str(datetime.datetime.now().year)

    if request.POST:
        form = FormOrder(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.regional_id = _reg.split('/')[0]
            order.seq_number = num
            order.save()

            return HttpResponseRedirect(reverse('order-child-add', args=[order.order_id, 0]))
    else:
        form = FormOrder(initial={'order_id': _id})

    msg = form.errors
    context = {
        'form': form,
        'crud': 'add',
        'reg': _reg+'/'+str(num),
        'msg': msg,
    }
    return render(request, 'home/order_add.html', context)


def order_update(request, _id):
    order = Order.objects.get(order_id=_id)

    if request.POST:
        form = FormOrderUpdate(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            order.save()

            child = OrderChild.objects.filter(order_id=_id)
            if child:
                return HttpResponseRedirect(reverse('order-child-update', args=[_id, child.first().id, 0]))
            else:
                return HttpResponseRedirect(reverse('order-child-add', args=[_id, 0]))
    else:
        form = FormOrderUpdate(instance=order)

    msg = form.errors

    context = {
        'form': form,
        'data': order,
        'msg': msg,
        'crud': 'update',
    }
    return render(request, 'home/order_update.html', context)


def order_child_add(request, _id, _add):
    try:
        last_child = OrderChild.objects.filter(order_id=_id).last()
    except OrderChild.DoesNotExist:
        last_child = None

    if request.POST:
        form = FormOrderChild(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.order_id = _id
            child.child_sex = request.POST.get('child_sex')
            child.save()

            package = OrderPackage.objects.filter(order_id=_id)
            if _add == 1:
                return HttpResponseRedirect(reverse('order-child-add', args=[_id, 0]))
            else:
                if package:
                    return HttpResponseRedirect(reverse('order-package-update', args=[_id, package[0].id, package[0].category_id, package[0].package_id, package[0].type, 0]))
                else:
                    return HttpResponseRedirect(reverse('order-package-add', args=[_id, '0', '0', '0', 0]))
    else:
        form = FormOrderChild(initial={'order': _id})

    msg = form.errors
    context = {
        'form': form,
        'crud': 'add',
        'last_child': last_child,
        'order_id': _id,
        'msg': msg,
    }
    return render(request, 'home/order_child_add.html', context)


def order_cs_child_add(request, _id):
    if request.POST:
        child_birth_error = _validate_child_birth_not_future(
            request.POST.get('child_birth')
        )
        if child_birth_error:
            return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))

        _child = OrderChild.objects.get(order_id=_id, child_name=request.POST.get('child_name')) if OrderChild.objects.filter(
            order_id=_id, child_name=request.POST.get('child_name')) else None
        if not _child:
            child = OrderChild(
                order_id=_id,
                child_name=request.POST.get('child_name'),
                child_birth=request.POST.get('child_birth'),
                child_sex=request.POST.get('child_sex'),
                child_father=request.POST.get('child_father'),
                child_mother=request.POST.get('child_mother'),
            )
            child.save()

            customer = Customer.objects.get(customer_phone=child.order.customer_phone) if Customer.objects.filter(
                customer_phone=child.order.customer_phone) else None
            if not customer:
                new_customer = Customer(
                    customer_phone=child.order.customer_phone,
                    customer_name=child.order.customer_name,
                    customer_phone2=child.order.customer_phone2,
                    customer_address=child.order.customer_address,
                    customer_email=child.order.customer_email,
                    customer_district=child.order.customer_district,
                    customer_city=child.order.customer_city,
                    customer_province=child.order.customer_province,
                )
                new_customer.save()

                children = OrderChild.objects.filter(order_id=_id)
                for i in children:
                    new_child = CustomerDetail(
                        customer_id=new_customer.customer_id,
                        child_name=i.child_name,
                        child_birth=i.child_birth,
                        child_sex=i.child_sex,
                        child_father=i.child_father,
                        child_mother=i.child_mother,
                    )
                    new_child.save()
            else:
                _child = CustomerDetail.objects.get(customer_id=customer.customer_id, child_name=child.child_name) if CustomerDetail.objects.filter(
                    customer_id=customer.customer_id, child_name=child.child_name) else None
                if not _child:
                    new_child = CustomerDetail(
                        customer_id=customer.customer_id,
                        child_name=request.POST.get('child_name'),
                        child_birth=request.POST.get('child_birth'),
                        child_sex=request.POST.get('child_sex'),
                        child_father=request.POST.get('child_father'),
                        child_mother=request.POST.get('child_mother'),
                    )
                    new_child.save()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def order_child_update(request, _id, _child, _add):
    child = OrderChild.objects.get(order_id=_id, id=_child)
    children = OrderChild.objects.filter(order_id=_id).order_by('id')

    first = False
    prev_id = 0

    first_child = OrderChild.objects.filter(order_id=_id).first()
    if first_child.id == _child:
        first = True

    for index, i in enumerate(children):
        if i.id == _child:
            n_child = index + 1

    for i in reversed(children):
        if i.id < _child:
            prev_id = i.id
            break

    if request.POST:
        form = FormOrderChildUpdate(request.POST, instance=child)
        if form.is_valid():
            child = form.save(commit=False)
            child.child_sex = request.POST.get('child_sex')
            child.save()

            last_child = OrderChild.objects.filter(order_id=_id).last()
            if _add == 1:
                return HttpResponseRedirect(reverse('order-child-add', args=[_id, 0]))
            else:
                if last_child.id == _child:
                    package = OrderPackage.objects.filter(order_id=_id)
                    if package:
                        return HttpResponseRedirect(reverse('order-package-update', args=[_id, package[0].id, package[0].category_id, package[0].package_id, package[0].type, 0]))
                    else:
                        return HttpResponseRedirect(reverse('order-package-add', args=[_id, '0', '0', '0', 0]))
                else:
                    for i in OrderChild.objects.filter(order_id=_id):
                        if i.id > _child:
                            return HttpResponseRedirect(reverse('order-child-update', args=[_id, i.id, 0]))
    else:
        form = FormOrderChildUpdate(instance=child)

    context = {
        'form': form,
        'data': child,
        'first_child': first,
        'n_child': n_child,
        'children': children,
        'prev_id': prev_id,
        'crud': 'update',
    }
    return render(request, 'home/order_child_update.html', context)


def order_child_cs_update(request, _id, _child):
    child = OrderChild.objects.get(order_id=_id, id=_child)

    if request.POST:
        child_birth_error = _validate_child_birth_not_future(
            request.POST.get('child_birth')
        )
        if child_birth_error:
            return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))

        child.child_name = request.POST.get('child_name')
        child.child_birth = request.POST.get('child_birth')
        child.child_sex = request.POST.get('child_sex')
        child.child_father = request.POST.get('child_father')
        child.child_mother = request.POST.get('child_mother')
        child.save()

        customer = Customer.objects.get(
            customer_phone=child.order.customer_phone) if Customer.objects.filter(customer_phone=child.order.customer_phone) else None
        if customer:
            detail = CustomerDetail.objects.get(customer_id=customer.customer_id, child_name=child.child_name) if CustomerDetail.objects.filter(
                customer_id=customer.customer_id, child_name=child.child_name) else None
            if detail:
                detail.child_birth = request.POST.get('child_birth')
                detail.child_name = request.POST.get('child_name')
                detail.child_sex = request.POST.get('child_sex')
                detail.child_father = request.POST.get('child_father')
                detail.child_mother = request.POST.get('child_mother')
                detail.save()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def order_child_delete(request, _id, _child):
    child = OrderChild.objects.get(order_id=_id, id=_child)
    child.delete()

    first = OrderChild.objects.filter(order_id=_id).first()

    return HttpResponseRedirect(reverse('order-child-update', args=[_id, first.id, 0]))


def order_child_cs_delete(request, _id, _child):
    child = OrderChild.objects.get(order_id=_id, id=_child)
    child.delete()

    customer = Customer.objects.get(customer_phone=child.order.customer_phone) if Customer.objects.filter(
        customer_phone=child.order.customer_phone) else None
    if customer:
        detail = CustomerDetail.objects.get(customer_id=customer.customer_id, child_name=child.child_name) if CustomerDetail.objects.filter(
            customer_id=customer.customer_id, child_name=child.child_name) else None
        if detail:
            detail.delete()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def order_package_add(request, _id, _cat, _pack, _type, _add):
    categories = Category.objects.filter(active=True)
    packages = Package.objects.filter(category=_cat, active=True).exclude(package_id__in=OrderPackage.objects.filter(
        order_id=_id).values_list('package_id', flat=True)) if _cat != '0' else None
    box_types = Pack.objects.filter(package=_pack) if _pack != '0' else None
    main_cuisines = MainCuisine.objects.filter(package=_pack)
    sub_cuisines = SubCuisine.objects.filter(package=_pack)
    side_cuisines1 = SideCuisine1.objects.filter(package=_pack)
    side_cuisines2 = SideCuisine2.objects.filter(package=_pack)
    side_cuisines3 = SideCuisine3.objects.filter(package=_pack)
    side_cuisines4 = SideCuisine4.objects.filter(package=_pack)
    side_cuisines5 = SideCuisine5.objects.filter(package=_pack)
    rices = Rice.objects.filter(package=_pack)
    bags = Bag.objects.filter(package=_pack)
    beverages = Beverage.objects.filter(
        package=_pack) if _pack != '0' else None
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_addon.equipment_id, equipment_name, extra_price, q_addon.equipment_id, q_addon.quantity FROM apps_equipment INNER JOIN apps_addon ON apps_equipment.equipment_id = apps_addon.equipment_id LEFT JOIN (SELECT * FROM apps_orderpackageaddon WHERE order_id = '" + str(_id) + "' AND package_id = '" + str(_pack) + "') AS q_addon ON apps_addon.equipment_id = q_addon.equipment_id WHERE apps_addon.package_id = '" + str(_pack) + "' ORDER BY equipment_name")
        addons = cursor.fetchall()
    souvenirs = Souvenir.objects.filter(
        package_id=_pack) if _pack != '0' else None
    last_package = OrderPackage.objects.filter(order_id=_id).last(
    ) if OrderPackage.objects.filter(order_id=_id) else None
    selected_package = Package.objects.get(
        package_id=_pack) if _pack != '0' else None
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id).last()
    addon_order = ''
    souvenir_order = ''

    if request.POST:
        form = FormOrderPackage(request.POST)
        up = []

        if form.is_valid():
            extra_price_main = MainCuisine.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('main_cuisine')).cuisine_id).extra_price if request.POST.get('main_cuisine') else 0
            up.append(request.POST.get('main_cuisine')
                      ) if extra_price_main > 0 else ''
            extra_price_sub = SubCuisine.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('sub_cuisine')).cuisine_id).extra_price if request.POST.get('sub_cuisine') else 0
            up.append(request.POST.get('sub_cuisine')
                      ) if extra_price_sub > 0 else ''
            extra_price_side1 = SideCuisine1.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine1')).cuisine_id).extra_price if request.POST.get('side_cuisine1') else 0
            up.append(request.POST.get('side_cuisine1')
                      ) if extra_price_side1 > 0 else ''
            extra_price_side2 = SideCuisine2.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine2')).cuisine_id).extra_price if request.POST.get('side_cuisine2') else 0
            up.append(request.POST.get('side_cuisine2')
                      ) if extra_price_side2 > 0 else ''
            extra_price_side3 = SideCuisine3.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine3')).cuisine_id).extra_price if request.POST.get('side_cuisine3') else 0
            up.append(request.POST.get('side_cuisine3')
                      ) if extra_price_side3 > 0 else ''
            extra_price_side4 = SideCuisine4.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine4')).cuisine_id).extra_price if request.POST.get('side_cuisine4') else 0
            up.append(request.POST.get('side_cuisine4')
                      ) if extra_price_side4 > 0 else ''
            extra_price_side5 = SideCuisine5.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine5')).cuisine_id).extra_price if request.POST.get('side_cuisine5') else 0
            up.append(request.POST.get('side_cuisine5')
                      ) if extra_price_side5 > 0 else ''
            extra_price_rice = Rice.objects.get(package=_pack, cuisine=Cuisine.objects.get(
                cuisine_name=request.POST.get('rice')).cuisine_id).extra_price if request.POST.get('rice') else 0
            up.append(request.POST.get('rice')) if extra_price_rice > 0 else ''
            extra_price_bag = Bag.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('bag')).equipment_id).extra_price if request.POST.get('bag') else 0
            up.append(request.POST.get('bag')) if extra_price_bag > 0 else ''
            extra_price_box = Pack.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('box_type')).equipment_id).extra_price if request.POST.get('box_type') else 0
            up.append(request.POST.get('box_type')
                      ) if extra_price_box > 0 else ''
            extra_price_beverage = Beverage.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('beverage')).equipment_id).extra_price if request.POST.get('beverage') else 0
            up.append(request.POST.get('beverage')
                      ) if extra_price_beverage > 0 else ''

            package = form.save(commit=False)

            package.order_id = _id
            package.category_id = _cat
            package.package_id = _pack
            package.type = _type
            package.quantity = request.POST.get('quantity')
            package.box_qty = int(request.POST.get('box')) if request.POST.get('box') else 0
            package.box_type = request.POST.get('box_type')
            package.main_cuisine = request.POST.get('main_cuisine')
            package.main_cuisine_price = extra_price_main
            package.sub_cuisine = request.POST.get('sub_cuisine')
            package.side_cuisine1 = request.POST.get('side_cuisine1')
            package.side_cuisine2 = request.POST.get('side_cuisine2')
            package.side_cuisine3 = request.POST.get('side_cuisine3')
            package.side_cuisine4 = request.POST.get('side_cuisine4')
            package.side_cuisine5 = request.POST.get('side_cuisine5')
            package.rice = request.POST.get('rice')
            package.bag = request.POST.get('bag')
            package.souvenir = request.POST.get('souvenir')
            package.beverage = request.POST.get('beverages')
            package.unit_price = selected_package.male_price if _type == 'Jantan' else selected_package.female_price
            package.extra_price = ((extra_price_sub + extra_price_side1 + extra_price_side2 +
                                   extra_price_side3 + extra_price_side4 + extra_price_side5 + extra_price_rice + extra_price_bag + extra_price_box + extra_price_beverage) * ((selected_package.box if selected_package.box > 0 else 0) * int(request.POST.get('quantity')))) + (extra_price_main * int(request.POST.get('quantity')))
            package.upgrade = ', '.join(up)
            package.save()

            total = OrderPackage.objects.filter(
                order_id=_id).aggregate(order=Sum('total_price'))
            total_addon = OrderPackageAddon.objects.filter(
                order_id=_id).aggregate(order=Sum('total_price'))
            _total_addon = total_addon['order'] if total_addon['order'] else 0
            order.total_order = total['order'] + \
                _total_addon - order.promo_nominal
            order.save()

            if _add == 2:
                check = request.GET.get('checks')
                qty = request.GET.get('qty')
                _ids = check.split(',')
                _qty = qty.split(',')
                _qty_idx = 0
                for index, i in enumerate(addons):
                    if str(i[0]) in _ids:
                        try:
                            _addon = OrderPackageAddon(
                                order_id=_id, package_id=_pack, equipment_id=i[0], unit_price=i[2])
                            _addon.save()
                            _update = OrderPackageAddon.objects.get(
                                order_id=_id, package_id=_pack, equipment_id=i[0])
                            _update.quantity = int(_qty[_qty_idx])
                            _update.save()
                        except IntegrityError:
                            _update = OrderPackageAddon.objects.get(
                                order_id=_id, package_id=_pack, equipment_id=i[0])
                            _update.quantity = int(_qty[_qty_idx])
                            _update.save()
                            continue

                        _qty_idx += 1

                    else:
                        OrderPackageAddon.objects.filter(
                            order_id=_id, package_id=_pack, equipment_id=i[0]).delete()

                _addon_order = OrderPackageAddon.objects.filter(
                    order_id=_id, package_id=_pack)
                for idx, j in enumerate(_addon_order):
                    addon_order += j.equipment.equipment_name + \
                        ' (' + str(j.quantity) + ')'
                    if idx < _addon_order.count() - 1:
                        addon_order += ', '

                return HttpResponseRedirect(reverse('order-package-update', args=[_id, package.id, _cat, _pack, _type, 0]))
            else:
                if _add == 3:
                    check = request.GET.get('checks')
                    qty = request.GET.get('qty')
                    _ids = check.split(',')
                    _qty = qty.split(',')
                    _qty_idx = 0
                    for index, i in enumerate(souvenirs):
                        if str(i[0]) in _ids:
                            try:
                                _souvenir = OrderPackageSouvenir(
                                    order_id=_id, package_id=_pack, equipment_id=i[0], unit_price=i[2])
                                _souvenir.save()
                                _update = OrderPackageSouvenir.objects.get(
                                    order_id=_id, package_id=_pack, equipment_id=i[0])
                                _update.quantity = int(_qty[_qty_idx])
                                _update.save()
                            except IntegrityError:
                                _update = OrderPackageSouvenir.objects.get(
                                    order_id=_id, package_id=_pack, equipment_id=i[0])
                                _update.quantity = int(_qty[_qty_idx])
                                _update.save()
                                continue

                            _qty_idx += 1

                        else:
                            OrderPackageSouvenir.objects.filter(
                                order_id=_id, package_id=_pack, equipment_id=i[0]).delete()

                    _souvenir_order = OrderPackageSouvenir.objects.filter(
                        order_id=_id, package_id=_pack)
                    for idx, j in enumerate(_souvenir_order):
                        souvenir_order += j.equipment.equipment_name
                        if idx < _souvenir_order.count() - 1:
                            souvenir_order += ', '

                    return HttpResponseRedirect(reverse('order-package-update', args=[_id, package.id, _cat, _pack, _type, 0]))
                else:
                    if _add == 1:
                        return HttpResponseRedirect(reverse('order-package-add', args=[_id, '0', '0', '0', 0]))
                    else:
                        return HttpResponseRedirect(reverse('order-confirm-update', args=[_id]))
    else:
        form = FormOrderPackage(initial={'order': _id})

    msg = form.errors
    context = {
        'form': form,
        'data': order,
        'crud': 'add',
        'cat': _cat,
        'pack': _pack,
        'type': _type,
        'categories': categories,
        'packages': packages,
        'box_types': box_types,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'rices': rices,
        'bags': bags,
        'beverages': beverages,
        'addons': addons,
        'addon_order': addon_order,
        'souvenirs': souvenirs,
        'souvenir_order': souvenir_order,
        'last_package': last_package,
        'selected_package': selected_package,
        'order_id': _id,
        'child': child,
        'msg': msg,
    }
    return render(request, 'home/order_package_add.html', context)


def order_cs_package_add(request, _id, _cat, _pack, _type):
    package = Package.objects.get(package_id=_pack)
    if request.POST:
        up = []

        extra_price_main = MainCuisine.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('main_cuisine')).cuisine_id).extra_price if request.POST.get('main_cuisine') else 0
        up.append(request.POST.get('main_cuisine')
                  ) if extra_price_main > 0 else ''
        extra_price_sub = SubCuisine.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('sub_cuisine')).cuisine_id).extra_price if request.POST.get('sub_cuisine') else 0
        up.append(request.POST.get('sub_cuisine')
                  ) if extra_price_sub > 0 else ''
        extra_price_side1 = SideCuisine1.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine1')).cuisine_id).extra_price if request.POST.get('side_cuisine1') else 0
        up.append(request.POST.get('side_cuisine1')
                  ) if extra_price_side1 > 0 else ''
        extra_price_side2 = SideCuisine2.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine2')).cuisine_id).extra_price if request.POST.get('side_cuisine2') else 0
        up.append(request.POST.get('side_cuisine2')
                  ) if extra_price_side2 > 0 else ''
        extra_price_side3 = SideCuisine3.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine3')).cuisine_id).extra_price if request.POST.get('side_cuisine3') else 0
        up.append(request.POST.get('side_cuisine3')
                  ) if extra_price_side3 > 0 else ''
        extra_price_side4 = SideCuisine4.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine4')).cuisine_id).extra_price if request.POST.get('side_cuisine4') else 0
        up.append(request.POST.get('side_cuisine4')
                  ) if extra_price_side4 > 0 else ''
        extra_price_side5 = SideCuisine5.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine5')).cuisine_id).extra_price if request.POST.get('side_cuisine5') else 0
        up.append(request.POST.get('side_cuisine5')
                  ) if extra_price_side5 > 0 else ''
        extra_price_rice = Rice.objects.get(package=_pack, cuisine=Cuisine.objects.get(
            cuisine_name=request.POST.get('rice')).cuisine_id).extra_price if request.POST.get('rice') else 0
        up.append(request.POST.get('rice')) if extra_price_rice > 0 else ''
        extra_price_bag = Bag.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('bag')).equipment_id).extra_price if request.POST.get('bag') else 0
        up.append(request.POST.get('bag')) if extra_price_bag > 0 else ''
        extra_price_box = Pack.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('box_type')).equipment_id).extra_price if request.POST.get('box_type') else 0
        up.append(request.POST.get('box_type')) if extra_price_box > 0 else ''
        extra_price_beverage = Beverage.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('beverage')).equipment_id).extra_price if request.POST.get('beverage') else 0
        up.append(request.POST.get('beverage')
                  ) if extra_price_beverage > 0 else ''

        package = OrderPackage(
            order_id=_id,
            category_id=_cat,
            package_id=_pack,
            type=_type,
            quantity=int(request.POST.get('quantity')),
            box_qty=package.box,
            box_type=request.POST.get('box_type'),
            main_cuisine=request.POST.get('main_cuisine') +
            ' (+ Rp ' + str('{:,}'.format(extra_price_main)).replace(',', '.') +
            ')' if extra_price_main > 0 else request.POST.get(
                'main_cuisine'),
            sub_cuisine=request.POST.get('sub_cuisine'),
            side_cuisine1=request.POST.get('side_cuisine1'),
            side_cuisine2=request.POST.get('side_cuisine2'),
            side_cuisine3=request.POST.get('side_cuisine3'),
            side_cuisine4=request.POST.get('side_cuisine4'),
            side_cuisine5=request.POST.get('side_cuisine5'),
            rice=request.POST.get('rice'),
            bag=request.POST.get('bag'),
            souvenir=request.POST.get('souvenir'),
            beverage=request.POST.get('beverage'),
            unit_price=package.male_price if _type == 'Jantan' else package.female_price,
            extra_price=((extra_price_sub + extra_price_side1 + extra_price_side2 +
                         extra_price_side3 + extra_price_side4 + extra_price_side5 + extra_price_rice + extra_price_bag + extra_price_box + extra_price_beverage) * ((Package.objects.get(package_id=_pack).box if Package.objects.get(package_id=_pack).box > 0 else 1) * int(request.POST.get('quantity')))) + (extra_price_main * int(request.POST.get('quantity'))),
            upgrade=', '.join(up)
        )
        package.save()

        total = OrderPackage.objects.filter(
            order_id=_id).aggregate(order=Sum('total_price'))
        total_addon = OrderPackageAddon.objects.filter(
            order_id=_id).aggregate(order=Sum('total_price'))
        _total_addon = total_addon['order'] if total_addon['order'] else 0
        order = Order.objects.get(order_id=_id)
        order.total_order = total['order'] + _total_addon - order.promo_nominal
        order.save()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def order_package_update(request, _id, _package, _cat, _pack, _type, _add):
    categories = Category.objects.filter(active=True)
    packages = Package.objects.filter(category=_cat, active=True).exclude(package_id__in=OrderPackage.objects.filter(
        order_id=_id).values_list('package_id', flat=True).exclude(package_id=_pack)) if _cat != '0' else None
    package = OrderPackage.objects.get(order_id=_id, id=_package)
    box_types = Pack.objects.filter(package=_pack) if _pack != '0' else None
    main_cuisines = MainCuisine.objects.filter(package=_pack)
    sub_cuisines = SubCuisine.objects.filter(package=_pack)
    side_cuisines1 = SideCuisine1.objects.filter(package=_pack)
    side_cuisines2 = SideCuisine2.objects.filter(package=_pack)
    side_cuisines3 = SideCuisine3.objects.filter(package=_pack)
    side_cuisines4 = SideCuisine4.objects.filter(package=_pack)
    side_cuisines5 = SideCuisine5.objects.filter(package=_pack)
    rices = Rice.objects.filter(package=_pack)
    bags = Bag.objects.filter(package=_pack)
    beverages = Beverage.objects.filter(
        package=_pack) if _pack != '0' else None
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_addon.equipment_id, equipment_name, extra_price, q_addon.equipment_id, q_addon.quantity FROM apps_equipment INNER JOIN apps_addon ON apps_equipment.equipment_id = apps_addon.equipment_id LEFT JOIN (SELECT * FROM apps_orderpackageaddon WHERE order_id = '" + str(_id) + "' AND package_id = '" + str(_pack) + "') AS q_addon ON apps_addon.equipment_id = q_addon.equipment_id WHERE apps_addon.package_id = '" + str(_pack) + "' ORDER BY equipment_name")
        addons = cursor.fetchall()
    souvenirs = Souvenir.objects.filter(
        package_id=_pack) if _pack != '0' else None
    last_child = OrderChild.objects.filter(order_id=_id).last()
    selected_package = Package.objects.get(
        package_id=_pack) if _pack != '0' else None
    order = Order.objects.get(order_id=_id)
    orders = OrderPackage.objects.filter(order_id=_id)
    addon_order = ''
    souvenir_order = ''

    first = False
    prev_id = 0
    prev_cat = 0
    prev_pack = 0
    prev_type = 0

    first_package = OrderPackage.objects.filter(order_id=_id).first()
    if first_package.id == _package:
        first = True

    for index, i in enumerate(OrderPackage.objects.filter(order_id=_id)):
        if i.id == _package:
            n_package = index + 1

    for i in reversed(OrderPackage.objects.filter(order_id=_id)):
        if i.id < _package:
            prev_id = i.id
            prev_cat = i.category_id
            prev_pack = i.package_id
            prev_type = i.type
            break

    _addon_order = OrderPackageAddon.objects.filter(
        order_id=_id, package_id=_pack)
    for idx, j in enumerate(_addon_order):
        addon_order += j.equipment.equipment_name + \
            ' (' + str(j.quantity) + ')'
        if idx < _addon_order.count() - 1:
            addon_order += ', '

    _souvenir_order = OrderPackageSouvenir.objects.filter(
        order_id=_id, package_id=_pack)
    for idx, j in enumerate(_souvenir_order):
        souvenir_order += j.equipment.equipment_name
        if idx < _souvenir_order.count() - 1:
            souvenir_order += ', '

    if request.POST:
        form = FormOrderPackage(request.POST, instance=package)
        up = []

        if form.is_valid():
            extra_price_main = MainCuisine.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('main_cuisine')).cuisine_id).extra_price if request.POST.get('main_cuisine') else 0
            up.append(request.POST.get('main_cuisine')
                      ) if extra_price_main > 0 else ''
            extra_price_sub = SubCuisine.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('sub_cuisine')).cuisine_id).extra_price if request.POST.get('sub_cuisine') else 0
            up.append(request.POST.get('sub_cuisine')
                      ) if extra_price_sub > 0 else ''
            extra_price_side1 = SideCuisine1.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine1')).cuisine_id).extra_price if request.POST.get('side_cuisine1') else 0
            up.append(request.POST.get('side_cuisine1')
                      ) if extra_price_side1 > 0 else ''
            extra_price_side2 = SideCuisine2.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine2')).cuisine_id).extra_price if request.POST.get('side_cuisine2') else 0
            up.append(request.POST.get('side_cuisine2')
                      ) if extra_price_side2 > 0 else ''
            extra_price_side3 = SideCuisine3.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine3')).cuisine_id).extra_price if request.POST.get('side_cuisine3') else 0
            up.append(request.POST.get('side_cuisine3')
                      ) if extra_price_side3 > 0 else ''
            extra_price_side4 = SideCuisine4.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine4')).cuisine_id).extra_price if request.POST.get('side_cuisine4') else 0
            up.append(request.POST.get('side_cuisine4')
                      ) if extra_price_side4 > 0 else ''
            extra_price_side5 = SideCuisine5.objects.get(
                package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine5')).cuisine_id).extra_price if request.POST.get('side_cuisine5') else 0
            up.append(request.POST.get('side_cuisine5')
                      ) if extra_price_side5 > 0 else ''
            extra_price_rice = Rice.objects.get(package=_pack, cuisine=Cuisine.objects.get(
                cuisine_name=request.POST.get('rice')).cuisine_id).extra_price if request.POST.get('rice') else 0
            up.append(request.POST.get('rice')) if extra_price_rice > 0 else ''
            extra_price_bag = Bag.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('bag')).equipment_id).extra_price if request.POST.get('bag') else 0
            up.append(request.POST.get('bag')) if extra_price_bag > 0 else ''
            extra_price_box = Pack.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('box_type')).equipment_id).extra_price if request.POST.get('box_type') else 0
            up.append(request.POST.get('box_type')
                      ) if extra_price_box > 0 else ''
            extra_price_beverage = Beverage.objects.get(package=_pack, equipment=Equipment.objects.get(
                equipment_name=request.POST.get('beverages')).equipment_id).extra_price if request.POST.get('beverages') else 0
            up.append(request.POST.get('beverages')
                      ) if extra_price_beverage > 0 else ''

            package = form.save(commit=False)

            package.category_id = _cat
            package.package_id = _pack
            package.type = _type
            package.quantity = request.POST.get('quantity')
            package.box_qty = int(request.POST.get('box')) if request.POST.get('box') else 0
            package.box_type = request.POST.get('box_type')
            package.main_cuisine = request.POST.get('main_cuisine')
            package.main_cuisine_price = extra_price_main
            package.sub_cuisine = request.POST.get('sub_cuisine')
            package.side_cuisine1 = request.POST.get('side_cuisine1')
            package.side_cuisine2 = request.POST.get('side_cuisine2')
            package.side_cuisine3 = request.POST.get('side_cuisine3')
            package.side_cuisine4 = request.POST.get('side_cuisine4')
            package.side_cuisine5 = request.POST.get('side_cuisine5')
            package.rice = request.POST.get('rice')
            package.bag = request.POST.get('bag')
            package.souvenir = request.POST.get('souvenir')
            package.beverage = request.POST.get('beverages')
            package.unit_price = selected_package.male_price if _type == 'Jantan' else selected_package.female_price
            package.extra_price = ((extra_price_sub + extra_price_side1 + extra_price_side2 +
                                   extra_price_side3 + extra_price_side4 + extra_price_side5 + extra_price_rice + extra_price_bag + extra_price_box + extra_price_beverage) * ((selected_package.box if selected_package.box > 0 else 0) * int(request.POST.get('quantity')))) + (extra_price_main * int(request.POST.get('quantity')))
            package.upgrade = ', '.join(up)
            package.save()

            total = OrderPackage.objects.filter(
                order_id=_id).aggregate(order=Sum('total_price'))
            total_addon = OrderPackageAddon.objects.filter(
                order_id=_id).aggregate(order=Sum('total_price'))
            _total_addon = total_addon['order'] if total_addon['order'] else 0
            order.total_order = total['order'] + \
                _total_addon - order.promo_nominal
            order.save()

            if _add == 2:
                check = request.GET.get('checks')
                qty = request.GET.get('qty')
                _ids = check.split(',')
                _qty = qty.split(',')
                _qty_idx = 0
                # delete all addons first
                OrderPackageAddon.objects.filter(
                    order_id=_id, package_id=_pack).delete()
                for ix, i in enumerate(addons):
                    if str(i[0]) in _ids:
                        try:
                            _addon = OrderPackageAddon(
                                order_id=_id, package_id=_pack, equipment_id=i[0], unit_price=i[2])
                            _addon.save()
                            _update = OrderPackageAddon.objects.get(
                                order_id=_id, package_id=_pack, equipment_id=i[0])
                            _update.quantity = int(_qty[_qty_idx])
                            _update.save()
                        except IntegrityError:
                            _update = OrderPackageAddon.objects.get(
                                order_id=_id, package_id=_pack, equipment_id=i[0])
                            _update.quantity = int(_qty[_qty_idx])
                            _update.save()
                            continue

                        _qty_idx += 1

                    else:
                        OrderPackageAddon.objects.filter(
                            order_id=_id, package_id=_pack, equipment_id=i[0]).delete()

                _addon_order = OrderPackageAddon.objects.filter(
                    order_id=_id, package_id=_pack)
                for idx, j in enumerate(_addon_order):
                    addon_order += j.equipment.equipment_name + \
                        ' (' + str(j.quantity) + ')'
                    if idx < _addon_order.count() - 1:
                        addon_order += ', '

                return HttpResponseRedirect(reverse('order-package-update', args=[_id, package.id, _cat, _pack, _type, 0]))
            else:
                if _add == 3:
                    check = request.GET.get('checks')
                    qty = request.GET.get('qty')
                    _ids = check.split(',')
                    _qty = qty.split(',')
                    _qty_idx = 0
                    # delete all souvenirs first
                    OrderPackageSouvenir.objects.filter(
                        order_id=_id, package_id=_pack).delete()
                    for ix, i in enumerate(souvenirs):
                        if str(i[0]) in _ids:
                            try:
                                _souvenir = OrderPackageSouvenir(
                                    order_id=_id, package_id=_pack, equipment_id=i[0], unit_price=i[2])
                                _souvenir.save()
                                _update = OrderPackageSouvenir.objects.get(
                                    order_id=_id, package_id=_pack, equipment_id=i[0])
                                _update.quantity = int(_qty[_qty_idx])
                                _update.save()
                            except IntegrityError:
                                _update = OrderPackageSouvenir.objects.get(
                                    order_id=_id, package_id=_pack, equipment_id=i[0])
                                _update.quantity = int(_qty[_qty_idx])
                                _update.save()
                                continue

                            _qty_idx += 1

                        else:
                            OrderPackageSouvenir.objects.filter(
                                order_id=_id, package_id=_pack, equipment_id=i[0]).delete()

                    _souvenir_order = OrderPackageSouvenir.objects.filter(
                        order_id=_id, package_id=_pack)
                    for idx, j in enumerate(_souvenir_order):
                        souvenir_order += j.equipment.equipment_name
                        if idx < _souvenir_order.count() - 1:
                            souvenir_order += ', '

                    return HttpResponseRedirect(reverse('order-package-update', args=[_id, package.id, _cat, _pack, _type, 0]))
                else:
                    if _add == 1:
                        return HttpResponseRedirect(reverse('order-package-add', args=[_id, '0', '0', '0', 0]))
                    else:
                        last_package = OrderPackage.objects.filter(
                            order_id=_id).last()
                        if last_package.id == _package:
                            return HttpResponseRedirect(reverse('order-confirm-update', args=[_id]))
                        else:
                            for i in OrderPackage.objects.filter(order_id=_id):
                                if i.id > _package:
                                    return HttpResponseRedirect(reverse('order-package-update', args=[_id, i.id, i.category_id, i.package_id, i.type, 0]))
    else:
        form = FormOrderPackage(instance=package)

    msg = form.errors
    context = {
        'form': form,
        'data': package,
        'first_package': first,
        'n_package': n_package,
        'orders': orders,
        'prev_id': prev_id,
        'prev_cat': prev_cat,
        'prev_pack': prev_pack,
        'prev_type': prev_type,
        'last_child': last_child,
        'cat': _cat,
        'pack': _pack,
        'type': _type,
        'crud': 'update',
        'categories': categories,
        'packages': packages,
        'box_types': box_types,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'rices': rices,
        'bags': bags,
        'beverages': beverages,
        'addons': addons,
        'addon_order': addon_order,
        'souvenirs': souvenirs,
        'souvenir_order': souvenir_order,
        'selected_package': selected_package,
        'order_id': _id,
        'msg': msg,
    }
    return render(request, 'home/order_package_update.html', context)


def order_package_cs_update(request, _id, _cat, _pack, _type):
    package = OrderPackage.objects.get(order_id=_id, package=_pack)
    order = Order.objects.get(order_id=_id)
    selected_package = Package.objects.get(package_id=_pack)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_addon.equipment_id, equipment_name, extra_price, q_addon.equipment_id, q_addon.quantity FROM apps_equipment INNER JOIN apps_addon ON apps_equipment.equipment_id = apps_addon.equipment_id LEFT JOIN (SELECT * FROM apps_orderpackageaddon WHERE order_id = '" + str(_id) + "' AND package_id = '" + str(_pack) + "') AS q_addon ON apps_addon.equipment_id = q_addon.equipment_id WHERE apps_addon.package_id = '" + str(_pack) + "' ORDER BY equipment_name")
        addons = cursor.fetchall()

    if request.POST:
        up = []

        extra_price_main = MainCuisine.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('main_cuisine')).cuisine_id).extra_price if request.POST.get('main_cuisine') else 0
        up.append(request.POST.get('main_cuisine')
                  ) if extra_price_main > 0 else ''
        extra_price_sub = SubCuisine.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('sub_cuisine')).cuisine_id).extra_price if request.POST.get('sub_cuisine') else 0
        up.append(request.POST.get('sub_cuisine')
                  ) if extra_price_sub > 0 else ''
        extra_price_side1 = SideCuisine1.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine1')).cuisine_id).extra_price if request.POST.get('side_cuisine1') else 0
        up.append(request.POST.get('side_cuisine1')
                  ) if extra_price_side1 > 0 else ''
        extra_price_side2 = SideCuisine2.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine2')).cuisine_id).extra_price if request.POST.get('side_cuisine2') else 0
        up.append(request.POST.get('side_cuisine2')
                  ) if extra_price_side2 > 0 else ''
        extra_price_side3 = SideCuisine3.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine3')).cuisine_id).extra_price if request.POST.get('side_cuisine3') else 0
        up.append(request.POST.get('side_cuisine3')
                  ) if extra_price_side3 > 0 else ''
        extra_price_side4 = SideCuisine4.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine4')).cuisine_id).extra_price if request.POST.get('side_cuisine4') else 0
        up.append(request.POST.get('side_cuisine4')
                  ) if extra_price_side4 > 0 else ''
        extra_price_side5 = SideCuisine5.objects.get(
            package=_pack, cuisine=Cuisine.objects.get(cuisine_name=request.POST.get('side_cuisine5')).cuisine_id).extra_price if request.POST.get('side_cuisine5') else 0
        up.append(request.POST.get('side_cuisine5')
                  ) if extra_price_side5 > 0 else ''
        extra_price_rice = Rice.objects.get(package=_pack, cuisine=Cuisine.objects.get(
            cuisine_name=request.POST.get('rice')).cuisine_id).extra_price if request.POST.get('rice') else 0
        up.append(request.POST.get('rice')) if extra_price_rice > 0 else ''
        extra_price_bag = Bag.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('bag')).equipment_id).extra_price if request.POST.get('bag') else 0
        up.append(request.POST.get('bag')) if extra_price_bag > 0 else ''
        extra_price_box = Pack.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('box_type')).equipment_id).extra_price if request.POST.get('box_type') else 0
        up.append(request.POST.get('box_type')
                  ) if extra_price_box > 0 else ''
        extra_price_beverage = Beverage.objects.get(package=_pack, equipment=Equipment.objects.get(
            equipment_name=request.POST.get('beverage')).equipment_id).extra_price if request.POST.get('beverage') else 0
        up.append(request.POST.get('beverage')
                  ) if extra_price_beverage > 0 else ''

        package.category_id = _cat
        package.package_id = _pack
        package.type = _type
        package.quantity = int(request.POST.get('quantity'))
        package.box_qty = int(request.POST.get('box')) if request.POST.get('box') else 0
        package.box_type = request.POST.get('box_type')
        package.main_cuisine = request.POST.get('main_cuisine')
        package.main_cuisine_price = extra_price_main
        package.sub_cuisine = request.POST.get('sub_cuisine')
        package.side_cuisine1 = request.POST.get('side_cuisine1')
        package.side_cuisine2 = request.POST.get('side_cuisine2')
        package.side_cuisine3 = request.POST.get('side_cuisine3')
        package.side_cuisine4 = request.POST.get('side_cuisine4')
        package.side_cuisine5 = request.POST.get('side_cuisine5')
        package.rice = request.POST.get('rice')
        package.bag = request.POST.get('bag')
        package.souvenir = request.POST.get('souvenir')
        package.beverage = request.POST.get('beverage')
        package.unit_price = selected_package.male_price if _type == 'Jantan' else selected_package.female_price
        package.extra_price = ((extra_price_sub + extra_price_side1 + extra_price_side2 +
                               extra_price_side3 + extra_price_side4 + extra_price_side5 + extra_price_rice + extra_price_bag + extra_price_box + extra_price_beverage) * ((selected_package.box if selected_package.box > 0 else 1) * int(request.POST.get('quantity')))) + (extra_price_main * int(request.POST.get('quantity')))
        package.upgrade = ', '.join(up)
        package.save()

        total = OrderPackage.objects.filter(
            order_id=_id).aggregate(order=Sum('total_price'))
        total_addon = OrderPackageAddon.objects.filter(
            order_id=_id).aggregate(order=Sum('total_price'))
        _total_addon = total_addon['order'] if total_addon['order'] else 0
        order.total_order = total['order'] + _total_addon - order.promo_nominal
        order.save()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def order_package_delete(request, _id, _package):
    package = OrderPackage.objects.get(order_id=_id, id=_package)
    package.delete()
    addon = OrderPackageAddon.objects.filter(
        order_id=_id, package_id=_package)
    for i in addon:
        i.delete()
    souvenir = OrderPackageSouvenir.objects.filter(
        order_id=_id, package_id=_package)
    for i in souvenir:
        i.delete()

    total = OrderPackage.objects.filter(
        order_id=_id).aggregate(order=Sum('total_price'))
    total_addon = OrderPackageAddon.objects.filter(
        order_id=_id).aggregate(order=Sum('total_price'))
    _total_addon = total_addon['order'] if total_addon['order'] else 0
    order = Order.objects.get(order_id=_id)
    order.total_order = total['order'] + _total_addon
    order.save()

    first = OrderPackage.objects.filter(order_id=_id).first()

    return HttpResponseRedirect(reverse('order-package-update', args=[_id, first.id, first.category_id, first.package_id, first.type, 0]))


def order_package_cs_delete(request, _id, _pack):
    package = OrderPackage.objects.get(order_id=_id, package_id=_pack)
    package.delete()
    addon = OrderPackageAddon.objects.filter(
        order_id=_id, package_id=_pack)
    for i in addon:
        i.delete()
    souvenir = OrderPackageSouvenir.objects.filter(
        order_id=_id, package_id=_pack)
    for i in souvenir:
        i.delete()

    total = OrderPackage.objects.filter(
        order_id=_id).aggregate(order=Sum('total_price'))
    total_addon = OrderPackageAddon.objects.filter(
        order_id=_id).aggregate(order=Sum('total_price'))
    _total_addon = total_addon['order'] if total_addon['order'] else 0
    order = Order.objects.get(order_id=_id)
    order.total_order = total['order'] + _total_addon
    order.save()

    return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))


def _calculate_order_base_total(order_id):
    total = OrderPackage.objects.filter(order_id=order_id).aggregate(
        order=Sum('total_price'))
    total_addon = OrderPackageAddon.objects.filter(order_id=order_id).aggregate(
        order=Sum('total_price'))
    return (total['order'] or 0) + (total_addon['order'] or 0)


def _apply_order_promo(order, promo_detail=None):
    order.total_order = _calculate_order_base_total(order.order_id)
    if promo_detail:
        order.promo = promo_detail.gift
        order.promo_nominal = promo_detail.nominal
        order.total_order -= promo_detail.nominal
    else:
        order.promo = None
        order.promo_nominal = 0


def _get_order_promo_options(order):
    min_promo = Promo.objects.filter(promo_limit__gt=0).aggregate(
        min=Min('promo_limit'))
    if not min_promo['min']:
        return False, None

    pack_order = OrderPackage.objects.filter(
        order_id=order.order_id, package__promo=True)
    if not pack_order.exists():
        return False, None

    eligible_total = order.total_order + order.promo_nominal
    if eligible_total < min_promo['min']:
        return False, None

    promos = Promo.objects.filter(promo_limit__gt=0).order_by('-promo_limit')
    for promo in promos:
        if eligible_total >= promo.promo_limit:
            return True, PromoDetail.objects.filter(promo_id=promo.promo_id)

    return False, None


def _draw_wrapped_paragraph(pdf_file, text, x, top_y, width, style):
    if not text:
        return top_y

    # Normalize any literal "<br/>" coming from DB or previous formatting.
    # ReportLab Paragraph will treat actual "<br/>" as a tag, but if it is passed through
    # escape() it may show up as visible text. Converting it to newline keeps behavior consistent.
    text = str(text).replace(
        '<br/>', '\n').replace('<br />', '\n').replace('<br>', '\n')
    lines = text.splitlines() or ['']
    paragraph_text = '<br/>'.join(escape(line) for line in lines)
    paragraph = Paragraph(paragraph_text, style)
    _, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(pdf_file, x, top_y - height)
    return top_y - height


def _paragraph_height(text, width, style):
    if not text:
        return 0

    text = str(text).replace(
        '<br/>', '\n').replace('<br />', '\n').replace('<br>', '\n')
    lines = text.splitlines() or ['']
    paragraph_text = '<br/>'.join(escape(line) for line in lines)
    paragraph = Paragraph(paragraph_text, style)
    _, height = paragraph.wrap(width, 1000)
    return height


def _truncate_text_to_width(text, font_name, font_size, max_width):
    if not text:
        return ''

    text = str(text)
    if stringWidth(text, font_name, font_size) <= max_width:
        return text

    ellipsis = '...'
    available_width = max_width - stringWidth(ellipsis, font_name, font_size)
    trimmed = ''
    for char in text:
        if stringWidth(trimmed + char, font_name, font_size) > available_width:
            break
        trimmed += char

    return (trimmed.rstrip() + ellipsis) if trimmed else ellipsis


def _text_or_empty(value):
    return '' if value is None else str(value)


def _join_nonempty(parts, separator=', '):
    return separator.join(str(part) for part in parts if part)


def _validate_delivery_date_not_past(value):
    if not value:
        return None

    try:
        delivery_day = date.fromisoformat(value)
    except (TypeError, ValueError):
        return 'Format tanggal pengiriman tidak valid.'

    if delivery_day < date.today():
        return 'Tanggal pengiriman tidak boleh kurang dari hari ini.'

    return None


def _validate_child_birth_not_future(value):
    if not value:
        return None

    try:
        child_birth_day = datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return 'Format tanggal lahir tidak valid.'

    if child_birth_day > datetime.date.today():
        return 'Tanggal lahir tidak boleh melebihi hari ini.'

    return None


def _paginate_queryset(request, queryset, per_page=25, page_param='page'):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param) or 1
    page_obj = paginator.get_page(page_number)
    return page_obj


def _get_search_query(request, param='search'):
    return request.GET.get(param, '').strip()


def _get_pagination_query(request, page_param='page'):
    query_params = request.GET.copy()
    query_params.pop(page_param, None)
    query_string = query_params.urlencode()
    return f'{query_string}&' if query_string else ''


def _get_cashin_order_popup_context(request, queryset, page_param='order_page', search_param='order_search', per_page=10):
    order_search_query = _get_search_query(request, search_param)
    if order_search_query:
        queryset = queryset.filter(
            Q(order_id__icontains=order_search_query) |
            Q(customer_name__icontains=order_search_query)
        )

    order_page_obj = _paginate_queryset(
        request,
        queryset.order_by('-order_id'),
        per_page=per_page,
        page_param=page_param,
    )

    return {
        'order_popup_data': order_page_obj.object_list,
        'order_page_obj': order_page_obj,
        'order_search_query': order_search_query,
        'order_pagination_query': _get_pagination_query(request, page_param),
        'open_order_modal': request.GET.get('open_order_modal') == '1',
    }


def _refresh_order_payment_status(order_id):
    order = Order.objects.get(order_id=order_id)
    order.down_payment = CashIn.objects.filter(order_id=order_id).aggregate(
        cashin=Sum('cashin_amount')
    )['cashin'] if CashIn.objects.filter(order_id=order_id) else 0
    order.save()

    if order.pending_payment == 0:
        order.order_status = 'LUNAS'
    else:
        if order.down_payment == 0:
            order.order_status = 'CONFIRMED'
        else:
            order.order_status = 'DP'
    order.save()


def order_confirm_update(request, _id):
    order = Order.objects.get(order_id=_id)
    last_package = OrderPackage.objects.filter(order_id=_id).last()
    got_promo, gifts = _get_order_promo_options(order)

    if request.POST:
        form = FormOrderConfirmUpdate(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            order.use_photo = request.POST.get('use_photo')
            order.witnessed = request.POST.get('witnessed')
            order.info_source = request.POST.get('info_source')
            promo_selected = PromoDetail.objects.get(
                id=request.POST.get('promo')) if request.POST.get('promo') else None
            _apply_order_promo(order, promo_selected)
            order.save()

            return HttpResponseRedirect(reverse('order-confirm', args=[_id]))
    else:
        form = FormOrderConfirmUpdate(instance=order)

    msg = form.errors
    context = {
        'form': form,
        'data': order,
        'msg': msg,
        'got_promo': got_promo,
        'gifts': gifts,
        'last_package': last_package,
        'crud': 'update',
    }
    return render(request, 'home/order_confirm_update.html', context)


def order_confirm(request, _id):
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)

    context = {
        'data': order,
        'child': child,
        'package': package,
        'crud': 'view',
    }
    return render(request, 'home/order_confirm.html', context)


def order_submit(request, _id):
    order = Order.objects.get(order_id=_id)
    order.order_status = 'DRAFT' if order.order_status == 'PENDING' else order.order_status
    order.save()

    link_form = AreaSales.objects.get(area_id=order.regional_id).form

    return render(request, 'home/order_thankyou.html', {'link_form': link_form})


def order_cancel(request, _id):
    order = Order.objects.get(order_id=_id)
    order.order_status = 'BATAL'
    order.save()

    return HttpResponseRedirect(reverse('order-index', args=['all', '0']))


def order_confirmed(request, _id):
    order = Order.objects.get(order_id=_id)
    order.order_status = 'CONFIRMED'
    order.cs = get_current_user().username
    order.save()

    children = OrderChild.objects.filter(order_id=_id)

    _customer = Customer.objects.get(customer_phone=order.customer_phone) if Customer.objects.filter(
        customer_phone=order.customer_phone) else None
    if not _customer:
        new_customer = Customer(
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            customer_phone2=order.customer_phone2,
            customer_address=order.customer_address,
            customer_email=order.customer_email,
            customer_district=order.customer_district,
            customer_city=order.customer_city,
            customer_province=order.customer_province,
        )
        new_customer.save()

        for child in children:
            new_detail = CustomerDetail(
                customer_id=new_customer.customer_id,
                child_name=child.child_name,
                child_birth=child.child_birth,
                child_sex=child.child_sex,
                child_father=child.child_father,
                child_mother=child.child_mother,
            )
            new_detail.save()
    else:
        _customer.customer_name = order.customer_name
        _customer.customer_phone = order.customer_phone
        _customer.customer_phone2 = order.customer_phone2
        _customer.customer_address = order.customer_address
        _customer.customer_email = order.customer_email
        _customer.customer_district = order.customer_district
        _customer.customer_city = order.customer_city
        _customer.customer_province = order.customer_province
        _customer.save()

        for child in children:
            _child = CustomerDetail.objects.get(customer_id=_customer.customer_id, child_name=child.child_name) if CustomerDetail.objects.filter(
                customer_id=_customer.customer_id, child_name=child.child_name) else None
            if not _child:
                new_detail = CustomerDetail(
                    customer_id=_customer.customer_id,
                    child_name=child.child_name,
                    child_birth=child.child_birth,
                    child_sex=child.child_sex,
                    child_father=child.child_father,
                    child_mother=child.child_mother,
                )
                new_detail.save()

    return HttpResponseRedirect(reverse('order-index', args=['all', '0']))


@login_required(login_url='/login/')
@role_required(allowed_roles='FORM')
def form_index(request):
    area_sales = AreaSales.objects.all()

    context = {
        'data': area_sales,
        'notif': order_notification(request),
        'segment': 'form',
        'group_segment': 'transaction',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='FORM') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/form_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER-ARCHIVE')
def order_archive(request, _branch, _date):
    search_query = _get_search_query(request)
    all_orders = Order.objects.filter(regional_id__in=AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True), delivery_date__lt=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=[
        'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id__in=AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True), delivery_date__lt=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])
    if _branch == 'all':
        if _date != '0':
            all_orders = all_orders.filter(delivery_date=_date)
        orders = all_orders
    else:
        if _date == '0':
            orders = Order.objects.filter(regional_id=_branch).order_by('-order_id', 'regional').exclude(order_status__in=[
                'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id=_branch).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])
        else:
            orders = Order.objects.filter(regional_id=_branch, delivery_date=_date).order_by('-order_id', 'regional').exclude(order_status__in=[
                'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id=_branch, delivery_date=_date).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])

    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(cs__icontains=search_query) |
            Q(regional__area_name__icontains=search_query) |
            Q(order_status__icontains=search_query)
        )

    br_order = all_orders.values_list('regional', flat=True).distinct()
    branch = AreaSales.objects.filter(area_id__in=br_order)
    br_name = AreaSales.objects.get(
        area_id=_branch).area_name if _branch != 'all' else 'Semua Cabang'
    # get date from delivery date

    page_obj = _paginate_queryset(request, orders)

    context = {
        'data': page_obj.object_list,
        'page_obj': page_obj,
        'branch': branch,
        'br_name': br_name,
        'selected_branch': _branch,
        'selected_date': _date,
        'search_query': search_query,
        'pagination_query': _get_pagination_query(request),
        'notif': order_notification(request),
        'segment': 'order-archive',
        'group_segment': 'transaction',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='ORDER-ARCHIVE') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/order_archive.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_index(request, _branch, _date):
    search_query = _get_search_query(request)
    all_orders = Order.objects.filter(regional_id__in=AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True), delivery_date__gte=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=[
        'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id__in=AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True), delivery_date__gte=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])
    if _branch == 'all':
        if _date != '0':
            all_orders = all_orders.filter(delivery_date=_date)
        orders = all_orders
    else:
        if _date == '0':
            orders = Order.objects.filter(regional_id=_branch, delivery_date__gte=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=[
                'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id=_branch, delivery_date__gte=date.today() - timedelta(days=90)).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])
        else:
            orders = Order.objects.filter(regional_id=_branch, delivery_date=_date).order_by('-order_id', 'regional').exclude(order_status__in=[
                'PENDING', 'BATAL']) if request.user.position_id == 'CS' else Order.objects.filter(regional_id=_branch, delivery_date=_date).order_by('-order_id', 'regional').exclude(order_status__in=['PENDING'])

    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(cs__icontains=search_query) |
            Q(regional__area_name__icontains=search_query) |
            Q(order_status__icontains=search_query)
        )

    br_order = all_orders.values_list('regional', flat=True).distinct()
    branch = AreaSales.objects.filter(area_id__in=br_order)
    br_name = AreaSales.objects.get(
        area_id=_branch).area_name if _branch != 'all' else 'Semua Cabang'
    # get date from delivery date

    page_obj = _paginate_queryset(request, orders)

    context = {
        'data': page_obj.object_list,
        'page_obj': page_obj,
        'branch': branch,
        'br_name': br_name,
        'selected_branch': _branch,
        'selected_date': _date,
        'search_query': search_query,
        'pagination_query': _get_pagination_query(request),
        'notif': order_notification(request),
        'segment': 'order',
        'group_segment': 'transaction',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='ORDER') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/order_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_view(request, _id, _cat, _pack, _type, _crud):
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)
    leftoverfood = OrderLeftoverFood.objects.filter(order_id=_id)
    form = FormOrderView(instance=order)
    formChild = FormOrderChild()
    category = Category.objects.filter(active=True)
    packages = Package.objects.filter(category=_cat, active=True).exclude(package_id__in=OrderPackage.objects.filter(
        order_id=_id).values_list('package_id', flat=True)) if _cat != '0' else None
    packages_upd = Package.objects.filter(category=_cat, active=True).exclude(package_id__in=OrderPackage.objects.filter(
        order_id=_id).values_list('package_id', flat=True).exclude(package_id=_pack)) if _cat != '0' else None
    box = Pack.objects.filter(package=_pack) if _pack != '0' else None
    main_cuisines = MainCuisine.objects.filter(package=_pack)
    sub_cuisines = SubCuisine.objects.filter(package=_pack)
    side_cuisines1 = SideCuisine1.objects.filter(package=_pack)
    side_cuisines2 = SideCuisine2.objects.filter(package=_pack)
    side_cuisines3 = SideCuisine3.objects.filter(package=_pack)
    side_cuisines4 = SideCuisine4.objects.filter(package=_pack)
    side_cuisines5 = SideCuisine5.objects.filter(package=_pack)
    rices = Rice.objects.filter(package=_pack)
    bags = Bag.objects.filter(package=_pack)
    beverages = Beverage.objects.filter(
        package=_pack) if _pack != '0' else None
    selected_package = Package.objects.get(
        package_id=_pack) if _pack != '0' else None
    upd_package = OrderPackage.objects.get(order_id=_id, id=_crud) if _crud not in [
        '0', 'add'] else None
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT apps_addon.equipment_id, equipment_name, extra_price, q_addon.equipment_id, q_addon.quantity FROM apps_equipment INNER JOIN apps_addon ON apps_equipment.equipment_id = apps_addon.equipment_id LEFT JOIN (SELECT * FROM apps_orderpackageaddon WHERE order_id = '" + str(_id) + "' AND package_id = '" + str(_pack) + "') AS q_addon ON apps_addon.equipment_id = q_addon.equipment_id WHERE apps_addon.package_id = '" + str(_pack) + "' ORDER BY equipment_name")
        addons = cursor.fetchall()
    souvenirs = Souvenir.objects.filter(package=_pack)
    addon_order = ''

    _addon_order = OrderPackageAddon.objects.filter(
        order_id=_id, package_id=_pack)
    for idx, j in enumerate(_addon_order):
        addon_order += j.equipment.equipment_name + \
            ' (' + str(j.quantity) + ')'
        if idx < _addon_order.count() - 1:
            addon_order += ', '

    got_promo, gifts = _get_order_promo_options(order)

    if request.POST:
        check = request.GET.get('checks')
        qty = request.GET.get('qty')

        if check is not None or qty is not None:
            _ids = [item for item in (check or '').split(',') if item]
            _qty = [item for item in (qty or '').split(',') if item != '']
            _qty_idx = 0

            # delete all addons first
            OrderPackageAddon.objects.filter(
                order_id=_id, package_id=_pack).delete()

            for ix, i in enumerate(addons):
                if str(i[0]) in _ids:
                    addon_qty = int(_qty[_qty_idx]) if _qty_idx < len(_qty) else 0
                    try:
                        _addon = OrderPackageAddon(
                            order_id=_id, package_id=_pack, equipment_id=i[0], unit_price=i[2])
                        _addon.save()
                        _update = OrderPackageAddon.objects.get(
                            order_id=_id, package_id=_pack, equipment_id=i[0])
                        _update.quantity = addon_qty
                        _update.save()
                    except IntegrityError:
                        _update = OrderPackageAddon.objects.get(
                            order_id=_id, package_id=_pack, equipment_id=i[0])
                        _update.quantity = addon_qty
                        _update.save()
                        continue

                    _qty_idx += 1

                else:
                    OrderPackageAddon.objects.filter(
                        order_id=_id, package_id=_pack, equipment_id=i[0]).delete()

            _addon_order = OrderPackageAddon.objects.filter(
                order_id=_id, package_id=_pack)
            for idx, j in enumerate(_addon_order):
                addon_order += j.equipment.equipment_name + \
                    ' (' + str(j.quantity) + ')'
                if idx < _addon_order.count() - 1:
                    addon_order += ', '

            return HttpResponseRedirect(reverse('order-view', args=[_id, _cat, _pack, _type, _crud]))

    msg = form.errors
    context = {
        'form': form,
        'formChild': formChild,
        'data': order,
        'child': child,
        'package': package,
        'category': category,
        'packages': packages,
        'packages_upd': packages_upd,
        'main_cuisines': main_cuisines,
        'sub_cuisines': sub_cuisines,
        'side_cuisines1': side_cuisines1,
        'side_cuisines2': side_cuisines2,
        'side_cuisines3': side_cuisines3,
        'side_cuisines4': side_cuisines4,
        'side_cuisines5': side_cuisines5,
        'rices': rices,
        'bags': bags,
        'beverages': beverages,
        'selected_package': selected_package,
        'upd_package': upd_package,
        'addons': addons,
        'addon_order': addon_order,
        'souvenirs': souvenirs,
        'box': box,
        'id': _id,
        'cat': _cat,
        'pack': _pack,
        'type': _type,
        'crud_det': _crud,
        'msg': msg,
        'got_promo': got_promo,
        'gifts': gifts,
        'notif': order_notification(request),
        'segment': 'order' if order.delivery_date.date() > date.today() - timedelta(days=90) else 'order-archive',
        'group_segment': 'transaction',
        'crud': 'view',
        'status': order.order_status,
        'archive': True if order.delivery_date.date() <= date.today() - timedelta(days=90) else False,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='ORDER') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/order_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_cs_update(request, _id, _cat, _pack, _type):
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)
    got_promo, gifts = _get_order_promo_options(order)

    if request.POST:
        form = FormOrderCSUpdate(request.POST, instance=order)
        if form.is_valid():
            delivery_date_error = _validate_delivery_date_not_past(
                request.POST.get('delivery_date')
            )
            if delivery_date_error:
                context = {
                    'form': form,
                    'data': order,
                    'child': child,
                    'package': package,
                    'id': _id,
                    'cat': _cat,
                    'pack': _pack,
                    'type': _type,
                    'crud_det': '0',
                    'msg': delivery_date_error,
                    'got_promo': got_promo,
                    'gifts': gifts,
                    'notif': order_notification(request),
                    'segment': 'order',
                    'group_segment': 'transaction',
                    'crud': 'update',
                    'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
                    'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='ORDER') if not request.user.is_superuser else Auth.objects.all(),
                }
                return render(request, 'home/order_view.html', context)

            order = form.save(commit=False)
            order.customer_name = request.POST.get('customer_name')
            order.customer_phone = request.POST.get('customer_phone')
            order.customer_phone2 = request.POST.get('customer_phone2')
            order.customer_email = request.POST.get('customer_email')
            order.customer_address = request.POST.get('customer_address')
            order.customer_city = request.POST.get('customer_city')
            order.customer_district = request.POST.get('customer_district')
            order.customer_province = request.POST.get('customer_province')
            order.delivery_date = request.POST.get('delivery_date')
            order.time_arrival = request.POST.get('time_arrival')
            order.use_photo = request.POST.get('use_photo')
            order.witnessed = request.POST.get('witnessed')
            order.info_source = request.POST.get('info_source')
            order.order_note = request.POST.get('order_note')
            order.discount = int(request.POST.get('discount').replace(
                '.', '')) if request.POST.get('discount') else 0
            promo_selected = PromoDetail.objects.get(
                id=request.POST.get('promo')) if request.POST.get('promo') else None
            _apply_order_promo(order, promo_selected)
            order.save()

            if order.order_status != 'DRAFT':
                customer = Customer.objects.get(customer_phone=order.customer_phone) if Customer.objects.filter(
                    customer_phone=order.customer_phone) else None

                if customer:
                    customer.customer_name = order.customer_name
                    customer.customer_phone = order.customer_phone
                    customer.customer_phone2 = order.customer_phone2
                    customer.customer_address = order.customer_address
                    customer.customer_email = order.customer_email
                    customer.customer_district = order.customer_district
                    customer.customer_city = order.customer_city
                    customer.customer_province = order.customer_province
                    customer.save()

                    for i in OrderChild.objects.filter(order_id=_id):
                        detail = CustomerDetail.objects.get(
                            customer_id=customer.customer_id, child_name=i.child_name) if CustomerDetail.objects.filter(customer_id=customer.customer_id, child_name=i.child_name) else None
                        if not detail:
                            new_detail = CustomerDetail(
                                customer_id=customer.customer_id,
                                child_name=i.child_name,
                                child_birth=i.child_birth,
                                child_sex=i.child_sex,
                                child_father=i.child_father,
                                child_mother=i.child_mother,
                            )
                            new_detail.save()
                else:
                    new_customer = Customer(
                        customer_name=order.customer_name,
                        customer_phone=order.customer_phone,
                        customer_phone2=order.customer_phone2,
                        customer_address=order.customer_address,
                        customer_email=order.customer_email,
                        customer_district=order.customer_district,
                        customer_city=order.customer_city,
                        customer_province=order.customer_province,
                    )
                    new_customer.save()

                    new_children = OrderChild.objects.filter(order_id=_id)
                    for i in new_children:
                        new_detail = CustomerDetail(
                            customer_id=new_customer.customer_id,
                            child_name=i.child_name,
                            child_birth=i.child_birth,
                            child_sex=i.child_sex,
                            child_father=i.child_father,
                            child_mother=i.child_mother,
                        )
                        new_detail.save()

        return HttpResponseRedirect(reverse('order-view', args=[_id, '0', '0', '0', '0']))
    else:
        form = FormOrderCSUpdate(instance=order)

    msg = form.errors

    context = {
        'form': form,
        'data': order,
        'child': child,
        'package': package,
        'id': _id,
        'cat': _cat,
        'pack': _pack,
        'type': _type,
        'crud_det': '0',
        'msg': msg,
        'got_promo': got_promo,
        'gifts': gifts,
        'notif': order_notification(request),
        'segment': 'order',
        'group_segment': 'transaction',
        'crud': 'update',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='ORDER') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/order_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def cashin_index(request):
    search_query = _get_search_query(request)
    cash_in = CashIn.objects.select_related('order', 'order__regional').filter(
        order_id__regional_id__in=AreaUser.objects.filter(
            user_id=request.user.user_id
        ).values_list('area_id', flat=True)
    ).order_by('-cashin_id')
    if search_query:
        cash_in = cash_in.filter(
            Q(order__order_id__icontains=search_query) |
            Q(order__customer_name__icontains=search_query) |
            Q(order__regional__area_name__icontains=search_query) |
            Q(order__order_status__icontains=search_query) |
            Q(bank__icontains=search_query) |
            Q(cashin_note__icontains=search_query) |
            Q(entry_by__icontains=search_query)
        )
    page_obj = _paginate_queryset(request, cash_in)

    context = {
        'data': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'pagination_query': _get_pagination_query(request),
        'notif': order_notification(request),
        'segment': 'cash-in',
        'group_segment': 'accounting',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CASH-IN') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/cashin_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def cashin_add(request, _id, _msg):
    orders = Order.objects.filter(order_status__in=['DP', 'CONFIRMED'], pending_payment__gt=0, regional_id__in=AreaUser.objects.filter(
        user_id=request.user.user_id).values_list('area_id', flat=True))
    order = Order.objects.get(order_id=_id) if Order.objects.filter(
        order_id=_id) else None
    popup_context = _get_cashin_order_popup_context(request, orders)

    if request.POST:
        form = FormCashIn(request.POST, request.FILES)
        if form.is_valid():
            cash_in = form.save(commit=False)
            cash_in.order_id = _id
            cash_in.cashin_type = request.POST.get('cashin_type')
            if cash_in.cashin_amount > Order.objects.get(order_id=_id).pending_payment:
                return HttpResponseRedirect(reverse('cashin-add', args=[_id, '1']))
            cash_in.save()

            if not settings.DEBUG:
                cash_in = CashIn.objects.get(cashin_id=cash_in.cashin_id)
                my_file = cash_in.evidence
                filename = '../aqiqahon.sahabataqiqah.co.id/apps/media/' + my_file.name
                with open(filename, 'wb+') as temp_file:
                    for chunk in my_file.chunks():
                        temp_file.write(chunk)

            selected_order = Order.objects.get(order_id=_id)
            if cash_in.cashin_amount == selected_order.pending_payment:
                selected_order.order_status = 'LUNAS'
            else:
                selected_order.order_status = 'DP'

            selected_order.down_payment += cash_in.cashin_amount
            selected_order.save()

            return HttpResponseRedirect(reverse('cashin-index'))
    else:
        form = FormCashIn()

    msg = form.errors
    context = {
        'form': form,
        'orders': orders,
        'order': order,
        'order_id': _id,
        'msg': _msg,
        # 'error': msg,
        'notif': order_notification(request),
        'segment': 'cash-in',
        'group_segment': 'accounting',
        'crud': 'add',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CASH-IN') if not request.user.is_superuser else Auth.objects.all(),
    }
    context.update(popup_context)

    return render(request, 'home/cashin_add.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def cashin_view(request, _id):
    cash_in = CashIn.objects.get(cashin_id=_id)
    form = FormCashInView(instance=cash_in)

    context = {
        'data': cash_in,
        'form': form,
        'notif': order_notification(request),
        'segment': 'cash-in',
        'group_segment': 'accounting',
        'crud': 'view',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CASH-IN') if not request.user.is_superuser else Auth.objects.all(),
    }

    return render(request, 'home/cashin_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def cashin_update(request, _id, _msg):
    cash_in = CashIn.objects.get(cashin_id=_id)
    orders = Order.objects.filter(pending_payment__gt=0, regional_id__in=AreaUser.objects.filter(
        user_id=request.user.user_id).values_list('area_id', flat=True))
    selected_order_id = request.GET.get('selected_order_id', cash_in.order_id)
    selected_order = Order.objects.get(order_id=selected_order_id) if Order.objects.filter(
        order_id=selected_order_id) else Order.objects.get(order_id=cash_in.order_id)
    order = Order.objects.get(order_id=cash_in.order_id)
    amount_before = cash_in.cashin_amount
    popup_context = _get_cashin_order_popup_context(request, orders)

    if request.POST:
        form = FormCashInUpdate(request.POST, request.FILES, instance=cash_in)
        if form.is_valid():
            update = form.save(commit=False)
            update.cashin_type = request.POST.get('cashin_type')
            target_order_id = request.POST.get(
                'selected_order_id', cash_in.order_id)
            target_order = Order.objects.get(order_id=target_order_id)
            max_allowed = order.pending_payment + \
                amount_before if target_order_id == cash_in.order_id else target_order.pending_payment
            if update.cashin_amount > max_allowed:
                error_url = reverse('cashin-update', args=[_id, '1'])
                if target_order_id:
                    error_url += f'?selected_order_id={target_order_id}'
                return HttpResponseRedirect(error_url)
            original_order_id = cash_in.order_id
            update.order_id = target_order_id
            update.save()

            if not settings.DEBUG:
                cash_in = CashIn.objects.get(cashin_id=cash_in.cashin_id)
                my_file = cash_in.evidence
                filename = '../aqiqahon.sahabataqiqah.co.id/apps/media/' + my_file.name
                with open(filename, 'wb+') as temp_file:
                    for chunk in my_file.chunks():
                        temp_file.write(chunk)

            _refresh_order_payment_status(original_order_id)
            if target_order_id != original_order_id:
                _refresh_order_payment_status(target_order_id)

            return HttpResponseRedirect(reverse('cashin-index'))
    else:
        form = FormCashInUpdate(instance=cash_in)

    # msg = form.errors
    context = {
        'form': form,
        'data': cash_in,
        'orders': orders,
        'selected_order': selected_order,
        'selected_order_id': selected_order.order_id,
        'notif': order_notification(request),
        'segment': 'cash-in',
        'group_segment': 'accounting',
        'crud': 'update',
        'msg': _msg,
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='CASH-IN') if not request.user.is_superuser else Auth.objects.all(),
    }
    context.update(popup_context)

    return render(request, 'home/cashin_view.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def remove_evidence(request, _id):
    cash_in = CashIn.objects.get(cashin_id=_id)
    cash_in.evidence = None
    cash_in.save()

    return HttpResponseRedirect(reverse('cashin-update', args=[_id, '0']))


@login_required(login_url='/login/')
@role_required(allowed_roles='CASH-IN')
def cashin_delete(request, _id):
    cash_in = CashIn.objects.get(cashin_id=_id)
    _order_id = cash_in.order_id
    cash_in.delete()

    selected_order = Order.objects.get(order_id=_order_id)
    selected_order.down_payment = CashIn.objects.filter(
        order_id=_order_id).aggregate(cashin=Sum('cashin_amount'))['cashin'] if CashIn.objects.filter(order_id=_order_id) else 0
    selected_order.save()

    if selected_order.pending_payment == 0:
        selected_order.order_status = 'LUNAS'
    else:
        if selected_order.down_payment == 0:
            selected_order.order_status = 'CONFIRMED'
        else:
            selected_order.order_status = 'DP'
    selected_order.save()

    return HttpResponseRedirect(reverse('cashin-index'))


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_invoice(request, _id):
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)
    region = AreaSales.objects.get(area_id=order.regional_id)

    hari = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad']
    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    order_id = _id.replace('/', '-')
    customer_name = order.customer_name.replace(' ', '_')
    customer_name = customer_name.replace('/', '-')

    styles = getSampleStyleSheet()
    normalStyle = styles['Normal']
    normalStyle.fontSize = 8

    filename = 'INVOICE_' + customer_name + '_' + order_id + '.pdf'
    pdf_file = canvas.Canvas(filename)

    # Add logo in the top left corner
    try:
        logo_path = '../www/aqiqahon/apps/static/img/logo.png'
        image_path = '../www/aqiqahon/apps/static/img/lunas.png'
        if logo_path:
            pdf_file.drawImage(logo_path, 35, 745, width=70, height=61)
    except:
        logo_path = '../../www/aqiqahon/apps/static/img/logo.png'
        image_path = '../../www/aqiqahon/apps/static/img/lunas.png'
        if logo_path:
            pdf_file.drawImage(logo_path, 35, 745, width=70, height=61)

    if order.order_status == 'LUNAS':
        # Add image with transparent 20% in the middle of the page
        if image_path:
            pdf_file.drawImage(image_path, 35, 400, width=525,
                               height=350, mask='auto')

    title = "INVOICE"
    title_width = pdf_file.stringWidth(
        title, "Helvetica-Bold", 12)  # Set font to bold
    page_width, _ = A4
    pdf_file.setFont("Helvetica-Bold", 12)  # Set font to bold
    # Calculate the x position for the title to be in the top right corner
    title_x = page_width - title_width - 35  # 25 is a margin from the right edge
    pdf_file.drawString(title_x, 795, title)

    # Add address below logo
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, 725, 'Cabang :')

    # Add regional info beside regional title with bold font
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(70, 725, order.regional.area_name)
    pdf_file.setFont("Helvetica", 8)
    str_address = order.regional.address if order.regional.address else ''
    address = 'Kantor : ' + str_address
    y = 711
    if str_address:
        y = _draw_wrapped_paragraph(
            pdf_file, address, 35, y, 180, normalStyle) - 6

    str_district = order.regional.district if order.regional.district else ''
    str_city = order.regional.city if order.regional.city else ''
    str_postal_code = order.regional.postal_code if order.regional.postal_code else ''
    comma_district = ', ' if str_district and (
        str_city or str_postal_code) else ''
    comma_city = ', ' if str_city and str_postal_code else ''
    city = str_district + comma_district + str_city + comma_city + str_postal_code
    if city:
        pdf_file.drawString(35, y, city)
        y -= 12
    phone = 'Telp/Whatsapp : 0812 9658 9090'
    pdf_file.drawString(35, y, phone)
    web = 'www.sahabataqiqah.co.id'
    pdf_file.drawString(35, y - 12, web)

    # Add title start from the middle of page
    pdf_file.setFont("Helvetica-Bold", 8)
    title = "No. Referensi"
    page_width, _ = A4
    title_x = (page_width / 2) - 35
    pdf_file.drawString(title_x, 770, title)
    # Add order_id below title
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(title_x, 758, order.order_id)
    # Add order date below order_id with higher space
    pdf_file.setFont("Helvetica-Bold", 8)
    title = "Tanggal Invoice"
    pdf_file.drawString(title_x, 740, title)

    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad']

    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(title_x, 728, days[order.order_date.weekday()] + order.order_date.strftime(
        ', %d ') + months[order.order_date.month - 1] + order.order_date.strftime(' %Y'))
    # Add delivery date below order date with higher space
    pdf_file.setFont("Helvetica-Bold", 8)
    title = "Tanggal Pengiriman"
    pdf_file.drawString(title_x, 710, title)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(title_x, 698, days[order.delivery_date.weekday()] + order.delivery_date.strftime(
        ', %d ') + months[order.delivery_date.month - 1] + order.delivery_date.strftime(' %Y'))
    # Add customer info below delivery date with higher space
    pdf_file.setFont("Helvetica-Bold", 8)
    title = "Nama Pemesan Aqiqah"
    pdf_file.drawString(title_x, 680, title)
    pdf_file.drawString(title_x, 668, order.customer_name)
    # Add customer phone below customer name
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(title_x, 656, order.customer_phone + ' / ' +
                        order.customer_phone2 if order.customer_phone2 else order.customer_phone)

    # Add customer address below customer phone
    y = _draw_wrapped_paragraph(
        pdf_file,
        order.customer_address,
        title_x,
        647,
        270,
        normalStyle,
    ) - 6

    # Add customer district below customer address
    pdf_file.drawString(
        title_x, y, _join_nonempty([order.customer_district, order.customer_city]))
    # Add customer province below customer district
    y -= 13
    pdf_file.drawString(title_x, y, _text_or_empty(order.customer_province))

    y -= 30
    # Add table for order detail
    pdf_file.rect(35, y, 160, 15, stroke=True)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(40, y + 5, 'Produk')
    pdf_file.rect(195, y, 180, 15, stroke=True)
    pdf_file.drawString(200, y + 5, 'Deskripsi')
    pdf_file.rect(375, y, 30, 15, stroke=True)
    # Calculate the width of the string 'Qty'
    qty_width = pdf_file.stringWidth('Qty', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 375 + (30 - qty_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Qty')
    pdf_file.rect(405, y, 85, 15, stroke=True)
    # Calculate the width of the string 'Harga Satuan (Rp)'
    price_width = pdf_file.stringWidth(
        'Harga Satuan (Rp)', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 405 + (85 - price_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Harga Satuan (Rp)')
    pdf_file.rect(490, y, 65, 15, stroke=True)
    # Calculate the width of the string 'Jumlah (Rp)'
    total_width = pdf_file.stringWidth('Jumlah (Rp)', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 490 + (65 - total_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Jumlah (Rp)')

    # Body rows start below the header row (header rect bottom is y)
    row_top = y
    total = 0

    wrap_style = styles['Normal']
    wrap_style.fontSize = 8
    center_style = ParagraphStyle(
        'invoice_center_8',
        parent=wrap_style,
        alignment=TA_CENTER,
    )
    center_style.fontSize = 8
    right_style = ParagraphStyle(
        'invoice_right_8',
        parent=wrap_style,
        alignment=TA_RIGHT,
        rightIndent=5,
    )
    right_style.fontSize = 8

    for pkg in package:
        # Build product cell text (wrapped, no ellipsis)
        qty_pack = f" - {pkg.package.quantity} - " if pkg.package.quantity and pkg.package.quantity > 0 else ''
        category_clean = re.sub(
            r'\s*\([^)]*\)', '', pkg.category.category_name) if pkg.category else ''
        product_lines = [
            f"{category_clean} - {pkg.package.package_name}{qty_pack}".strip(' -')]
        if pkg.package.quantity and pkg.package.quantity > 0:
            product_lines.append(f"Hewan {pkg.type}")
        product_text = '\n'.join(product_lines)

        # Build description cell text (wrapped, no ellipsis)
        desc_lines = []
        row_main = []
        for cuisine in [pkg.main_cuisine, pkg.sub_cuisine, pkg.side_cuisine1]:
            if not cuisine:
                continue
            if pkg.main_cuisine_price and pkg.main_cuisine_price > 0 and cuisine == pkg.main_cuisine:
                row_main.append(
                    cuisine +
                    ' (+ Rp ' + str('{:,}'.format(pkg.main_cuisine_price)
                                    ).replace(',', '.') + ')'
                )
            else:
                row_main.append(cuisine)
        if row_main:
            desc_lines.append(' - '.join(row_main))

        row_sides = [c for c in [pkg.side_cuisine2, pkg.side_cuisine3,
                                 pkg.side_cuisine4, pkg.side_cuisine5] if c]
        str_box = ''
        if row_sides and pkg.package.box and pkg.package.box > 0 and pkg.box_type:
            str_box = f" - {pkg.package.box} Box ({pkg.box_type})"
        elif pkg.package.box and pkg.package.box > 0 and pkg.box_type:
            str_box = f"{pkg.package.box} Box ({pkg.box_type})"
        if row_sides or str_box:
            desc_lines.append(' - '.join(row_sides) + str_box)

        if pkg.upgrade:
            desc_lines.append(f"Up: {pkg.upgrade}")

        addons = OrderPackageAddon.objects.filter(
            order_id=_id, package_id=pkg.package_id)
        if addons.exists():
            parts = []
            for addon in addons:
                parts.append(
                    f"{addon.equipment.equipment_name} ({addon.quantity})")
            desc_lines.append('+ ' + ', '.join(parts))

        if pkg.beverage:
            desc_lines.append(f"Minuman: {pkg.beverage}")

        if pkg.souvenir:
            desc_lines.append(f"Souvenir: {pkg.souvenir}")

        desc_text = '\n'.join(desc_lines)

        product_h = _paragraph_height(product_text, 150, wrap_style)
        desc_h = _paragraph_height(desc_text, 170, wrap_style)

        padding_top = 2
        padding_bottom = 8
        min_row_height = 55
        row_height = max(min_row_height, max(
            product_h, desc_h) + padding_top + padding_bottom)

        row_bottom = row_top - row_height
        pdf_file.rect(35, row_bottom, 160, row_height, stroke=True)
        pdf_file.rect(195, row_bottom, 180, row_height, stroke=True)
        pdf_file.rect(375, row_bottom, 30, row_height, stroke=True)
        pdf_file.rect(405, row_bottom, 85, row_height, stroke=True)
        pdf_file.rect(490, row_bottom, 65, row_height, stroke=True)

        _draw_wrapped_paragraph(pdf_file, product_text,
                                40, row_top - padding_top, 150, wrap_style)
        _draw_wrapped_paragraph(pdf_file, desc_text, 200,
                                row_top - padding_top, 170, wrap_style)

        # Place Qty/Harga/Jumlah using Paragraph so their first visible line
        # aligns with the first line of product/description content.
        top_y = row_top - padding_top

        _draw_wrapped_paragraph(
            pdf_file, str(pkg.quantity), 375, top_y, 30, center_style
        )
        _draw_wrapped_paragraph(
            pdf_file, "{:,}".format(
                pkg.unit_price), 405, top_y, 85, right_style
        )

        base_total = pkg.unit_price * pkg.quantity
        total += base_total
        base_total_str = "{:,}".format(base_total)

        # Align "Up: ..." costs with the paragraph line where "Up:" begins.
        # We do this by counting wrapped lines of the description prefix.
        def _desc_wrapped_line_count(prefix_lines):
            if not prefix_lines:
                return 0
            prefix_text = '<br/>'.join(escape(line)
                                       for line in prefix_lines if line)
            p = Paragraph(prefix_text, wrap_style)
            try:
                p.wrap(170, 1000)
                blPara = getattr(p, 'blPara', None)
                if blPara and hasattr(blPara, 'lines'):
                    return len(blPara.lines)
            except Exception:
                pass
            return 0

        # Build multi-line amounts for the "Jumlah" column.
        money_lines = [base_total_str]  # line 0

        up_line_idx = None
        addon_line_idx = None
        beverage_line_idx = None
        for idx, line in enumerate(desc_lines):
            if line.startswith('Up:') and up_line_idx is None:
                up_line_idx = idx
            if line.startswith('+ ') and addon_line_idx is None:
                addon_line_idx = idx
            if line.startswith('Minuman:') and beverage_line_idx is None:
                beverage_line_idx = idx

        beverage_extra_total = 0
        if pkg.beverage:
            selected_beverage = Beverage.objects.filter(
                package_id=pkg.package_id,
                equipment__equipment_name=pkg.beverage
            ).first()
            if selected_beverage and selected_beverage.extra_price > 0:
                box_multiplier = pkg.package.box if pkg.package.box and pkg.package.box > 0 else 1
                beverage_extra_total = selected_beverage.extra_price * box_multiplier * pkg.quantity

        package_extra_total = pkg.extra_price or 0
        beverage_extra_total = min(beverage_extra_total, package_extra_total)
        other_extra_total = package_extra_total - beverage_extra_total

        if package_extra_total > 0:
            total += package_extra_total

        if other_extra_total > 0:
            up_str = "{:,}".format(other_extra_total)

            lines_before_up = _desc_wrapped_line_count(
                desc_lines[:up_line_idx]) if up_line_idx is not None else _desc_wrapped_line_count(desc_lines[:beverage_line_idx]) if beverage_line_idx is not None else 1
            target_line = lines_before_up if lines_before_up > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = up_str

        if beverage_extra_total > 0:
            beverage_str = "{:,}".format(beverage_extra_total)

            lines_before_beverage = _desc_wrapped_line_count(
                desc_lines[:beverage_line_idx]) if beverage_line_idx is not None else _desc_wrapped_line_count(desc_lines[:up_line_idx]) if up_line_idx is not None else 1
            target_line = lines_before_beverage if lines_before_beverage > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = beverage_str

        if addons.exists() and addon_line_idx is not None:
            total_addon = 0
            for addon in addons:
                total_addon += addon.unit_price * addon.quantity
            total += total_addon
            add_str = "{:,}".format(total_addon)

            lines_before_addon = _desc_wrapped_line_count(
                desc_lines[:addon_line_idx])
            target_line = lines_before_addon if lines_before_addon > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = add_str

        jumlah_text = '\n'.join(money_lines)
        _draw_wrapped_paragraph(
            pdf_file, jumlah_text, 490, top_y, 65, right_style
        )

        row_top = row_bottom

    # Maintain the same vertical offset as the original fixed-height table,
    # so subsequent summary rows (Sub Total / Diskon / DP) don't leave a gap.
    y = row_top + 15

    # Promo
    pdf_file.setFont("Helvetica-Bold", 8)
    if order.promo:
        pdf_file.drawString(200, y - 40, 'Promo: ' + order.promo)

    y -= 30
    # create rectangle from first column to column 3
    pdf_file.setFont("Helvetica", 8)
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Sub Total'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(total)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Diskon'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(order.discount + order.promo_nominal)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'DP'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(order.down_payment)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Jumlah Tertagih'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total = total - order.discount - order.promo_nominal - order.down_payment
    total_str = "{:,}".format(total)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y2 = y
    y -= 30
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(35, y, 'Syarat & Ketentuan')
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y - 15, 'Pengiriman')
    pdf_file.drawString(95, y - 15, ':')
    pdf_file.drawString(
        105, y - 15, hari[int(order.delivery_date.strftime('%w')) - 1] + ', ' + order.delivery_date.strftime('%-d ') + bulan[int(order.delivery_date.strftime('%-m')) - 1] + order.delivery_date.strftime(' %Y'))
    pdf_file.drawString(35, y - 27, 'Jam Tiba')
    pdf_file.drawString(95, y - 27, ':')
    time_arrival_minus_one_hour = datetime.datetime.strptime(
        order.time_arrival, '%H:%M') - datetime.timedelta(hours=1)
    pdf_file.drawString(
        105, y - 27, time_arrival_minus_one_hour.strftime('%H:%M'))
    pdf_file.drawString(35, y - 39, 'Jam Acara')
    pdf_file.drawString(95, y - 39, ':')
    pdf_file.drawString(105, y - 39, _text_or_empty(order.time_arrival))
    pdf_file.drawString(35, y - 51, 'Catatan')
    pdf_file.drawString(95, y - 51, ':')

    y = _draw_wrapped_paragraph(
        pdf_file,
        order.order_note,
        105,
        y - 43,
        200,
        normalStyle,
    )

    y2 -= 30
    pdf_file.setFont("Helvetica-Bold", 8)
    page_width = 595.27
    text = 'Anak yang di aqiqah'
    text_x = (page_width / 2) + 35
    pdf_file.drawString(text_x, y2, text)
    pdf_file.setFont("Helvetica", 8)
    y2 -= 15
    for i in range(1, child.count() + 1):
        pdf_file.drawString(text_x, y2, str(i) + '.')
        pdf_file.drawString(text_x + 10, y2, child[i - 1].child_name)
        y2 -= 12
        sex = 'Laki-laki' if child[i - 1].child_sex == '1' else 'Perempuan'
        pdf_file.drawString(
            text_x + 10, y2, '(' + child[i - 1].child_birth.strftime('%-d') + ' ' + bulan[int(child[i - 1].child_birth.strftime('%-m')) - 1] + ' ' + child[i - 1].child_birth.strftime('%Y') + ') | ' + sex)
        y2 -= 12

    y2 -= 15
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(text_x, y2, 'Anak dari')
    pdf_file.setFont("Helvetica", 8)
    y2 -= 15
    pdf_file.drawString(
        text_x, y2, child[0].child_father)
    y2 -= 12
    pdf_file.drawString(text_x, y2, child[0].child_mother)

    # Place this block two lines below the wrapped order note so it follows
    # note height dynamically instead of using a fixed offset.
    y -= 36
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(
        35, y, 'Sertifikat dan Kartu Ucapan pakai foto atau tidak?')
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(
        35, y - 12, 'YA' if order.use_photo == 1 else 'TIDAK')

    y -= 27
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(35, y, 'Penyembelihan disaksikan?')
    y -= 12
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y, 'YA' if order.witnessed == 1 else 'TIDAK')

    y -= 15
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(35, y, 'Sumber Informasi?')
    y -= 12
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y, _text_or_empty(order.info_source))

    y -= 30
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(
        35, y, '* Pembayaran DP 30% dari total Invoice, baru tercatat sebagai order')
    y -= 12
    pdf_file.drawString(
        41, y, 'yang sah. Dan pelunasan selambat-lambatnya pada hari H.')

    y -= 30
    pdf_file.drawString(
        35, y, 'Pembayaran dapat dilakukan melalui transfer ke rekening :')
    y -= 15
    bank = _text_or_empty(region.bank_account).split(
        '\n') if region.bank_account else []
    for line in bank:
        bank_paragraph = Paragraph(line, normalStyle)
        bank_paragraph.wrapOn(pdf_file, 200, 100)
        bank_paragraph.drawOn(pdf_file, 35, y)
        y -= 10

    y2 -= 30
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(text_x, y2, 'Tangerang, ' + order.order_date.strftime('%-d ') +
                        bulan[int(order.order_date.strftime('%-m')) - 1] + order.order_date.strftime(' %Y'))
    y2 -= 55
    gm = User.objects.get(position='GM')
    sign_path = gm.signature.path
    pdf_file.drawImage(sign_path, text_x, y2, width=100, height=50)

    y2 -= 15
    pdf_file.drawString(text_x, y2, gm.username)
    y2 -= 12
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(text_x, y2, gm.position.position_name)

    pdf_file.save()

    return FileResponse(open(filename, 'rb'), content_type='application/pdf')


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_bap(request, _id):
    order = Order.objects.get(order_id=_id)
    child = OrderChild.objects.filter(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)
    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    order_id = _id.replace('/', '-')
    customer_name = order.customer_name.replace(' ', '_')
    customer_name = customer_name.replace('/', '-')

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 8
    bold_style = styles['Normal']
    bold_style.fontSize = 8
    bold_style.fontName = 'Helvetica-Bold'

    filename = 'SURAT_JALAN_' + customer_name + '_' + order_id + '.pdf'
    pdf_file = canvas.Canvas(filename)

    # Add logo in the top center
    try:
        logo_path = '../www/aqiqahon/apps/static/img/logo.png'
        image_path = '../www/aqiqahon/apps/static/img/lunas.png'
        if logo_path:
            pdf_file.drawImage(logo_path, 260, 745, width=70, height=61)
    except:
        logo_path = '../../www/aqiqahon/apps/static/img/logo.png'
        image_path = '../../www/aqiqahon/apps/static/img/lunas.png'
        if logo_path:
            pdf_file.drawImage(logo_path, 260, 745, width=70, height=61)

    if order.order_status == 'LUNAS':
        # Add image with transparent 20% in the middle of the page
        if image_path:
            pdf_file.drawImage(image_path, 35, 400, width=525,
                               height=350, mask='auto')

    y = 725
    title = "SURAT JALAN SAHABAT AQIQAH"
    title_width = pdf_file.stringWidth(title, "Helvetica-Bold", 12)
    page_width, _ = A4
    title_x = (page_width / 2) - (title_width / 2)
    pdf_file.setFont("Helvetica-Bold", 12)
    pdf_file.drawString(title_x, y, title)

    y -= 50
    y2 = y
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y, 'Nama Shahibul Aqiqah (1)')
    pdf_file.drawString(135, y, ':')
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(145, y, child[0].child_name)
    y -= 12
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y, 'Nama Pemesan')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, order.customer_name)
    y -= 12
    pdf_file.drawString(35, y, 'No. Telepon')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, order.customer_phone +
                        ' / ' + str(order.customer_phone2) if order.customer_phone2 else order.customer_phone)
    y -= 12
    pdf_file.drawString(35, y, 'Alamat')
    pdf_file.drawString(135, y, ':')

    y = _draw_wrapped_paragraph(
        pdf_file,
        order.customer_address,
        145,
        y + 8,
        232,
        bold_style,
    ) - 6

    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(35, y, 'Kecamatan')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, _text_or_empty(order.customer_district))
    y -= 12
    pdf_file.drawString(35, y, 'Kota/Kabupaten')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, _text_or_empty(order.customer_city))
    y -= 12
    pdf_file.drawString(35, y, 'Propinsi')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, _text_or_empty(order.customer_province))
    y -= 12

    pdf_file.drawString(35, y, 'Tanggal Pengiriman')
    pdf_file.drawString(135, y, ':')
    pdf_file.drawString(145, y, order.delivery_date.strftime(
        '%-d ') + bulan[order.delivery_date.month - 1] + order.delivery_date.strftime(' %Y'))
    y -= 12
    pdf_file.drawString(35, y, 'Jam Acara')
    pdf_file.drawString(135, y, ':')
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(145, y, order.time_arrival)

    # Add table right beside the customer info
    y2 -= 2
    pdf_file.rect(405, y2, 150, 15, stroke=True)
    pdf_file.setFont("Helvetica-Bold", 8)
    text = 'No. Order'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 150
    text_x = 405 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y2 + 5, text)
    pdf_file.rect(405, y2 - 15, 150, 15, stroke=True)
    pdf_file.setFont("Helvetica", 8)
    text = order.order_id
    text_width = pdf_file.stringWidth(text, "Helvetica", 8)
    text_x = 405 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y2 - 10, text)

    y -= 30
    # Add table for order detail
    pdf_file.rect(35, y, 160, 15, stroke=True)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(40, y + 5, 'Produk')
    pdf_file.rect(195, y, 180, 15, stroke=True)
    pdf_file.drawString(200, y + 5, 'Deskripsi')
    pdf_file.rect(375, y, 30, 15, stroke=True)
    # Calculate the width of the string 'Qty'
    qty_width = pdf_file.stringWidth('Qty', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 375 + (30 - qty_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Qty')
    pdf_file.rect(405, y, 85, 15, stroke=True)
    # Calculate the width of the string 'Harga Satuan (Rp)'
    price_width = pdf_file.stringWidth(
        'Harga Satuan (Rp)', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 405 + (85 - price_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Harga Satuan (Rp)')
    pdf_file.rect(490, y, 65, 15, stroke=True)
    # Calculate the width of the string 'Jumlah (Rp)'
    total_width = pdf_file.stringWidth('Jumlah (Rp)', "Helvetica-Bold", 8)
    # Calculate the center position of the rectangle
    center_x = 490 + (65 - total_width) / 2
    pdf_file.drawString(center_x, y + 5, 'Jumlah (Rp)')

    row_top = y
    total = 0

    wrap_style = styles['Normal']
    wrap_style.fontSize = 8
    wrap_style.fontName = 'Helvetica'
    center_style = ParagraphStyle(
        'bap_center_8',
        parent=wrap_style,
        alignment=TA_CENTER,
    )
    right_style = ParagraphStyle(
        'bap_right_8',
        parent=wrap_style,
        alignment=TA_RIGHT,
        rightIndent=5,
    )

    for pkg in package:
        qty_pack = f" - {pkg.package.quantity} - " if pkg.package.quantity and pkg.package.quantity > 0 else ''
        category_clean = re.sub(
            r'\s*\([^)]*\)', '', pkg.category.category_name) if pkg.category else ''
        product_lines = [
            f"{category_clean} - {pkg.package.package_name}{qty_pack}".strip(' -')]
        if pkg.package.quantity and pkg.package.quantity > 0:
            product_lines.append(f"Hewan {pkg.type}")
        product_text = '\n'.join(product_lines)

        desc_lines = []
        row_main = []
        for cuisine in [pkg.main_cuisine, pkg.sub_cuisine, pkg.side_cuisine1]:
            if not cuisine:
                continue
            if pkg.main_cuisine_price and pkg.main_cuisine_price > 0 and cuisine == pkg.main_cuisine:
                row_main.append(
                    cuisine +
                    ' (+ Rp ' + str('{:,}'.format(pkg.main_cuisine_price)
                                    ).replace(',', '.') + ')'
                )
            else:
                row_main.append(cuisine)
        if row_main:
            desc_lines.append(' - '.join(row_main))

        row_sides = [c for c in [pkg.side_cuisine2, pkg.side_cuisine3,
                                 pkg.side_cuisine4, pkg.side_cuisine5] if c]
        str_box = ''
        if row_sides and pkg.package.box and pkg.package.box > 0 and pkg.box_type:
            str_box = f" - {pkg.package.box} Box ({pkg.box_type})"
        elif pkg.package.box and pkg.package.box > 0 and pkg.box_type:
            str_box = f"{pkg.package.box} Box ({pkg.box_type})"
        if row_sides or str_box:
            desc_lines.append(' - '.join(row_sides) + str_box)

        if pkg.upgrade:
            desc_lines.append(f"Up: {pkg.upgrade}")

        addons = OrderPackageAddon.objects.filter(
            order_id=_id, package_id=pkg.package_id)
        if addons.exists():
            parts = []
            for addon in addons:
                parts.append(
                    f"{addon.equipment.equipment_name} ({addon.quantity})")
            desc_lines.append('+ ' + ', '.join(parts))

        if pkg.beverage:
            desc_lines.append(f"Minuman: {pkg.beverage}")

        if pkg.souvenir:
            desc_lines.append(f"Souvenir: {pkg.souvenir}")

        desc_text = '\n'.join(desc_lines)

        product_h = _paragraph_height(product_text, 150, wrap_style)
        desc_h = _paragraph_height(desc_text, 170, wrap_style)

        padding_top = 2
        padding_bottom = 8
        min_row_height = 55
        row_height = max(min_row_height, max(
            product_h, desc_h) + padding_top + padding_bottom)

        row_bottom = row_top - row_height
        pdf_file.rect(35, row_bottom, 160, row_height, stroke=True)
        pdf_file.rect(195, row_bottom, 180, row_height, stroke=True)
        pdf_file.rect(375, row_bottom, 30, row_height, stroke=True)
        pdf_file.rect(405, row_bottom, 85, row_height, stroke=True)
        pdf_file.rect(490, row_bottom, 65, row_height, stroke=True)

        _draw_wrapped_paragraph(pdf_file, product_text,
                                40, row_top - padding_top, 150, wrap_style)
        _draw_wrapped_paragraph(pdf_file, desc_text, 200,
                                row_top - padding_top, 170, wrap_style)

        top_y = row_top - padding_top
        _draw_wrapped_paragraph(pdf_file, str(
            pkg.quantity), 375, top_y, 30, center_style)
        _draw_wrapped_paragraph(pdf_file, "{:,}".format(
            pkg.unit_price), 405, top_y, 85, right_style)

        base_total = pkg.unit_price * pkg.quantity
        total += base_total
        money_lines = ["{:,}".format(base_total)]

        def _desc_wrapped_line_count(prefix_lines):
            if not prefix_lines:
                return 0
            prefix_text = '<br/>'.join(escape(line)
                                       for line in prefix_lines if line)
            p = Paragraph(prefix_text, wrap_style)
            try:
                p.wrap(170, 1000)
                blPara = getattr(p, 'blPara', None)
                if blPara and hasattr(blPara, 'lines'):
                    return len(blPara.lines)
            except Exception:
                pass
            return 0

        up_line_idx = None
        addon_line_idx = None
        beverage_line_idx = None
        for idx, line in enumerate(desc_lines):
            if line.startswith('Up:') and up_line_idx is None:
                up_line_idx = idx
            if line.startswith('+ ') and addon_line_idx is None:
                addon_line_idx = idx
            if line.startswith('Minuman:') and beverage_line_idx is None:
                beverage_line_idx = idx

        beverage_extra_total = 0
        if pkg.beverage:
            selected_beverage = Beverage.objects.filter(
                package_id=pkg.package_id,
                equipment__equipment_name=pkg.beverage
            ).first()
            if selected_beverage and selected_beverage.extra_price > 0:
                box_multiplier = pkg.package.box if pkg.package.box and pkg.package.box > 0 else 1
                beverage_extra_total = selected_beverage.extra_price * box_multiplier * pkg.quantity

        package_extra_total = pkg.extra_price or 0
        beverage_extra_total = min(beverage_extra_total, package_extra_total)
        other_extra_total = package_extra_total - beverage_extra_total

        if package_extra_total > 0:
            total += package_extra_total

        if other_extra_total > 0:
            target_line = _desc_wrapped_line_count(desc_lines[:up_line_idx]) if up_line_idx is not None else _desc_wrapped_line_count(desc_lines[:beverage_line_idx]) if beverage_line_idx is not None else 1
            target_line = target_line if target_line > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = "{:,}".format(other_extra_total)

        if beverage_extra_total > 0:
            target_line = _desc_wrapped_line_count(desc_lines[:beverage_line_idx]) if beverage_line_idx is not None else _desc_wrapped_line_count(desc_lines[:up_line_idx]) if up_line_idx is not None else 1
            target_line = target_line if target_line > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = "{:,}".format(beverage_extra_total)

        if addons.exists() and addon_line_idx is not None:
            total_addon = 0
            for addon in addons:
                total_addon += addon.unit_price * addon.quantity
            total += total_addon
            target_line = _desc_wrapped_line_count(desc_lines[:addon_line_idx])
            target_line = target_line if target_line > 0 else 1
            while len(money_lines) <= target_line:
                money_lines.append('')
            money_lines[target_line] = "{:,}".format(total_addon)

        _draw_wrapped_paragraph(pdf_file, '\n'.join(
            money_lines), 490, top_y, 65, right_style)
        row_top = row_bottom

    y = row_top + 15

    # Promo
    pdf_file.setFont("Helvetica-Bold", 8)
    if order.promo:
        pdf_file.drawString(200, y - 40, 'Promo: ' + order.promo)

    y -= 30
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Sub Total'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(total)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Diskon'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(order.discount + order.promo_nominal)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'DP'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total_str = "{:,}".format(order.down_payment)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 15
    # create rectangle from first column to column 3
    pdf_file.rect(35, y, 455, 15, stroke=True)
    total_str = 'Jumlah Tertagih'
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica-Bold", 8)
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.drawString(490 - total_str_width - 5, y + 5, total_str)
    pdf_file.rect(490, y, 65, 15, stroke=True)
    total = total - order.discount - order.promo_nominal - order.down_payment
    total_str = "{:,}".format(total)
    total_str_width = pdf_file.stringWidth(total_str, "Helvetica", 8)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(490 + 65 - total_str_width - 5, y + 5, total_str)

    y -= 60
    pdf_file.setFont("Helvetica-Bold", 8)
    pdf_file.rect(35, y, 100, 15, stroke=False)
    text = 'GA'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 100
    text_x = 35 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y + 5, text)
    pdf_file.rect(135, y, 100, 15, stroke=False)
    text = 'Kurir'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 100
    text_x = 135 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y + 5, text)
    pdf_file.rect(35, y - 50, 100, 15, stroke=False)
    text = '( __________________ )'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 100
    text_x = 35 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y - 50, text)
    pdf_file.rect(135, y - 50, 100, 15, stroke=False)
    text = '( __________________ )'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 100
    text_x = 135 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y - 50, text)

    pdf_file.rect(250, y, 210, 15, stroke=True)
    pdf_file.setFont("Helvetica-Bold", 8)
    text = 'Keterangan'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 210
    text_x = 250 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y + 5, text)
    pdf_file.rect(460, y, 45, 15, stroke=True)
    text = 'Checklist'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 45
    text_x = 460 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y + 5, text)
    pdf_file.rect(505, y, 50, 15, stroke=True)
    text = 'Penerima'
    text_width = pdf_file.stringWidth(text, "Helvetica-Bold", 8)
    box_width = 50
    text_x = 505 + (box_width - text_width) / 2
    pdf_file.drawString(text_x, y + 5, text)

    y -= 15
    pdf_file.rect(250, y, 210, 15, stroke=True)
    pdf_file.setFont("Helvetica", 8)
    pdf_file.drawString(
        255, y + 5, 'Kelengkapan isi box dari paketan sudah sesuai orderan')
    pdf_file.rect(460, y, 45, 15, stroke=True)
    pdf_file.rect(505, y - 25, 50, 40, stroke=True)
    y -= 15
    pdf_file.rect(250, y - 10, 210, 25, stroke=True)
    pdf_file.drawString(
        255, y + 5, 'Saran penyajian: sebaiknya dikonsumsi maks 3 jam')
    pdf_file.drawString(
        255, y - 5, 'setelah masakan diterima')
    pdf_file.rect(460, y - 10, 45, 25, stroke=True)

    pdf_file.save()

    return FileResponse(open(filename, 'rb'), content_type='application/pdf')


@login_required(login_url='/login/')
@role_required(allowed_roles='ORDER')
def order_checklist(request, _id):
    order = Order.objects.get(order_id=_id)
    package = OrderPackage.objects.filter(order_id=_id)

    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    order_id = _id.replace('/', '-')
    customer_name = order.customer_name.replace(' ', '_')
    customer_name = customer_name.replace('/', '-')

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 8

    filename = 'CHECKLIST_' + customer_name + '_' + order_id + '.pdf'
    pdf_file = canvas.Canvas(filename)

    def checklist_draw_wrapped_field(cvs, page_w, col_x, y, label, value,
                                     font='Helvetica', size=8, line_height=12):
        text = str(value) if value is not None else ''
        text = text.replace('\r', ' ').replace('\n', ' ')
        value_x = col_x + 90
        max_w = max(40.0, page_w - 35 - value_x)
        cvs.setFont(font, size)
        lines = simpleSplit(text.strip(), font, size, max_w) if text.strip() else ['']
        if not lines:
            lines = ['']
        cvs.drawString(col_x, y, label)
        cvs.drawString(col_x + 80, y, ':')
        cvs.drawString(value_x, y, lines[0])
        y -= line_height
        for line in lines[1:]:
            cvs.drawString(value_x, y, line)
            y -= line_height
        return y

    for i in range(0, package.count()):
        # Add logo in the top left corner
        try:
            logo_path = '../www/aqiqahon/apps/static/img/logo.png'
            pdf_file.drawImage(logo_path, 35, 745, width=70, height=61)
        except:
            logo_path = '../../www/aqiqahon/apps/static/img/logo.png'
            pdf_file.drawImage(logo_path, 35, 745, width=70, height=61)

        title = "CHECKLIST FORM"
        title_width = pdf_file.stringWidth(
            title, "Helvetica-Bold", 12)  # Set font to bold
        page_width, _ = A4
        pdf_file.setFont("Helvetica-Bold", 12)  # Set font to bold
        # Calculate the x position for the title to be in the top right corner
        title_x = page_width - title_width - 35  # 25 is a margin from the right edge
        pdf_file.drawString(title_x, 795, title)

        # Add address below logo
        pdf_file.setFont("Helvetica", 8)
        pdf_file.drawString(35, 725, 'Cabang :')
        title_x = (page_width / 2) + 35

        # Add regional info beside regional title with bold font
        pdf_file.setFont("Helvetica-Bold", 8)
        pdf_file.drawString(74, 725, order.regional.area_name)
        pdf_file.setFont("Helvetica", 8)
        str_address = order.regional.address if order.regional.address else ''
        address = 'Kantor : ' + str_address
        y = 713
        if str_address:
            max_left_width = max(120, title_x - 60)
            address_lines = simpleSplit(address, "Helvetica", 8, max_left_width)
            for line in address_lines:
                pdf_file.drawString(35, y, line)
                y -= 12
        str_district = order.regional.district if order.regional.district else ''
        str_city = order.regional.city if order.regional.city else ''
        str_postal_code = order.regional.postal_code if order.regional.postal_code else ''
        comma_district = ', ' if str_district and (
            str_city or str_postal_code) else ''
        comma_city = ', ' if str_city and str_postal_code else ''
        city = str_district + comma_district + str_city + comma_city + str_postal_code
        if city:
            max_left_width = max(120, title_x - 60)
            city_lines = simpleSplit(city, "Helvetica", 8, max_left_width)
            for line in city_lines:
                pdf_file.drawString(35, y, line)
                y -= 12
        phone = 'Telp/Whatsapp : 0812 9658 9090'
        pdf_file.drawString(35, y, phone)
        web = 'www.sahabataqiqah.co.id'
        pdf_file.drawString(35, y - 12, web)
        y_left_bottom = y - 12

        col_x = title_x
        yr = 745
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "No. Invoice", order.order_id)
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Nama Pemesan", order.customer_name)
        delivery_str = order.delivery_date.strftime(
            '%-d ') + bulan[order.delivery_date.month - 1] + order.delivery_date.strftime(' %Y')
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Tanggal Delivery", delivery_str)
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Checker", '______________________')
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Driver", '______________________')
        category_clean = re.sub(r'\s*\([^)]*\)',
                                '', package[i].category.category_name)
        menu_text = f"{category_clean} - {package[i].package.package_name}"
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Menu", menu_text)
        box = package[i].package.box if package[i].package.box > 0 else 1
        qty = package[i].quantity
        box_type = package[i].box_type if package[i].box_type else ''
        box_text = (str(box * qty) + ' ' + box_type).strip()
        yr = checklist_draw_wrapped_field(
            pdf_file, page_width, col_x, yr, "Jumlah Box/Porsi", box_text)

        y = min(y_left_bottom, yr)
        y -= 30
        pdf_file.setFont("Helvetica-Bold", 8)
        pdf_file.line(35, y, page_width - 35, y)
        y -= 15
        y2 = y
        pdf_file.drawString(40, y, 'DI ISI OLEH DRIVER')
        pdf_file.drawString(140, y, 'DI ISI OLEH CHECKER')
        y -= 10
        pdf_file.line(35, y, page_width - 35, y)
        pdf_file.setFont("Helvetica", 8)

        rice = package[i].rice
        if rice:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(
                140, y + 5, rice)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].main_cuisine:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].main_cuisine)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].sub_cuisine:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].sub_cuisine)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].side_cuisine1:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].side_cuisine1)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].side_cuisine2:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].side_cuisine2)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].side_cuisine3:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].side_cuisine3)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].side_cuisine4:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].side_cuisine4)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)
        if package[i].side_cuisine5:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].side_cuisine5)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        other = Other.objects.filter(
            package_id=package[i].package_id)
        if other.count() > 0:
            for j in range(0, other.count()):
                y -= 20
                pdf_file.rect(40, y, 80, 15, stroke=True)
                pdf_file.drawString(140, y + 5, str(other[j].equipment))
                y -= 5
                pdf_file.line(35, y, page_width - 35, y)

        package_addons = OrderPackageAddon.objects.filter(
            order=order, package=package[i].package
        ).select_related('equipment')
        for addon in package_addons:
            if addon.equipment is None:
                continue
            addon_label = addon.equipment.equipment_name
            if addon.quantity and addon.quantity > 1:
                addon_label = addon_label + ' (x' + str(addon.quantity) + ')'
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, addon_label)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        if package[i].beverage:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].beverage)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        y -= 20
        pdf_file.rect(40, y, 80, 15, stroke=True)
        pdf_file.drawString(140, y + 5, 'Sertifikat')
        y -= 5
        pdf_file.line(35, y, page_width - 35, y)

        if package[i].bag:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].bag)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        if package[i].souvenir:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, package[i].souvenir)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        if order.promo and order.promo_nominal == 0:
            y -= 20
            pdf_file.rect(40, y, 80, 15, stroke=True)
            pdf_file.drawString(140, y + 5, 'Promo: ' + order.promo)
            y -= 5
            pdf_file.line(35, y, page_width - 35, y)

        y -= 20
        pdf_file.rect(40, y, 80, 15, stroke=True)
        pdf_file.drawString(140, y + 5, 'BAP & Kwitansi')
        y -= 5
        pdf_file.line(35, y, page_width - 35, y)
        y -= 20
        pdf_file.rect(40, y, 80, 15, stroke=True)
        pdf_file.drawString(140, y + 5, 'Sisa Masakan Olahan Daging ......')
        y -= 5
        pdf_file.line(35, y, page_width - 35, y)
        y -= 20
        pdf_file.rect(40, y, 80, 15, stroke=True)
        pdf_file.drawString(
            140, y + 5, 'Sisa Masakan Olahan Tulangan & Jeroan ......')
        y -= 5
        pdf_file.line(35, y, page_width - 35, y)

        pdf_file.setFont("Helvetica-Bold", 8)
        pdf_file.drawString(title_x, y2, 'CATATAN LAINNYA')
        y2 -= 30
        pdf_file.rect(title_x, y2, 80, 15, stroke=True)
        y2 -= 25
        pdf_file.rect(title_x, y2, 80, 15, stroke=True)
        y2 -= 25
        pdf_file.rect(title_x, y2, 80, 15, stroke=True)

        y -= 60
        title = "TTD CHECKER"
        title_width = pdf_file.stringWidth(title, "Helvetica-Bold", 8)
        pdf_file.rect(35, y, (page_width - 2*35) / 2, 15, stroke=False)
        pdf_file.drawString(35 + (((page_width / 2 - 35) -
                            title_width) / 2), y + 5, title)
        string = '( __________________ )'
        string_width = pdf_file.stringWidth(string, "Helvetica-Bold", 8)
        pdf_file.drawString(35 + (((page_width / 2 - 35) -
                            string_width) / 2), y - 80, string)
        title = "TTD DRIVER"
        title_width = pdf_file.stringWidth(title, "Helvetica-Bold", 8)
        pdf_file.rect(35 + (page_width - 2*35) / 2, y,
                      (page_width - 2*35) / 2, 15, stroke=False)
        pdf_file.drawString(35 + (page_width - 2*35) / 2 +
                            ((page_width - 2*35) / 2 - title_width) / 2, y + 5, title)
        pdf_file.drawString(35 + (page_width - 2*35) / 2 +
                            ((page_width - 2*35) / 2 - string_width) / 2, y - 80, string)
        pdf_file.showPage()

    pdf_file.save()

    return FileResponse(open(filename, 'rb'), content_type='application/pdf')


@login_required(login_url='/login/')
@role_required(allowed_roles='JADWAL')
def jadwal_index(request):
    areas = AreaUser.objects.filter(user_id=request.user.user_id)
    area_ids = areas.values_list('area_id', flat=True)

    context = {
        'notif': order_notification(request),
        'segment': 'jadwal',
        'group_segment': 'transaction',
        'crud': 'index',
        'role': Auth.objects.filter(user_id=request.user.user_id).values_list('menu_id', flat=True),
        'btn': Auth.objects.get(user_id=request.user.user_id, menu_id='JADWAL') if not request.user.is_superuser else Auth.objects.all(),
        'areas': AreaSales.objects.filter(area_id__in=area_ids),
    }
    return render(request, 'home/jadwal_index.html', context)


@login_required(login_url='/login/')
@role_required(allowed_roles='JADWAL')
def jadwal_events(request):
    start = request.GET.get('start', '').split('T')[0]
    end = request.GET.get('end', '').split('T')[0]
    filter_branch_list = request.GET.getlist('branch', [])
    filter_branch_list = [b for b in filter_branch_list if b and b != 'all']
    status = request.GET.get('status', 'all')
    driver = request.GET.get('driver', '').strip()

    areas = AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True)
    orders = Order.objects.filter(
        delivery_date__date__gte=start,
        delivery_date__date__lte=end,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])

    if filter_branch_list:
        orders = orders.filter(regional_id__in=filter_branch_list)
    if status != 'all':
        orders = orders.filter(schedule_status=status)
    if driver:
        orders = orders.filter(driver__icontains=driver)

    schedule_status_colors = {
        'UNSCHEDULED': '#6c757d',
        'SCHEDULED': '#ffc107',
        'COOKING': '#fd7e14',
        'PACKING': '#17a2b8',
        'READY': '#0dcaf0',
        'ON_DELIVERY': '#0d6efd',
        'COMPLETED': '#28a745',
        'CANCELLED': '#dc3545',
    }

    events = []
    for order in orders.select_related('regional'):
        if not order.regional:
            continue
        try:
            dt = str(order.departure_time or '').strip()
            event_hour, event_min = 0, 0
            if dt:
                try:
                    parts = dt.split(':')
                    event_hour = int(parts[0])
                    event_min = int(parts[1]) if len(parts) > 1 else 0
                except (ValueError, IndexError):
                    event_hour, event_min = 0, 0
            start_str = order.delivery_date.strftime('%Y-%m-%d') + 'T{:02d}:{:02d}:00'.format(event_hour, event_min)

            packages = OrderPackage.objects.filter(order=order).select_related('category', 'package', 'package__goat_type')
            product_list = []
            description_parts = []
            quantity_total = 0
            goat_types = []
            goat_type_names = []
            for pkg in packages:
                category_clean = re.sub(r'\s*\([^)]*\)', '', pkg.category.category_name) if pkg.category else ''
                product_name = f"{category_clean} - {pkg.package.package_name}".strip(' -')
                product_list.append(product_name)
                quantity_total += (pkg.package.quantity or 0) * (pkg.quantity or 1)
                if pkg.type and pkg.type not in goat_types:
                    goat_types.append(pkg.type)
                if pkg.package.goat_type and pkg.package.goat_type.goat_type_name not in goat_type_names:
                    goat_type_names.append(pkg.package.goat_type.goat_type_name)

                desc_items = []
                for cuisine in [pkg.main_cuisine, pkg.sub_cuisine, pkg.side_cuisine1, pkg.side_cuisine2, pkg.side_cuisine3, pkg.side_cuisine4, pkg.side_cuisine5]:
                    if cuisine:
                        desc_items.append(cuisine)
                if pkg.box_type:
                    desc_items.append(f"Box ({pkg.box_type})")
                if pkg.upgrade:
                    desc_items.append(f"Up: {pkg.upgrade}")
                if pkg.beverage:
                    desc_items.append(f"Minuman: {pkg.beverage}")
                if pkg.souvenir:
                    desc_items.append(f"Souvenir: {pkg.souvenir}")
                if desc_items:
                    description_parts.append(', '.join(desc_items))

            events.append({
                'id': order.order_id,
                'title': order.customer_name,
                'start': start_str,
                'color': schedule_status_colors.get(order.schedule_status or 'UNSCHEDULED', '#6c757d'),
                'extendedProps': {
                    'order_id': order.order_id,
                    'customer_name': order.customer_name,
                    'area_name': order.regional.area_name,
                    'status': order.order_status,
                    'total_order': str(order.total_order),
                    'cs': order.cs or '-',
                    'time_arrival': order.time_arrival or '',
                    'customer_address': order.customer_address or '',
                    'driver': order.driver or '',
                    'departure_time': order.departure_time or '00:00',
                    'schedule_status': order.schedule_status or 'UNSCHEDULED',
                    'product_name': ' | '.join(product_list) if product_list else '-',
                    'description': ' | '.join(description_parts) if description_parts else '-',
                    'quantity': quantity_total,
                    'goat_type': ' - '.join(f"{t} - {n}" for t, n in zip(goat_types, goat_type_names)) if goat_types and goat_type_names else (', '.join(goat_types) if goat_types else '-'),
                    'leftover_food': order.orderleftoverfood_set.values_list('leftover_food', flat=True).first() or '',
                }
            })
        except Exception as e:
            print(f"ERROR processing order {order.order_id}: {e}")
            continue

    return JsonResponse(events, safe=False)


@login_required(login_url='/login/')
def jadwal_save(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        if not request.user.is_superuser:
            auth = Auth.objects.filter(user_id=request.user.user_id, menu_id='JADWAL').first()
            if not auth or not auth.edit:
                return JsonResponse({'success': False, 'error': 'Tidak memiliki akses edit'}, status=403)

        data = json.loads(request.body)
        order = Order.objects.get(order_id=order_id)
        driver = data.get('driver', '').strip()
        departure_time = data.get('departure_time', '00:00')
        schedule_status = data.get('schedule_status', 'UNSCHEDULED')

        order.driver = driver
        order.departure_time = departure_time
        order.schedule_status = schedule_status
        order.save()

        leftover_food = data.get('leftover_food', '')
        if leftover_food is not None:
            first_package = OrderPackage.objects.filter(order=order).first()
            if first_package:
                leftover_obj, created = OrderLeftoverFood.objects.get_or_create(
                    order=order,
                    package=first_package.package,
                    defaults={'leftover_food': leftover_food, 'entry_date': timezone.now(), 'entry_by': request.user.username}
                )
                if not created:
                    leftover_obj.leftover_food = leftover_food
                    leftover_obj.update_by = request.user.username
                    leftover_obj.save()

        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='/login/')
def jadwal_reminders(request):
    today = date.today()
    now = dt.datetime.now()
    current_time = now.strftime('%H:%M')

    areas = AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True)
    active_orders = Order.objects.filter(
        delivery_date__date=today,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])

    reminders = []

    for order in active_orders:
        order_id = order.order_id
        cust = order.customer_name or '-'
        departure = str(order.departure_time or '00:00')
        status = order.schedule_status or 'UNSCHEDULED'

        if not order.driver or not str(order.driver).strip():
            reminders.append({
                'type': 'NO_DRIVER',
                'message': f'Driver belum ditentukan untuk pesanan {order_id} ({cust})',
                'order_id': order_id,
            })

        if status == 'UNSCHEDULED':
            reminders.append({
                'type': 'UNSCHEDULED',
                'message': f'Pesanan {order_id} ({cust}) belum dijadwalkan',
                'order_id': order_id,
            })

        if status == 'PACKING' and departure < current_time:
            reminders.append({
                'type': 'PACKING_OVERDUE',
                'message': f'Packing pesanan {order_id} ({cust}) belum selesai',
                'order_id': order_id,
            })

        if status not in ('ON_DELIVERY', 'COMPLETED', 'CANCELLED') and departure < current_time:
            reminders.append({
                'type': 'DELIVERY_OVERDUE',
                'message': f'Pengiriman pesanan {order_id} ({cust}) terlambat',
                'order_id': order_id,
            })

        if status == 'SCHEDULED' and departure < current_time:
            reminders.append({
                'type': 'SCHEDULED_OVERDUE',
                'message': f'Pesanan {order_id} ({cust}) masih Scheduled tetapi jam sudah lewat',
                'order_id': order_id,
            })

        if status not in ('UNSCHEDULED', 'COMPLETED', 'CANCELLED') and departure > current_time:
            dep_h, dep_m = map(int, departure.split(':'))
            cur_h, cur_m = map(int, current_time.split(':'))
            diff_min = (dep_h * 60 + dep_m) - (cur_h * 60 + cur_m)
            if diff_min <= 60:
                reminders.append({
                    'type': 'DEPARTURE_SOON',
                    'message': f'Pesanan {order_id} ({cust}) berangkat dalam {diff_min} menit',
                    'order_id': order_id,
                })

    return JsonResponse({'reminders': reminders, 'count': len(reminders)})


@login_required(login_url='/login/')
@role_required(allowed_roles='JADWAL')
def jadwal_export_excel(request):
    start = request.GET.get('start', '').split('T')[0]
    end = request.GET.get('end', '').split('T')[0]
    filter_branch_list = request.GET.getlist('branch', [])
    filter_branch_list = [b for b in filter_branch_list if b and b != 'all']
    status = request.GET.get('status', 'all')
    driver_filter = request.GET.get('driver', '').strip()

    areas = AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True)
    orders = Order.objects.filter(
        delivery_date__date__gte=start,
        delivery_date__date__lte=end,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])

    if filter_branch_list:
        orders = orders.filter(regional_id__in=filter_branch_list)
    if status != 'all':
        orders = orders.filter(schedule_status=status)
    if driver_filter:
        orders = orders.filter(driver__icontains=driver_filter)
    orders = orders.order_by('delivery_date', 'departure_time')

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Jadwal Pesanan')

    title_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'align': 'center', 'valign': 'vcenter'
    })
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#FF8C42', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 12
    })
    cell_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'font_size': 12
    })
    center_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'align': 'center', 'font_size': 12
    })
    nama_pemesan_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'font_size': 12,
        'bg_color': '#FFFF00'
    })
    sisa_masakan_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'font_size': 12,
        'font_color': '#FF0000'
    })
    total_label_format = workbook.add_format({
        'bold': True, 'border': 1, 'valign': 'vcenter', 'font_size': 12
    })
    total_number_format = workbook.add_format({
        'bold': True, 'border': 1, 'valign': 'vcenter', 'align': 'center', 'font_size': 12,
        'bg_color': '#FFFF00'
    })

    columns = [
        ('No.', 5),
        ('Driver', 18),
        ('Jenis Kambing', 20),
        ('Jumlah Kambing', 15),
        ('Hari & Tanggal Kirim', 22),
        ('Masakan & Menu Olahan', 35),
        ('Jumlah Box', 12),
        ('Nama Pemesan', 25),
        ('Sisa Masakan', 20),
        ('Jam Berangkat', 14),
        ('Jam Tiba', 12),
        ('Cabang', 20),
        ('Alamat', 30),
    ]

    hari = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad']
    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    worksheet.merge_range(0, 0, 0, len(columns) - 1, 'JADWAL PESANAN', title_format)
    date_label = f'{start} s/d {end}' if start and end else 'Semua'
    worksheet.merge_range(1, 0, 1, len(columns) - 1, f'Periode: {date_label}', workbook.add_format({'align': 'center', 'font_size': 12}))

    for col_idx, (col_name, col_width) in enumerate(columns):
        worksheet.write(3, col_idx, col_name, header_format)
        worksheet.set_column(col_idx, col_idx, col_width)

    row = 4
    grand_total_kambing = 0
    grand_total_box = 0
    for no, order in enumerate(orders.select_related('regional'), 1):
        if not order.regional:
            continue

        packages = OrderPackage.objects.filter(order=order).select_related('category', 'package', 'package__goat_type')
        product_parts = []
        description_parts = []
        quantity_total = 0
        goat_types = []
        goat_type_names = []
        total_box = 0
        for pkg in packages:
            category_clean = re.sub(r'\s*\([^)]*\)', '', pkg.category.category_name) if pkg.category else ''
            product_name = f"{category_clean} - {pkg.package.package_name}".strip(' -')
            product_parts.append(product_name)
            quantity_total += (pkg.package.quantity or 0) * (pkg.quantity or 1)
            if pkg.type and pkg.type not in goat_types:
                goat_types.append(pkg.type)
            if pkg.package.goat_type and pkg.package.goat_type.goat_type_name not in goat_type_names:
                goat_type_names.append(pkg.package.goat_type.goat_type_name)
            total_box += (pkg.box_qty or 0) * (pkg.quantity or 1)

            desc_items = []
            for cuisine in [pkg.main_cuisine, pkg.sub_cuisine, pkg.side_cuisine1, pkg.side_cuisine2, pkg.side_cuisine3, pkg.side_cuisine4, pkg.side_cuisine5]:
                if cuisine:
                    desc_items.append(cuisine)
            if pkg.box_type:
                desc_items.append(f"Box ({pkg.box_type})")
            if pkg.upgrade:
                desc_items.append(f"Up: {pkg.upgrade}")
            if pkg.beverage:
                desc_items.append(f"Minuman: {pkg.beverage}")
            if pkg.souvenir:
                desc_items.append(f"Souvenir: {pkg.souvenir}")
            if desc_items:
                description_parts.append(', '.join(desc_items))

        if quantity_total == 0:
            goat_type_str = '-'
            jumlah_kambing = 0
        else:
            goat_type_str = ' - '.join(f"{t} - {n}" for t, n in zip(goat_types, goat_type_names)) if goat_types and goat_type_names else (', '.join(goat_types) if goat_types else '-')
            jumlah_kambing = quantity_total

        delivery = order.delivery_date
        if delivery:
            day_name = hari[delivery.weekday()]
            tanggal = f"{day_name}, {delivery.day} {bulan[delivery.month - 1]} {delivery.year}"
        else:
            tanggal = '-'

        box_addon_total = OrderPackageAddon.objects.filter(
            order=order,
            equipment__tipe='Box Paket'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        total_box += box_addon_total

        leftover = OrderLeftoverFood.objects.filter(order=order).values_list('leftover_food', flat=True).first() or '-'

        grand_total_kambing += jumlah_kambing
        grand_total_box += total_box

        dt_val = str(order.departure_time or '00:00')
        ta_val = ''
        if order.time_arrival:
            try:
                parts = order.time_arrival.split(':')
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                h = (h - 1 + 24) % 24
                ta_val = f"{h:02d}:{m:02d}"
            except (ValueError, IndexError):
                ta_val = '-'
        else:
            ta_val = '-'

        worksheet.write_number(row, 0, no, center_format)
        worksheet.write_string(row, 1, order.driver or '-', cell_format)
        worksheet.write_string(row, 2, goat_type_str, cell_format)
        worksheet.write_number(row, 3, jumlah_kambing, center_format)
        worksheet.write_string(row, 4, tanggal, cell_format)
        worksheet.write_string(row, 5, ' | '.join(description_parts) if description_parts else '-', cell_format)
        worksheet.write_number(row, 6, total_box, center_format)
        worksheet.write_string(row, 7, order.customer_name or '-', nama_pemesan_format)
        worksheet.write_string(row, 8, leftover, sisa_masakan_format)
        worksheet.write_string(row, 9, dt_val, center_format)
        worksheet.write_string(row, 10, ta_val, center_format)
        worksheet.write_string(row, 11, order.regional.area_name or '-', cell_format)
        worksheet.write_string(row, 12, order.customer_address or '-', cell_format)
        row += 1

    worksheet.write_number(row, 3, grand_total_kambing, total_number_format)
    worksheet.write_number(row, 6, grand_total_box, total_number_format)
    row += 1

    workbook.close()
    output.seek(0)

    period_str = f'{start}_sd_{end}' if start and end else 'Semua'
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Jadwal_Pesanan_{period_str}.xlsx"'
    return response


@login_required(login_url='/login/')
@role_required(allowed_roles='JADWAL')
def jadwal_print_daily(request):
    start = request.GET.get('start', '').split('T')[0]
    end = request.GET.get('end', '').split('T')[0]
    filter_branch_list = request.GET.getlist('branch', [])
    filter_branch_list = [b for b in filter_branch_list if b and b != 'all']
    status = request.GET.get('status', 'all')
    driver_filter = request.GET.get('driver', '').strip()

    areas = AreaUser.objects.filter(user_id=request.user.user_id).values_list('area_id', flat=True)
    orders = Order.objects.filter(
        delivery_date__date__gte=start,
        delivery_date__date__lte=end,
        regional_id__in=areas
    ).exclude(order_status__in=['PENDING', 'DRAFT', 'BATAL'])

    if filter_branch_list:
        orders = orders.filter(regional_id__in=filter_branch_list)
    if status != 'all':
        orders = orders.filter(schedule_status=status)
    if driver_filter:
        orders = orders.filter(driver__icontains=driver_filter)
    orders = orders.order_by('delivery_date', 'departure_time')

    hari = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad']
    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    schedule_data = []
    for no, order in enumerate(orders.select_related('regional'), 1):
        if not order.regional:
            continue

        packages = OrderPackage.objects.filter(order=order).select_related('category', 'package', 'package__goat_type')
        product_parts = []
        description_parts = []
        quantity_total = 0
        goat_types = []
        goat_type_names = []
        total_box = 0
        for pkg in packages:
            category_clean = re.sub(r'\s*\([^)]*\)', '', pkg.category.category_name) if pkg.category else ''
            product_name = f"{category_clean} - {pkg.package.package_name}".strip(' -')
            product_parts.append(product_name)
            quantity_total += (pkg.package.quantity or 0) * (pkg.quantity or 1)
            if pkg.type and pkg.type not in goat_types:
                goat_types.append(pkg.type)
            if pkg.package.goat_type and pkg.package.goat_type.goat_type_name not in goat_type_names:
                goat_type_names.append(pkg.package.goat_type.goat_type_name)
            total_box += (pkg.box_qty or 0) * (pkg.quantity or 1)

            desc_items = []
            for cuisine in [pkg.main_cuisine, pkg.sub_cuisine, pkg.side_cuisine1, pkg.side_cuisine2, pkg.side_cuisine3, pkg.side_cuisine4, pkg.side_cuisine5]:
                if cuisine:
                    desc_items.append(cuisine)
            if pkg.box_type:
                desc_items.append(f"Box ({pkg.box_type})")
            if pkg.upgrade:
                desc_items.append(f"Up: {pkg.upgrade}")
            if pkg.beverage:
                desc_items.append(f"Minuman: {pkg.beverage}")
            if pkg.souvenir:
                desc_items.append(f"Souvenir: {pkg.souvenir}")
            if desc_items:
                description_parts.append(', '.join(desc_items))

        if quantity_total == 0:
            goat_type_str = '-'
            jumlah_kambing = 0
        else:
            goat_type_str = ' - '.join(f"{t} - {n}" for t, n in zip(goat_types, goat_type_names)) if goat_types and goat_type_names else (', '.join(goat_types) if goat_types else '-')
            jumlah_kambing = quantity_total

        delivery = order.delivery_date
        if delivery:
            day_name = hari[delivery.weekday()]
            tanggal = f"{day_name}, {delivery.day} {bulan[delivery.month - 1]} {delivery.year}"
        else:
            tanggal = '-'

        box_addon_total = OrderPackageAddon.objects.filter(
            order=order,
            equipment__tipe='Box Paket'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        total_box += box_addon_total

        leftover = OrderLeftoverFood.objects.filter(order=order).values_list('leftover_food', flat=True).first() or '-'

        dt_val = str(order.departure_time or '00:00')
        ta_val = ''
        if order.time_arrival:
            try:
                parts = order.time_arrival.split(':')
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                h = (h - 1 + 24) % 24
                ta_val = f"{h:02d}:{m:02d}"
            except (ValueError, IndexError):
                ta_val = '-'
        else:
            ta_val = '-'

        schedule_status_labels = {
            'UNSCHEDULED': 'Belum Dijadwalkan', 'SCHEDULED': 'Sudah Dijadwalkan',
            'COOKING': 'Sedang Produksi', 'PACKING': 'Sedang Packing',
            'READY': 'Siap Kirim', 'ON_DELIVERY': 'Dalam Pengiriman',
            'COMPLETED': 'Selesai', 'CANCELLED': 'Dibatalkan'
        }

        schedule_data.append({
            'no': no,
            'driver': order.driver or '-',
            'goat_type': goat_type_str,
            'jumlah_kambing': jumlah_kambing,
            'tanggal': tanggal,
            'masakan': ' | '.join(description_parts) if description_parts else '-',
            'jumlah_box': total_box,
            'customer_name': order.customer_name or '-',
            'leftover_food': leftover,
            'departure_time': dt_val,
            'arrival_time': ta_val,
            'cabang': order.regional.area_name or '-',
            'alamat': order.customer_address or '-',
            'schedule_status': schedule_status_labels.get(order.schedule_status or 'UNSCHEDULED', '-'),
        })

    total_kambing = sum(item['jumlah_kambing'] for item in schedule_data)
    total_box_sum = sum(item['jumlah_box'] for item in schedule_data)

    periode = f'{start} s/d {end}' if start and end else 'Semua'
    print_date = timezone.now().strftime('%d %m %Y %H:%M')

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 7

    today_str = date.today().strftime('%Y-%m-%d')
    if start and end:
        filename = f'Jadwal_Harian_{start}_{end}.pdf'
    else:
        filename = f'Jadwal_Harian_{today_str}.pdf'
    pdf_file = canvas.Canvas(filename, pagesize=landscape(A4))

    page_w, page_h = landscape(A4)
    margin_x = 20
    margin_top = 20

    y = page_h - margin_top

    title = "JADWAL PESANAN HARIAN"
    pdf_file.setFont("Helvetica-Bold", 13)
    title_w = pdf_file.stringWidth(title, "Helvetica-Bold", 13)
    pdf_file.drawString((page_w - title_w) / 2, y - 8, title)

    pdf_file.setFont("Helvetica", 8)
    info_text = f"Periode: {periode}  |  Dicetak: {print_date}  |  Total: {len(schedule_data)} pesanan  |  Jumlah Kambing: {total_kambing}  |  Jumlah Box: {total_box_sum}"
    info_w = pdf_file.stringWidth(info_text, "Helvetica", 8)
    pdf_file.drawString((page_w - info_w) / 2, y - 20, info_text)

    pdf_file.setStrokeColor(HexColor('#FF8C42'))
    pdf_file.setLineWidth(2)
    pdf_file.line(margin_x, y - 28, page_w - margin_x, y - 28)

    y = y - 40

    col_headers = ['No.', 'Driver', 'Jenis Kambing', 'Jumlah\nKambing', 'Hari & Tanggal\nKirim', 'Masakan &\nMenu Olahan', 'Jumlah\nBox', 'Nama\nPemesan', 'Sisa\nMasakan', 'Jam\nBerangkat', 'Jam\nTiba', 'Cabang', 'Alamat']
    col_widths = [22, 57, 70, 37, 83, 122, 33, 78, 65, 44, 37, 65, 88]
    row_height_header = 28

    pdf_file.setFillColor(HexColor('#FF8C42'))
    pdf_file.rect(margin_x, y - row_height_header, page_w - 2 * margin_x, row_height_header, fill=1, stroke=0)
    pdf_file.setFillColor(HexColor('#FFFFFF'))
    pdf_file.setFont("Helvetica-Bold", 6.5)

    x = margin_x
    for i, (header, w) in enumerate(zip(col_headers, col_headers and col_widths)):
        lines = header.split('\n')
        for li, line in enumerate(lines):
            tw = pdf_file.stringWidth(line, "Helvetica-Bold", 6.5)
            pdf_file.drawString(x + (w - tw) / 2, y - 10 - li * 8, line)
        x += col_widths[i]

    pdf_file.setFillColor(HexColor('#000000'))
    y -= row_height_header

    row_height = 18
    font_size = 6.5

    def draw_row(data_row, y_pos):
        x = margin_x
        values = [
            str(data_row['no']),
            data_row['driver'],
            data_row['goat_type'],
            str(data_row['jumlah_kambing']),
            data_row['tanggal'],
            data_row['masakan'],
            str(data_row['jumlah_box']),
            data_row['customer_name'],
            data_row['leftover_food'],
            data_row['departure_time'],
            data_row['arrival_time'],
            data_row['cabang'],
            data_row['alamat'],
        ]
        aligns = ['center', 'left', 'left', 'center', 'left', 'left', 'center', 'left', 'left', 'center', 'center', 'left', 'left']

        max_lines = 1
        for i, (val, w) in enumerate(zip(values, col_widths)):
            lines = simpleSplit(val, 'Helvetica', font_size, w - 4)
            if len(lines) > max_lines:
                max_lines = len(lines)

        actual_row_h = max(row_height, 6 + max_lines * 9)

        if int(data_row['no']) % 2 == 0:
            pdf_file.setFillColor(HexColor('#F9F9F9'))
            pdf_file.rect(margin_x, y_pos - actual_row_h, page_w - 2 * margin_x, actual_row_h, fill=1, stroke=0)
            pdf_file.setFillColor(HexColor('#000000'))

        pdf_file.setStrokeColor(HexColor('#DDDDDD'))
        pdf_file.setLineWidth(0.5)
        pdf_file.rect(margin_x, y_pos - actual_row_h, page_w - 2 * margin_x, actual_row_h, fill=0, stroke=1)

        pdf_file.setFont("Helvetica", font_size)
        x = margin_x
        for i, (val, w) in enumerate(zip(values, col_widths)):
            lines = simpleSplit(val, 'Helvetica', font_size, w - 4)
            for li, line in enumerate(lines):
                if aligns[i] == 'center':
                    tw = pdf_file.stringWidth(line, 'Helvetica', font_size)
                    pdf_file.drawString(x + (w - tw) / 2, y_pos - 10 - li * 9, line)
                elif aligns[i] == 'right':
                    tw = pdf_file.stringWidth(line, 'Helvetica', font_size)
                    pdf_file.drawString(x + w - tw - 2, y_pos - 10 - li * 9, line)
                else:
                    pdf_file.drawString(x + 2, y_pos - 10 - li * 9, line)
            x += col_widths[i]

        return y_pos - actual_row_h

    for data_row in schedule_data:
        needed = max(row_height, 24)
        if y - needed < 50:
            pdf_file.setFont("Helvetica-Oblique", 7)
            pdf_file.drawString(margin_x, 30, f"Dicetak oleh: Sahabat Aqiqah - {print_date}")
            pdf_file.showPage()
            pdf_file.setFont("Helvetica-Bold", 10)
            pdf_file.drawString(margin_x, page_h - 30, "JADWAL PESANAN HARIAN (lanjutan)")
            pdf_file.setFont("Helvetica", 8)
            pdf_file.drawString(margin_x, page_h - 42, f"Periode: {periode}")
            y = page_h - 55

            pdf_file.setFillColor(HexColor('#FF8C42'))
            pdf_file.rect(margin_x, y - row_height_header, page_w - 2 * margin_x, row_height_header, fill=1, stroke=0)
            pdf_file.setFillColor(HexColor('#FFFFFF'))
            pdf_file.setFont("Helvetica-Bold", 6.5)
            x = margin_x
            for i, (header, w) in enumerate(zip(col_headers, col_widths)):
                lines = header.split('\n')
                for li, line in enumerate(lines):
                    tw = pdf_file.stringWidth(line, "Helvetica-Bold", 6.5)
                    pdf_file.drawString(x + (w - tw) / 2, y - 10 - li * 8, line)
                x += col_widths[i]
            pdf_file.setFillColor(HexColor('#000000'))
            y -= row_height_header

        y = draw_row(data_row, y)

    pdf_file.setFont("Helvetica-Oblique", 7)
    pdf_file.drawString(margin_x, 30, f"Dicetak oleh: Sahabat Aqiqah - {print_date}")

    pdf_file.save()

    result = open(filename, 'rb')
    response = FileResponse(result, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{filename}"'
    return response


@login_required(login_url='/login/')
def cleanup_pdf_info(request):
    if not request.user.is_superuser:
        has_access = Auth.objects.filter(
            user_id=request.user.user_id, menu_id='CLEANUP').exists()
        if not has_access:
            return JsonResponse({'error': 'Tidak memiliki akses'}, status=403)

    patterns = ['INVOICE_*.pdf', 'SURAT_JALAN_*.pdf', 'CHECKLIST_*.pdf', 'Jadwal_Harian_*.pdf']
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(settings.BASE_DIR, pattern)))

    file_names = [os.path.basename(f) for f in files]
    return JsonResponse({'count': len(file_names), 'files': file_names})


@login_required(login_url='/login/')
def cleanup_pdf(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not request.user.is_superuser:
        has_access = Auth.objects.filter(
            user_id=request.user.user_id, menu_id='CLEANUP').exists()
        if not has_access:
            return JsonResponse({'error': 'Tidak memiliki akses'}, status=403)

    patterns = ['INVOICE_*.pdf', 'SURAT_JALAN_*.pdf', 'CHECKLIST_*.pdf', 'Jadwal_Harian_*.pdf']
    deleted = 0
    errors = []
    for pattern in patterns:
        for filepath in glob.glob(os.path.join(settings.BASE_DIR, pattern)):
            try:
                os.remove(filepath)
                deleted += 1
            except Exception as e:
                errors.append(os.path.basename(filepath))

    return JsonResponse({'success': True, 'deleted': deleted, 'errors': errors})
