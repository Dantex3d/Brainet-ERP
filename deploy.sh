#!/bin/bash
# Quick Deployment Script for PythonAnywhere
# Run this in PythonAnywhere Bash Console

USERNAME="yourusername"  # Replace with your PythonAnywhere username
PROJECT_DIR="/home/$USERNAME/brainet"

echo "🚀 Brainet Analytics - PythonAnywhere Quick Deploy"
echo "=================================================="

# Step 1: Create Virtual Environment
echo "Step 1: Creating virtual environment..."
cd $PROJECT_DIR
python3.10 -m venv venv
source venv/bin/activate

# Step 2: Install Dependencies
echo "Step 2: Installing dependencies..."
pip install -r requirements.txt

# Step 3: Database Migration
echo "Step 3: Running database migrations..."
python manage.py migrate

# Step 4: Create Superuser (interactive)
echo "Step 4: Creating superuser..."
python manage.py createsuperuser

# Step 5: Collect Static Files
echo "Step 5: Collecting static files..."
python manage.py collectstatic --noinput

# Step 6: Check if you're using WSGI
echo "Step 6: WSGI file configuration info..."
echo "Remember to update your WSGI file at:"
echo "/var/www/${USERNAME}_pythonanywhere_com_wsgi.py"
echo ""
echo "Use the template from PYTHONANYWHERE_DEPLOYMENT.md"

echo ""
echo "✅ Deployment script complete!"
echo ""
echo "Next steps:"
echo "1. Edit WSGI file (/var/www/${USERNAME}_pythonanywhere_com_wsgi.py)"
echo "2. Set Virtualenv to: $PROJECT_DIR/venv"
echo "3. Click 'Reload yourusername.pythonanywhere.com'"
echo "4. Visit: https://${USERNAME}.pythonanywhere.com"
echo ""
echo "Check demo at: https://${USERNAME}.pythonanywhere.com/features-demo/"
