# PWA Installation Setup Guide

## What's Installed

Your Brainet ERP system now has Progressive Web App (PWA) capabilities that allow installation on any device via the browser.

### Files Created:

1. **`/static/manifest.json`** - PWA app metadata (name, icons, description, etc.)
2. **`/static/service-worker.js`** - Service worker for caching and offline support
3. **Updated `landing.html`** - Added installation UI and app download buttons

## How It Works

### Web App Installation (PWA)
- Users visiting your site will see an "Install" prompt
- Works on Chrome, Edge, Firefox, and mobile browsers
- Can be added to home screen/app drawer
- Loads like a native app with no URL bar

### Desktop App
- Link to download Windows executable (.exe file)
- Runs as standalone desktop application
- Connects to your hosted website

### Mobile App
- Android app link to Google Play Store
- iOS coming soon
- Native mobile experience

## For Your Render Deployment

### Before Deploying:

1. **Ensure HTTPS is enabled** (Render does this automatically)
   - PWAs require HTTPS to work
   - Render provides free SSL certificates

2. **Ensure static files are collected**
   - The manifest.json and service-worker.js need to be in staticfiles/
   - Add to your deploy script:
     ```bash
     python manage.py collectstatic --noinput
     ```

3. **Update settings.py** (already configured):
   - STATIC_URL = '/static/'
   - STATIC_ROOT = 'staticfiles'

### Icons Setup (Optional but Recommended):

Create these icon files in `/static/images/`:
- `brainet-icon-192.png` (192x192 pixels)
- `brainet-icon-512.png` (512x512 pixels)
- `brainet-maskable-192.png` (192x192 pixels, transparent edges)
- `brainet-maskable-512.png` (512x512 pixels, transparent edges)

Without these, the PWA will still work but won't have custom icons.

## Testing Locally

1. **Start your Django server**:
   ```bash
   python manage.py runserver
   ```

2. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Open in Chrome/Edge**:
   - Visit `http://localhost:8000` (local) or your Render URL (production)
   - You should see install prompts
   - Click "Install Web App" to test

4. **Test on Mobile**:
   - Visit your Render URL on a mobile phone
   - Chrome/Firefox will show "Install app" option
   - Tap to add to home screen

## Deployment Checklist

- [ ] Update Render build command to include `collectstatic`
- [ ] Ensure HTTPS is enabled (Render default)
- [ ] Optional: Add PWA icons to `/static/images/`
- [ ] Update your Procfile or deployment script to run collectstatic
- [ ] Deploy and visit landing page
- [ ] Test install prompt on desktop and mobile browsers

## Desktop App Deployment

For the downloadable desktop app:
1. Build the app: `cd desktop-app && npm run package`
2. Upload to GitHub Releases or your hosting
3. Update the download link in landing.html

## Troubleshooting

### Install button not appearing?
- Check browser: PWAs work best on Chrome, Edge, Firefox (mobile)
- Ensure HTTPS is enabled
- Check browser console for service worker errors
- Make sure manifest.json is accessible at `/static/manifest.json`

### Service worker not registering?
- Check HTTPS is enabled
- Verify `/static/service-worker.js` exists and is accessible
- Check browser's Developer Tools > Application > Service Workers

### Manifest not loading?
- Verify `/static/manifest.json` exists
- Check `<link rel="manifest">` is in landing.html head
- Verify manifest.json is valid JSON
