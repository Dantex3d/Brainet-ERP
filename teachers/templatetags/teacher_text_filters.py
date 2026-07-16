from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()

@register.filter(name='replace')
def replace(value, old, new):
    if value is None:
        return ''
    try:
        return str(value).replace(old, new)
    except Exception:
        return value


@register.filter(name='get_school_logo_url', is_safe=False)
def get_school_logo_url(school):
    """Return the URL for the school's logo.

    If no logo is available, return an empty string.
    """
    if not school:
        return ""

    logo = getattr(school, 'logo', None)

    if not logo:
        return ""

    try:
        url = logo.url
        return url
    except Exception:
        return ""
