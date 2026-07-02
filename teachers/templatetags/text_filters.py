from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, old, new):
    if value is None:
        return ''
    try:
        return str(value).replace(old, new)
    except Exception:
        return value


@register.filter(name='get_school_logo_url')
def get_school_logo_url_filter(school):
    from schools.views import get_school_logo_url

    return get_school_logo_url(school)
