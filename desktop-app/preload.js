const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('desktopApp', {
  getAppUrl: () => process.env.APP_URL || 'http://localhost:8000',
});
