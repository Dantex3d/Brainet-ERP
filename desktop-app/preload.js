const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("api", {
  // Example: expose a safe method
  ping: () => "pong"
});
