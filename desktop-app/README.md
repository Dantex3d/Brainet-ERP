# Brainet Desktop App

This folder contains a simple Electron desktop wrapper for the Brainet ERP web system.

## How it works

- The Electron app launches a desktop window
- It loads the web system at `http://localhost:8000` by default
- You can override the target URL with the `APP_URL` environment variable

## Setup

1. Open a terminal in `desktop-app`
2. Install dependencies:

```powershell
npm install
```

3. Run the desktop app:

```powershell
npm start
```

4. If your Django site is running elsewhere, set the URL first:

```powershell
$env:APP_URL = "https://your-deployed-site.com"
npm start
```

## Build (Windows)

```powershell
npm run package
```

The packaged app will appear in `desktop-app/dist/BrainetERP-win32-x64`.

## Notes

- Keep your Django server running for the desktop app to load the site.
- If the site fails to load, the app will show a fallback offline page.
