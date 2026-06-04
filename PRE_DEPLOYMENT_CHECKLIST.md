# ✅ Pre-Deployment Testing Checklist

Before deploying to PythonAnywhere, ensure all features work locally.

## Local Testing

### 1. Database Setup ✓
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```
- [ ] No migration errors
- [ ] Superuser created successfully
- [ ] Static files collected

### 2. Run Development Server ✓
```bash
python manage.py runserver
```
- [ ] Server starts without errors
- [ ] No 500 errors on startup
- [ ] Console shows "Starting development server"

### 3. Landing Page Tests
- [ ] Navigate to `http://127.0.0.1:8000/`
- [ ] Landing page loads
- [ ] "View Features Demo" button visible
- [ ] "Login to System" button works
- [ ] "Register School" button visible

### 4. Features Demo Page
- [ ] Navigate to `http://127.0.0.1:8000/features-demo/`
- [ ] Page loads completely
- [ ] All sections visible (Class Management, License, Promotion)
- [ ] Demo modals open/close properly
- [ ] Links work (Dashboard, Promotion Center)
- [ ] Styling renders correctly

### 5. Authentication Tests
- [ ] Login page loads at `/login/`
- [ ] Login with superuser works
- [ ] Dashboard accessible after login
- [ ] Logout works
- [ ] Redirects to login for protected pages

### 6. Class Management
- [ ] Navigate to "Add Class"
- [ ] Form loads
- [ ] Can create class with stream
- [ ] Class appears in list
- [ ] Can view class details

### 7. Promotion System
- [ ] Navigate to Promotion Center
- [ ] All options visible (School, Class, Individual)
- [ ] Promotion history loads
- [ ] Can view student promotion page
- [ ] History filtering works

### 8. School Deactivation
- [ ] Admin can deactivate a school
- [ ] Deactivated message shows
- [ ] Can request renewal
- [ ] Renewal request recorded

### 9. Admin Interface
- [ ] Access `/admin/` with superuser
- [ ] Can view all models
- [ ] Can add/edit/delete records
- [ ] No database integrity errors

### 10. Static Files & Media
- [ ] Images load
- [ ] CSS styling applied
- [ ] JavaScript functionality works
- [ ] No 404 errors for assets

---

## Performance Tests (Local)

### Response Times
- [ ] Landing page: < 500ms
- [ ] Features demo: < 1000ms
- [ ] Login: < 500ms
- [ ] Dashboard: < 1000ms

### Database
- [ ] No N+1 queries (check Django Debug Toolbar)
- [ ] Database migrations are reversible
- [ ] No slow queries

---

## Security Pre-Flight

### Before PythonAnywhere Deployment:
- [ ] Change `DEBUG = False` locally, test site still works
- [ ] Update `SECRET_KEY` (generate new one)
- [ ] Set `ALLOWED_HOSTS` correctly
- [ ] Remove any hardcoded credentials
- [ ] Check `.gitignore` is comprehensive
- [ ] No sensitive data in templates

### To Generate New SECRET_KEY:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

---

## Browser Compatibility

Test in:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge
- [ ] Mobile browsers

---

## Post-Deployment Testing

### At `yourusername.pythonanywhere.com`

### Functional Tests
- [ ] Landing page loads (HTTPS)
- [ ] Features demo works
- [ ] Login functions correctly
- [ ] Can create classes
- [ ] Promotion center accessible
- [ ] History page loads
- [ ] Admin panel works

### Performance Tests
- [ ] Page load time acceptable
- [ ] No 500 errors
- [ ] Database queries optimized
- [ ] Static files loading

### Security Tests
- [ ] HTTPS enforced
- [ ] Cannot access `/admin/` without login
- [ ] CSRF tokens working
- [ ] Session management secure

### Edge Cases
- [ ] Try invalid login (should fail gracefully)
- [ ] Try SQL injection in search (should be escaped)
- [ ] Test with slow network (observe loading)
- [ ] Test on mobile (responsive design)

---

## Common Issues & Fixes

### Issue: Debug Toolbar Interferes
```python
# Remove from INSTALLED_APPS for production
# Or set DEBUG = False to disable it
```

### Issue: Static Files Return 404
```bash
# Re-run:
python manage.py collectstatic --noinput

# Check settings:
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
```

### Issue: Database Lock (SQLite)
```bash
# Migrate to MySQL on PythonAnywhere
# SQLite has connection issues with shared hosting
```

### Issue: Media Files Not Accessible
```python
# Ensure MEDIA_ROOT and MEDIA_URL are set
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
```

---

## Sign-Off

| Item | Status | Date |
|------|--------|------|
| All local tests passing | ⬜ | |
| Demo content reviewed | ⬜ | |
| Deployment document reviewed | ⬜ | |
| Security checklist complete | ⬜ | |
| Ready for PythonAnywhere | ⬜ | |

---

## Next Steps

1. ✅ Run all local tests
2. ✅ Check database migrations
3. ✅ Verify static files
4. ✅ Review security settings
5. ⏳ Deploy to PythonAnywhere
6. ⏳ Run post-deployment tests
7. ⏳ Share demo link with customers
8. ⏳ Gather feedback

---

**Version:** 1.0  
**Last Updated:** June 2026
