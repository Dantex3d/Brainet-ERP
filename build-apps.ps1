# Brainet ERP - Build and Release Apps (PowerShell)
# This script builds both desktop and mobile apps and prepares them for GitHub release

param(
    [string]$Version = "0.1.0"
)

# Error handling
$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Brainet ERP - Build & Release Apps" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

try {
    # Get version from desktop-app package.json
    if (Test-Path "./desktop-app/package.json") {
        $packageJson = Get-Content "./desktop-app/package.json" | ConvertFrom-Json
        $Version = $packageJson.version
    }
    
    Write-Host "Building version: $Version" -ForegroundColor Yellow
    
    # Build Desktop App
    Write-Host "`n[1/3] Building Desktop App..." -ForegroundColor Yellow
    Push-Location desktop-app
    
    Write-Host "Installing dependencies..." -ForegroundColor Gray
    npm install
    
    Write-Host "Packaging application..." -ForegroundColor Gray
    npm run package
    
    $desktopBuildPath = "dist/BrainetERP-win32-x64"
    if (Test-Path $desktopBuildPath) {
        Write-Host "✓ Desktop app built successfully" -ForegroundColor Green
        Write-Host "  Location: $(Get-Location)/$desktopBuildPath" -ForegroundColor Gray
    } else {
        throw "Desktop app build failed"
    }
    Pop-Location
    
    # Build Mobile App
    Write-Host "`n[2/3] Installing Mobile App Dependencies..." -ForegroundColor Yellow
    Push-Location mobile-app
    
    Write-Host "Installing with legacy peer deps..." -ForegroundColor Gray
    npm install --legacy-peer-deps
    
    Write-Host "✓ Mobile app dependencies installed" -ForegroundColor Green
    Write-Host "  Ready for: 'eas build' or 'expo build'" -ForegroundColor Gray
    Pop-Location
    
    # Create Release Archive
    Write-Host "`n[3/3] Preparing Release Package..." -ForegroundColor Yellow
    $releaseDir = "releases/v$Version"
    
    if (-not (Test-Path $releaseDir)) {
        New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    }
    
    # Copy desktop app
    $sourcePath = "desktop-app/dist/BrainetERP-win32-x64"
    $destPath = "$releaseDir/BrainetERP-Desktop-v$Version"
    
    if (Test-Path $destPath) {
        Remove-Item -Recurse -Force $destPath
    }
    
    Copy-Item -Path $sourcePath -Destination $destPath -Recurse
    Write-Host "✓ Desktop app packaged" -ForegroundColor Green
    
    # Create archive
    $archiveName = "BrainetERP-v$Version-all.zip"
    $archivePath = "$releaseDir/$archiveName"
    
    Write-Host "Creating archive: $archiveName" -ForegroundColor Yellow
    Compress-Archive -Path $destPath -DestinationPath $archivePath -Force
    Write-Host "✓ Release archive created" -ForegroundColor Green
    
    # Summary
    Write-Host "`n======================================" -ForegroundColor Green
    Write-Host "✓ Build Complete!" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    
    Write-Host "Release location: $releaseDir" -ForegroundColor Yellow
    Write-Host "`n📦 Created files:" -ForegroundColor Cyan
    Get-ChildItem -Path $releaseDir -Force | Format-Table -Property Name, Length
    
    Write-Host "`n🚀 Next steps to publish to GitHub:" -ForegroundColor Cyan
    Write-Host "1. Commit: git add . && git commit -m 'Release v$Version'" -ForegroundColor Gray
    Write-Host "2. Tag:    git tag -a v$Version -m 'Release v$Version' && git push origin v$Version" -ForegroundColor Gray
    Write-Host "3. GitHub Actions will automatically create a release!" -ForegroundColor Gray
    Write-Host "======================================" -ForegroundColor Green
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
