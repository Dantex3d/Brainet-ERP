# 🚀 Deploy Brainet Analytics to PythonAnywhere

## Quick Deployment Guide

Follow these steps to deploy your Brainet Analytics application to PythonAnywhere and test it live.

---

## Step 1: Prepare Your Code

### 1.1 Create a `.gitignore` (if not already present)

```bash
# In project root
cat > .gitignore << EOF
*.pyc
__pycache__/
*.sqlite3
db.sqlite3
.env
.DS_Store
media/
static/
*.log
.vscode/
.idea/
*.egg-info/
dist/
build/
EOF
```

### 1.2 Create `requirements.txt`

```bash
# In project root, run:
pip freeze > requirements.txt
```

Or manually create with these key dependencies:

```
Django>=4.2
pillow>=10.0
reportlab>=4.0
python-dotenv>=1.0
gunicorn>=21.0
```

### 1.3 Update `settings.py` for Production

Edit `brainet/settings.py`:

```python
# At the top, add:
import os
from pathlib import Path

# Change DEBUG based on environment
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Add PythonAnywhere host
ALLOWED_HOSTS = [
    'yourusername.pythonanywhere.com',
    'localhost',
    '127.0.0.1'
]

# Database (keep SQLite for now, or use MySQL from PythonAnywhere)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### 1.4 Commit to Git

```bash
cd /path/to/brainet
git init
git add .
git commit -m "Initial commit - Ready for deployment"
```

---

## Step 2: Create PythonAnywhere Account

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Click **"Start running Python online in less than a minute"**
3. Create a free account
4. Verify email
5. Go to **Dashboard**

---

## Step 3: Set Up PythonAnywhere

### 3.1 Open Bash Console

1. From Dashboard → **Consoles**
2. Click **"Bash"** → New console

### 3.2 Clone Your Repository

```bash
# If using GitHub:
cd /home/yourusername
git clone https://github.com/yourusername/brainet.git

# Navigate to project
cd brainet
```

Or **upload your code** via Web Interface:
1. Go to **Files**
2. Upload your `.zip` file
3. Extract it

### 3.3 Create Virtual Environment

```bash
# In /home/yourusername/brainet
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3.4 Create Django Super User (Admin)

```bash
cd brainet  # The main project folder with manage.py
python manage.py migrate
python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: your@email.com
# Password: (create strong password)
```

### 3.5 Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Step 4: Configure Web App

### 4.1 Create Web App

1. From Dashboard → **Web**
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.10**
5. Click **"Next"**

### 4.2 Configure WSGI File

1. Go to **Web** tab
2. Under "Code" section, click link to **WSGI configuration file**
3. Replace the entire content with:

```python
# /var/www/yourusername_pythonanywhere_com_wsgi.py
import os
import sys

path = '/home/yourusername/brainet'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'brainet.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace `yourusername` with your actual PythonAnywhere username.

**Save & Exit**

### 4.3 Set Virtualenv Path

1. Still on **Web** tab
2. Find "Virtualenv" section
3. Click and set to: `/home/yourusername/brainet/venv`
4. Click ✓

### 4.4 Set Working Directory (if needed)

1. Scroll to "Working directory"
2. Set to: `/home/yourusername/brainet`

### 4.5 Reload Web App

1. Click green **"Reload yourusername.pythonanywhere.com"** button
2. Wait 10-30 seconds

---

## Step 5: Test Your Deployment

### 5.1 Check Website

Go to: `https://yourusername.pythonanywhere.com`

You should see the **Brainet landing page**!

### 5.2 Login

1. Click **"Login to System"** button
2. Username: `admin` (or your superuser)
3. Password: (what you created earlier)

### 5.3 Test Features Demo

1. From landing page, click **"View Features Demo"** 
2. See all feature demonstrations
3. Navigate to dashboard

### 5.4 Test Promotion Center

1. From DOS Dashboard → **🎓 Student Promotion**
2. View promotion center
3. Check history page

---

## Step 6: Configure Database (MySQL Optional)

For better performance, use MySQL instead of SQLite:

### 6.1 Go to Databases Tab

1. PythonAnywhere Dashboard → **Databases**
2. Click **"Create a new MySQL database"**
3. Database name: `brainet`
4. Password: (create strong password)

### 6.2 Update settings.py

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'yourusername$brainet',
        'USER': 'yourusername',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'yourusername.mysql.pythonanywhere-services.com',
    }
}
```

### 6.3 Migrate to MySQL

```bash
cd /home/yourusername/brainet
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 6.4 Reload Web App

Click reload button in **Web** tab

---

## Troubleshooting

### Issue: 502 Bad Gateway Error

**Check Error Log:**
1. Go to **Web** tab
2. Scroll down → "Log files"
3. Click **Error log**
4. Look for error messages

**Common Fixes:**
```bash
# 1. Reload web app
# (From Web tab)

# 2. Check if venv is properly set
# (From Web tab → Virtualenv)

# 3. Reinstall dependencies
cd /home/yourusername/brainet
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 4. Migrate database
python manage.py migrate

# 5. Reload again
```

### Issue: Static Files Not Showing

```bash
cd /home/yourusername/brainet
source venv/bin/activate
python manage.py collectstatic --noinput
# Then reload web app
```

### Issue: Login Page Not Working

```bash
# Check that superuser was created
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.all()
# If empty, create superuser:
# python manage.py createsuperuser
```

### Issue: Demo Page Not Found (404)

1. Verify URL in settings: `/features-demo/`
2. Check that view is defined
3. Check that URL pattern is in `urls.py`
4. Reload web app

---

## Maintenance Tasks

### Regular Backups

```bash
# Download database
# From PythonAnywhere Files, download db.sqlite3 or export MySQL

# Or use:
python manage.py dumpdata > backup.json
```

### Update Code

```bash
cd /home/yourusername/brainet
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# Reload web app
```

### Monitor Logs

1. Dashboard → **Web**
2. View **Error log** regularly
3. Check **Access log** for traffic

---

## Custom Domain (Optional)

1. Buy domain (e.g., brainet.com)
2. PythonAnywhere → **Web**
3. Under "Web app" section, add custom domain
4. Update DNS records at registrar

---

## Performance Tips

### 1. Enable GZIP Compression
In **settings.py**:
```python
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    # ... other middleware
]
```

### 2. Use CDN for Static Files
Upload static files to external CDN if needed

### 3. Database Optimization
- For MySQL: Add indexes on frequently queried fields
- Monitor query performance

### 4. Upgrade Account (if needed)
- Free account: 512MB storage
- Paid account: More storage, always-on features

---

## Security Checklist

- [ ] Set `DEBUG = False` in production
- [ ] Set strong `SECRET_KEY` (change from default)
- [ ] Use HTTPS only
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Set secure cookie settings
- [ ] Enable CSRF protection
- [ ] Regularly update Django and dependencies

```python
# In settings.py for production:
DEBUG = False
SECRET_KEY = 'generate-random-secret-key-here'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## Testing Checklist

After deployment, test:

- [ ] Landing page loads
- [ ] Features demo accessible
- [ ] Login works
- [ ] Create a test class with streams
- [ ] Promotion center loads
- [ ] Can view promotion history
- [ ] School deactivation flow works
- [ ] License renewal page accessible
- [ ] Admin panel accessible at `/admin/`

---

## Live Testing URLs

Once deployed to `yourusername.pythonanywhere.com`:

| Feature | URL |
|---------|-----|
| Landing Page | `https://yourusername.pythonanywhere.com/` |
| Features Demo | `https://yourusername.pythonanywhere.com/features-demo/` |
| Login | `https://yourusername.pythonanywhere.com/login/` |
| Admin | `https://yourusername.pythonanywhere.com/admin/` |
| Promotion Center | `https://yourusername.pythonanywhere.com/promotion/center/` |
| Promotion History | `https://yourusername.pythonanywhere.com/promotion/history/` |

---

## Next Steps

1. ✅ Deploy to PythonAnywhere
2. ✅ Test all features
3. ✅ Share demo link with customers
4. ✅ Gather feedback
5. ⏳ Plan feature updates

---

## Support

For PythonAnywhere issues:
- [PythonAnywhere Help](https://help.pythonanywhere.com)
- [PythonAnywhere Forums](https://www.pythonanywhere.com/forums)

For Django issues:
- [Django Documentation](https://docs.djangoproject.com)
- [Django Discord Community](https://discord.gg/xcRH6mN57D)

---

**Status:** 🚀 Ready to Deploy!

**Last Updated:** June 2026  
**Version:** 1.0
