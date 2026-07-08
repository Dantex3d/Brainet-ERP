from django import template

register = template.Library()


@register.filter(name='replace')
def replace(value, arg):
    if value is None or arg is None:
        return ''
    try:
        old, new = arg.split(',')
        return str(value).replace(old, new)
    except ValueError:
        return value
    except Exception:
        return value


@register.filter(name='get_school_logo_url')
def get_school_logo_url_filter(school):
    from schools.views import get_school_logo_url

    return get_school_logo_url(school)


@register.filter(name='get_item')
def get_item(value, key, default=''):
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)
