import os
import django

# 👇 IMPORTANT: set your project settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainet.settings")

# 👇 initialize Django BEFORE importing models
django.setup()

from django.db.models import Count
from schools.models import Class


duplicates = Class.objects.values('school_id', 'name', 'level') \
    .annotate(c=Count('id')) \
    .filter(c__gt=1)

for d in duplicates:
    objs = Class.objects.filter(
        school_id=d['school_id'],
        name=d['name'],
        level=d['level']
    ).order_by('id')

    if objs.exists():
        objs.exclude(id=objs.first().id).delete()

print("DONE CLEANING DUPLICATES")