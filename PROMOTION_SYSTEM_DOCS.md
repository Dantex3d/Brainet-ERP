# 📚 Brainet School Management System - Enhancement Documentation

## New Features & Updates

### 1. **School Deactivation & License Management** 🔒

#### Overview
Schools can now be deactivated when their license expires or is suspended. A deactivated school will be directed to a special page showing renewal options.

#### How It Works:
- **Deactivation**: When a school's license expires or is suspended, it is marked as `is_active=False`
- **Deactivated Page**: Users are redirected to `/schools/<school_id>/deactivated/` 
- **License Renewal Request**: Schools can request license renewal with a custom period (1, 2, or 3 years)
- **Superuser Approval**: Superusers can approve/reject renewal requests in the admin dashboard
- **Automatic Reactivation**: Upon approval, the school is reactivated and license expiry is extended

#### New Fields on School Model:
```python
license_status = CharField(['active', 'expired', 'suspended'])  # License status
license_expiry = DateField()  # When license expires
deactivated_at = DateTimeField()  # When school was deactivated
deactivation_reason = TextField()  # Why it was deactivated
```

#### Routes:
- `POST /schools/<school_id>/deactivate/` - Deactivate a school
- `GET /schools/<school_id>/deactivated/` - Deactivated school page
- `POST /schools/<school_id>/renew-license/` - Request license renewal
- `POST /license-renewal/<renewal_id>/approve/` - Approve renewal (superuser only)

---

### 2. **Student Promotion System** 🎓

#### Overview
Automatic end-of-year promotion system with intelligent class creation and stream management.

#### Promotion Logic:
```
Level 1 (Grade 10 East) → Level 2 (Grade 11 East) → Level 3 → Graduated
```

- **Level 1 to 2**: Students move to the next level
- **Level 2 to 3**: Students move to the next level  
- **Level 3 to Graduated**: Students are marked as graduated (removed from classes)
- **Stream Handling**: If a student is in "Grade 10 East", they automatically move to "Grade 11 East" (creates it if needed)

#### Features:

##### A. School-Wide Promotion
Promote all active students in the school at once:
- Route: `/promotion/school/`
- Promotes all students across all classes
- Creates missing classes automatically
- Graduates Level 3 students

##### B. Class-Specific Promotion
Promote all students in a specific class:
- Route: `/promotion/class/<class_id>/`
- Bulk promotes one class
- Useful for multi-class promotions

##### C. Individual Student Management
Promote, repeat, or drop individual students:
- Route: `/promotion/student/<student_id>/`
- **Promote**: Move to next level
- **Repeat**: Keep in same class for another year
- **Drop**: Remove from school with remarks

##### D. Promotion History
View all promotions with filtering:
- Route: `/promotion/history/`
- Filter by student name or status
- Tracks who promoted and when

#### New Models:

```python
# Student Promotion Record
StudentPromotion:
  - student: ForeignKey(Student)
  - from_class: ForeignKey(Class)
  - to_class: ForeignKey(Class)
  - from_stream: ForeignKey(Stream)
  - to_stream: ForeignKey(Stream)
  - status: [promoted, repeated, graduated, dropped]
  - remarks: TextField
  - promoted_by: ForeignKey(User)
  - promoted_at: DateTimeField
```

#### Promotion Service

A dedicated service (`schools/promotion_service.py`) handles all promotion logic:

```python
from schools.promotion_service import PromotionService

# Promote a single student
next_class, next_stream = PromotionService.get_next_class(
    current_class, 
    current_stream
)
promotion = PromotionService.promote_student(
    student, 
    next_class, 
    next_stream,
    promoted_by=user
)

# Promote entire class
stats = PromotionService.promote_class(class_obj, promoted_by=user)
# Returns: {promoted: 30, graduated: 5, failed: 0, total: 35}

# Promote entire school
stats = PromotionService.promote_school(school, promoted_by=user)

# Repeat a student
PromotionService.repeat_student(student, repeated_by=user, remarks="Low marks")

# Drop a student
PromotionService.drop_student(student, dropped_by=user, remarks="Left school")
```

#### Example: Automatic Class Creation

If you promote students from "Grade 10 East" to "Grade 11":
1. System checks if "Grade 11 East" exists
2. If NOT: Creates it with the same configuration
3. Student is automatically placed in the new class

This handles multi-level schools naturally!

#### Routes:
- `GET /promotion/center/` - Main promotion center
- `GET /promotion/class/<class_id>/` - Promote class (confirmation)
- `POST /promotion/class/<class_id>/` - Execute class promotion
- `GET /promotion/student/<student_id>/` - Individual student options
- `POST /promotion/student/<student_id>/` - Execute student action
- `GET /promotion/school/` - School-wide promotion (confirmation)
- `POST /promotion/school/` - Execute school-wide promotion
- `GET /promotion/history/` - View promotion history

---

### 3. **License Renewal Model**

```python
LicenseRenewal:
  - school: ForeignKey(School)
  - requested_by: ForeignKey(User)
  - requested_at: DateTimeField
  - renewal_period_days: IntegerField (default: 365)
  - status: [pending, approved, rejected]
  - processed_at: DateTimeField
  - processed_by: ForeignKey(User)
  - notes: TextField
```

---

## Setup Instructions

### 1. **Create Migrations**

```bash
python manage.py makemigrations schools
python manage.py migrate
```

### 2. **Add to Admin (Optional)**

```python
# schools/admin.py
from .models import StudentPromotion, LicenseRenewal

admin.site.register(StudentPromotion)
admin.site.register(LicenseRenewal)
```

### 3. **Update Middleware (Optional)**

To automatically redirect deactivated schools:

```python
# brainet/middleware.py
from django.shortcuts import redirect
from schools.models import School

class SchoolDeactivationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if hasattr(request.user, 'dos_profile'):
            school = request.user.dos_profile.school
            if not school.is_active:
                return redirect('school_deactivated', school_id=school.id)
        
        return self.get_response(request)
```

Add to `MIDDLEWARE` in settings.py:
```python
MIDDLEWARE = [
    ...
    'brainet.middleware.SchoolDeactivationMiddleware',
    ...
]
```

---

## Usage Examples

### Example 1: End-of-Year Promotion

```python
from schools.promotion_service import PromotionService
from schools.models import School
from django.contrib.auth import get_user_model

school = School.objects.get(id=1)
user = get_user_model().objects.get(username='admin')

# Promote entire school
stats = PromotionService.promote_school(school, promoted_by=user)
print(f"Promoted: {stats['promoted']}, Graduated: {stats['graduated']}")
```

### Example 2: Handle Individual Student

```python
student = Student.objects.get(id=123)

# Check where they'll go
next_class, next_stream = PromotionService.get_next_class(
    student.current_class,
    student.stream
)

if next_class is None:
    print("Student will graduate")
else:
    print(f"Student moves to {next_class.name} - {next_stream.name}")
```

### Example 3: Manual Stream Creation

```python
class_obj = Class.objects.get(id=5)  # Grade 11
stream = PromotionService.get_or_create_stream(class_obj, "East")
# Creates "Grade 11 East" if it doesn't exist
```

---

## Templates Created

1. **school_deactivated.html** - Deactivated school info page with renewal options
2. **deactivate_confirm.html** - Confirmation before deactivating a school
3. **promotion_center.html** - Main hub for all promotion operations
4. **promotion_history.html** - View all promotions with filters
5. **promote_school_confirm.html** - Confirm school-wide promotion
6. **promote_class_confirm.html** - Confirm class promotion
7. **promote_student.html** - Individual student promotion options

---

## Database Changes

Run these commands to apply changes:

```bash
# Create migrations
python manage.py makemigrations schools

# Review migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate
```

---

## Important Notes

⚠️ **Before Running Promotion:**
1. Back up your database
2. Review student records to ensure accuracy
3. Test on a small class first
4. Verify that next-level classes exist (or they'll be auto-created)

✅ **System Handles:**
- Creating missing classes automatically
- Maintaining stream relationships
- Tracking who promoted when
- Preventing duplicate promotions

❌ **Cannot Undo:**
- Promotions are recorded in StudentPromotion table
- Manual rollback required if errors occur
- Always have backups!

---

## Future Enhancements

Potential improvements:
- [ ] Bulk import promotions from CSV/Excel
- [ ] Promotion undo/rollback feature
- [ ] Email notifications on promotion
- [ ] Promotion reports and analytics
- [ ] AJAX-based promotion with progress bar
- [ ] Conditional promotion based on grades
- [ ] Integration with report cards

---

## Support

For issues or questions:
1. Check the promotion history to audit actions
2. Review StudentPromotion records in admin
3. Check system logs for errors
4. Contact development team

---

**Last Updated:** June 2026
**Version:** 1.0
