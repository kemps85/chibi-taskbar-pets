const { contextBridge, ipcRenderer } = require("electron");

/**
 * Expose the smallest possible renderer API. Node access remains unavailable
 * to the page; all asset loading is performed by the main process.
 */
contextBridge.exposeInMainWorld("taskbarPet", {
  getAnimationConfig: () => ipcRenderer.invoke("taskbar-pet:get-animation-config"),
  reportFirstFrame: () => ipcRenderer.send("taskbar-pet:first-frame"),
  onRuntimeConfig: (callback) => {
    if (typeof callback !== "function") throw new TypeError("callback must be a function");
    const listener = (_event, config) => callback(config);
    ipcRenderer.on("taskbar-pet:runtime-config", listener);
    return () => ipcRenderer.removeListener("taskbar-pet:runtime-config", listener);
  },
  onRuntimeState: (callback) => {
    if (typeof callback !== "function") throw new TypeError("callback must be a function");
    const listener = (_event, snapshot) => callback(snapshot);
    ipcRenderer.on("taskbar-pet:runtime-state", listener);
    return () => ipcRenderer.removeListener("taskbar-pet:runtime-state", listener);
  },
});
