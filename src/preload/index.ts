import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import { CurrentIds, ModifyResult } from '../main/types'

// Custom APIs for renderer
const api = {
  getCurrentIds: () => ipcRenderer.invoke('get-current-ids'),
  modifyIds: (options: any) => ipcRenderer.invoke('modify-ids', options)
}

// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}

export type ElectronAPI = {
  ipcRenderer: {
    invoke(channel: 'get-current-ids'): Promise<CurrentIds>
    invoke(channel: 'modify-ids'): Promise<ModifyResult>
    invoke(channel: 'set-file-permission', isReadOnly: boolean): Promise<ModifyResult>
    invoke(channel: 'check-file-permission'): Promise<{ isReadOnly: boolean }>
    invoke(channel: 'backup-storage'): Promise<ModifyResult>
    invoke(channel: 'restore-storage'): Promise<ModifyResult>
    invoke(channel: 'check-backup-exists'): Promise<{ exists: boolean }>
  }
}
