# 🚀 Setup Guide - Promotion System & School Deactivation

## Quick Start - Next Steps

After pulling these changes, follow these steps to activate the new features:

### Step 1: Create & Apply Migrations

```bash
# Terminal: Navigate to project root
cd c:\Users\DANTEX3D\Desktop\Brainet Analytics\brainet

# Create migrations for new models
python manage.py makemigrations schools

# Apply migrations to database
python manage.py migrate
```

**Expected output:**
```
Running migrations:
  Applying schools.0001_initial...
  Applying schools.0002_license_and_promotion...OK
```

### Step 2: Update Admin Interface (Optional but Recommended)

Add the new models to Django admin for easy management:

```python
# Edit schools/admin.py and add:

from .models import StudentPromotion, LicenseRenewal

@admin.register(StudentPromotion)
class StudentPromotionAdmin(admin.ModelAdmin):
    list_display = ('student', 'from_class', 'to_class', 'status', 'promoted_at')
    list_filter = ('status', 'promoted_at', 'school')
    search_fields = ('student__name', 'student__admission_number')
    readonly_fields = ('promoted_at',)

@admin.register(LicenseRenewal)
class LicenseRenewalAdmin(admin.ModelAdmin):
    list_display = ('school', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('school__name',)
    readonly_fields = ('requested_at', 'processed_at')
```

### Step 3: Test the Features

#### Test Deactivation Flow:
1. Go to superuser dashboard
2. Click on a school
3. Click "Deactivate School"
4. Verify you're redirected to the deactivation page
5. Request license renewal
6. Verify pending renewal appears

#### Test Promotion Flow:
1. Go to DOS Dashboard
2. Click "Student Promotion Center"
3. Select a class to promote
4. Verify student count
5. Review students to be promoted
6. Confirm promotion
7. Check promotion history

### Step 4: Configure (Optional)

#### Add School Deactivation Middleware (Automatic Redirect)

Edit `brainet/settings.py`:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'schools.middleware.SchoolDeactivationMiddleware',  # Add this
]
```

Create `schools/middleware.py`:

```python
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

class SchoolDeactivationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is from a deactivated school
        if hasattr(request.user, 'dos_profile') and request.user.is_authenticated:
            school = request.user.dos_profile.school
            # Skip for deactivation/renewal pages
            if (not school.is_active and 
                'deactivated' not in request.path and
                'renew' not in request.path):
                return redirect('school_deactivated', school_id=school.id)
        
        return self.get_response(request)
```

### Step 5: Update Navigation (Optional)

Add links to promotion center in your DOS dashboard or navigation menu:

```html
<!-- Add to DOS Dashboard -->
<a href="{% url 'promotion_center' %}" class="btn btn-primary">
    🎓 Student Promotion
</a>
```

---

## File Summary

### New Files Created:
- ✅ `schools/promotion_service.py` - Core promotion logic
- ✅ `brainet/templates/schools/school_deactivated.html` - Deactivated school page
- ✅ `brainet/templates/schools/deactivate_confirm.html` - Deactivation confirmation
- ✅ `brainet/templates/schools/request_renewal.html` - License renewal request
- ✅ `brainet/templates/schools/promotion_center.html` - Main promotion hub
- ✅ `brainet/templates/schools/promotion_history.html` - Promotion records
- ✅ `brainet/templates/schools/promote_school_confirm.html` - School-wide promotion
- ✅ `brainet/templates/schools/promote_class_confirm.html` - Class promotion
- ✅ `brainet/templates/schools/promote_student.html` - Individual promotion
- ✅ `PROMOTION_SYSTEM_DOCS.md` - Complete documentation

### Modified Files:
- ✅ `schools/models.py` - Added School license fields, StudentPromotion, LicenseRenewal models
- ✅ `schools/views.py` - Added deactivation, renewal, and promotion views
- ✅ `schools/urls.py` - Added new URL patterns

---

## Key Features at a Glance

### 🔒 School Deactivation
- Deactivate schools when licenses expire
- Request renewal with custom periods (1/2/3 years)
- Superuser approval workflow
- Automatic reactivation on approval

### 🎓 Student Promotion
- End-of-year bulk promotion (entire school or by class)
- Intelligent class creation (Grade 10 East → Grade 11 East)
- Support for Level 1 → 2 → 3 → Graduation
- Individual student management:
  - ✓ Promote
  - 🔄 Repeat year
  - ✕ Drop from school
- Complete promotion history with audit trail

### 📊 Reporting
- Promotion statistics
- History filtering and search
- Automatic tracking of promotions

---

## Troubleshooting

### Issue: Migration fails
```bash
# Check migration status
python manage.py showmigrations schools

# View specific migration
python manage.py sqlmigrate schools 0001

# Reset (only in development!)
python manage.py migrate schools zero
python manage.py makemigrations schools
python manage.py migrate
```

### Issue: Classes not created automatically
- Ensure reference class has proper naming convention
- Check logs for errors
- Manually create missing classes in admin

### Issue: Deactivated users still see full interface
- Apply middleware from Step 4
- Or manually check `school.is_active` in templates
- Clear browser cache

---

## Database Backup (Important!)

Before running promotions, backup your database:

```bash
# Windows
python manage.py dumpdata > backup.json

# Restore if needed
python manage.py loaddata backup.json
```

---

## API Usage Examples

### Example 1: Promote All Students in School
```python
from schools.promotion_service import PromotionService
from schools.models import School
from django.contrib.auth import get_user_model

school = School.objects.get(id=1)
user = get_user_model().objects.get(username='admin')

stats = PromotionService.promote_school(school, promoted_by=user)
print(f"✓ Promoted: {stats['promoted']}")
print(f"🎓 Graduated: {stats['graduated']}")
print(f"✕ Failed: {stats['failed']}")
```

### Example 2: Check Student's Next Class
```python
from schools.promotion_service import PromotionService
from students.models import Student

student = Student.objects.get(id=123)
next_class, next_stream = PromotionService.get_next_class(
    student.current_class,
    student.stream
)

if next_class:
    print(f"{student.name} → {next_class.name} {next_stream.name if next_stream else ''}")
else:
    print(f"{student.name} → Graduated 🎓")
```

### Example 3: Create Next Level Classes if Missing
```python
from classes.models import Class

classes_to_create = [
    ('Grade 11 East', 11),
    ('Grade 11 West', 11),
    ('Grade 12 East', 12),
]

for name, level in classes_to_create:
    Class.objects.get_or_create(
        school_id=1,
        level=level,
        defaults={'name': name}
    )
```

---

## Performance Tips

For schools with 1000+ students:
1. Use "Promote by Class" instead of school-wide
2. Split promotion into multiple batches
3. Run during off-hours
4. Monitor database query logs

---

## Next Steps

1. ✅ Run migrations
2. ✅ Test promotion on a small class
3. ✅ Configure middleware (optional)
4. ✅ Train staff on new features
5. ✅ Plan end-of-year promotion schedule

---

## Support & Questions

For detailed documentation, see: **PROMOTION_SYSTEM_DOCS.md**

For code examples, check: **schools/promotion_service.py**

---

**Version:** 1.0  
**Last Updated:** June 2026  
**Status:** Ready for Production ✅
