const { app, BrowserWindow } = require("electron");
const path = require("path");

// Switch between local dev and deployed Django site
const isDev = !app.isPackaged;
const APP_URL = isDev
  ? "http://127.0.0.1:8000" // Django dev server
  : "https://brainet-analytics-system.onrender.com"; // deployed site

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, "assets", "brainet.ico")
  });

  mainWindow.loadURL(APP_URL);
  mainWindow.setMenuBarVisibility(false);

  // Fallback if site fails to load
  mainWindow.webContents.on("did-fail-load", () => {
    mainWindow.loadFile(path.join(__dirname, "offline.html"));
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
