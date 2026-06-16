#!/bin/bash
# Brainet ERP - Build and Release Apps Script
# This script builds both desktop and mobile apps and prepares them for GitHub release

set -e

echo "======================================"
echo "Brainet ERP - Build & Release Apps"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from desktop-app package.json
VERSION=$(node -p "require('./desktop-app/package.json').version" 2>/dev/null || echo "0.1.0")
echo -e "${YELLOW}Building version: $VERSION${NC}"

# Build Desktop App
echo -e "\n${YELLOW}[1/3] Building Desktop App...${NC}"
cd desktop-app
npm install
npm run package
DESKTOP_BUILD_PATH="dist/BrainetERP-win32-x64"
if [ -d "$DESKTOP_BUILD_PATH" ]; then
    echo -e "${GREEN}✓ Desktop app built successfully${NC}"
    echo "  Location: $(pwd)/$DESKTOP_BUILD_PATH"
else
    echo -e "${RED}✗ Desktop app build failed${NC}"
    exit 1
fi
cd ..

# Build Mobile App
echo -e "\n${YELLOW}[2/3] Installing Mobile App Dependencies...${NC}"
cd mobile-app
npm install --legacy-peer-deps
echo -e "${GREEN}✓ Mobile app dependencies installed${NC}"
echo "  Ready for: 'eas build' or 'expo build'"
cd ..

# Create Release Archive
echo -e "\n${YELLOW}[3/3] Preparing Release Package...${NC}"
RELEASE_DIR="releases/v$VERSION"
mkdir -p "$RELEASE_DIR"

# Copy desktop app
cp -r desktop-app/dist/BrainetERP-win32-x64 "$RELEASE_DIR/BrainetERP-Desktop-v$VERSION"
echo -e "${GREEN}✓ Desktop app packaged${NC}"

# Create archive (PowerShell for Windows compatibility)
ARCHIVE_NAME="BrainetERP-v$VERSION-all.zip"
echo -e "${YELLOW}Creating archive: $ARCHIVE_NAME${NC}"

if command -v zip &> /dev/null; then
    cd "$RELEASE_DIR"
    zip -r "$ARCHIVE_NAME" BrainetERP-Desktop-v$VERSION/
    cd ../..
else
    echo "Using PowerShell for archiving..."
    powershell -NoProfile -Command "Compress-Archive -Path '$PWD/$RELEASE_DIR/BrainetERP-Desktop-v$VERSION' -DestinationPath '$PWD/$RELEASE_DIR/$ARCHIVE_NAME' -Force"
fi

echo -e "${GREEN}✓ Release archive created${NC}"

echo -e "\n${GREEN}======================================"
echo "✓ Build Complete!"
echo "======================================"
echo -e "Release location: ${YELLOW}$RELEASE_DIR${NC}"
echo ""
echo "📦 Created files:"
ls -lh "$RELEASE_DIR/" 2>/dev/null || powershell -NoProfile -Command "Get-ChildItem -Path '$RELEASE_DIR' -Force"
echo ""
echo "🚀 Next steps to publish to GitHub:"
echo "1. Commit: git add . && git commit -m 'Release v$VERSION'"
echo "2. Tag:    git tag -a v$VERSION -m 'Release v$VERSION' && git push origin v$VERSION"
echo "3. GitHub Actions will automatically create a release!"
echo -e "=====================================${NC}"
