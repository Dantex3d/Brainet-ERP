# Build and Release Guide for Brainet ERP Apps

This guide explains how to build the desktop and mobile apps and release them to GitHub.

## 📋 Overview

The Brainet ERP project consists of:
- **Desktop App**: Electron-based wrapper for Windows
- **Mobile App**: React Native/Expo cross-platform app
- **Automated Releases**: GitHub Actions workflows for CI/CD

## 🚀 Quick Start (Windows)

### Option 1: Using PowerShell Script (Easiest)

```powershell
# Make sure you're in the project root directory
cd C:\Users\DANTEX3D\Desktop\Brainet-ERP

# Run the build script
./build-apps.ps1 -Version "0.2.0"  # Optional: specify version

# Or just use defaults
./build-apps.ps1
```

### Option 2: Using Bash Script

```bash
cd C:\Users\DANTEX3D\Desktop\Brainet-ERP
bash build-apps.sh
```

### Option 3: Manual Build

#### Desktop App
```powershell
cd desktop-app
npm install
npm run build        # Standard Windows build
npm run build:all    # Windows + Portable versions
```

#### Mobile App
```powershell
cd mobile-app
npm install --legacy-peer-deps
npm start            # Start Expo development server
npm run android      # Build for Android
npm run ios         # Build for iOS (macOS only)
```

## 📦 What Gets Built

### Desktop App Output
- **Location**: `desktop-app/dist/BrainetERP-win32-x64/`
- **Files**: 
  - `BrainetERP.exe` - Main executable
  - Supporting DLLs and resources
  - Complete application bundle

### Mobile App
- Built with Expo/EAS
- Android: APK/AAB files
- iOS: IPA files
- Requires additional configuration (see below)

## 🔧 Configuration

### Desktop App
The desktop app loads from a URL defined in `main.js`:

```javascript
const APP_URL = process.env.APP_URL || 'https://your-deployed-brainet-site.com';
```

To override at runtime:
```powershell
$env:APP_URL = "https://your-site.com"
npm start
```

### Mobile App
Uses Expo for development and EAS for production builds.

#### To enable production builds:
1. Install EAS CLI:
```bash
npm install -g eas-cli
```

2. Configure EAS (in `mobile-app` directory):
```bash
eas build:configure
```

3. Build:
```bash
npm run build         # All platforms
npm run build:android # Android only
npm run build:ios     # iOS only
```

## 🔄 GitHub Actions Workflow

The workflow is configured in `.github/workflows/build-release.yml`

### Triggers
- **Auto**: On push to `main` branch when app files change
- **Manual**: Via GitHub Actions "Run workflow" button

### What Happens
1. ✅ Installs dependencies
2. ✅ Builds desktop app for Windows
3. ✅ Installs mobile app dependencies
4. ✅ Creates artifacts for download
5. ✅ (Optional) Publishes GitHub Release with binaries

## 📤 Publishing to GitHub

### Automatic Release (GitHub Actions)
1. Make your changes and commit:
```powershell
git add .
git commit -m "Release v0.2.0"
```

2. Create a tag:
```powershell
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

3. GitHub Actions automatically:
   - Builds both apps
   - Creates a GitHub Release
   - Uploads artifacts

### Manual Release via GitHub Web
1. Go to: https://github.com/yourusername/Brainet-ERP/releases
2. Click "Create a new release"
3. Enter version tag (e.g., `v0.2.0`)
4. Upload files from `releases/v0.2.0/` folder
5. Add release notes
6. Publish

## 📥 Downloading Released Apps

Users can download apps from:
- **GitHub Releases**: https://github.com/yourusername/Brainet-ERP/releases
- **Direct Download**: Get specific version assets
- **Latest**: Always available on Releases page

## 🐛 Troubleshooting

### Desktop App Issues

**npm: command not found**
- Install Node.js from https://nodejs.org/
- Restart terminal/PowerShell

**Electron build fails**
```powershell
# Clear cache and reinstall
cd desktop-app
rm -r node_modules, package-lock.json
npm install
npm run build
```

### Mobile App Issues

**Dependency conflicts**
```bash
npm install --legacy-peer-deps
```

**Port 19000 already in use**
```bash
npm start -- --port 19001
```

**EAS not found**
```bash
npm install -g eas-cli
eas whoami  # Verify installation
```

## 📝 Version Management

### Update Version for Release
Update `version` in package.json files:

**Desktop:**
```json
{
  "version": "0.2.0"
}
```

**Mobile:**
```json
{
  "version": "0.2.0"
}
```

Then run the build script - it will use the new version in file names and archives.

## 🎯 Release Checklist

- [ ] Update version in `desktop-app/package.json`
- [ ] Update version in `mobile-app/package.json`
- [ ] Update version in main `package.json` (if exists)
- [ ] Test desktop app locally: `npm start` in desktop-app
- [ ] Test mobile app locally: `npm start` in mobile-app
- [ ] Commit changes: `git add . && git commit -m "vX.X.X release"`
- [ ] Create tag: `git tag -a vX.X.X -m "Release X.X.X"`
- [ ] Push tag: `git push origin vX.X.X`
- [ ] Verify GitHub Actions builds successfully
- [ ] Check GitHub Releases page for published artifacts
- [ ] Test downloaded apps work correctly

## 📚 Additional Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [Expo Documentation](https://docs.expo.dev/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [EAS Build Docs](https://docs.expo.dev/build/introduction/)

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review GitHub Actions logs: Actions tab → workflow → failed job
3. Check build script output for detailed error messages
4. Review app-specific documentation in `desktop-app/README.md` and `mobile-app/README.md`

---

**Last Updated**: 2026-06-15
**Maintainer**: Brainet ERP Team
