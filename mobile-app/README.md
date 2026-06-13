# Brainet Mobile App

A simple Expo-based mobile wrapper that loads the Brainet ERP web system inside a WebView.

## Setup

1. Open a terminal in `mobile-app`
2. Install dependencies:

```powershell
npm install
```

3. Start the app:

```powershell
npm start
```

4. Use the Expo app on your phone, an emulator, or run directly on Android:

```powershell
npm run android
```

## Default URL

The app loads `https://your-deployed-brainet-site.com` by default.

If your deployed site uses a different domain, set the `APP_URL` environment variable before starting the app:

```powershell
$env:APP_URL = "https://your-brainet-site.com"
npm start
```

## Notes

- This is a mobile wrapper, not a fully native app with separate backend logic.
- It is ideal for quickly packaging your existing Django site as a mobile experience.
- For production deployment to Google Play, configure your Expo or Android build accordingly.
