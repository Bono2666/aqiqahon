import os
import re

from django import template


register = template.Library()


@register.filter
def filename(value):
    return os.path.basename(value.file.name)


@register.filter
def to_space(value):
    return value.replace('%20', ' ').replace('25', '')


MOBILE_RE = re.compile(r'Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini', re.IGNORECASE)


@register.filter
def is_mobile(request):
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
    return bool(MOBILE_RE.search(ua))
