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
