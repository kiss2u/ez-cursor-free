import { contextBridge, ipcRenderer } from 'electron'
import { IElectronAPI } from './types'

// 直接暴露 API，不需要单独定义 api 变量
contextBridge.exposeInMainWorld('electron', {
  platform: () => ipcRenderer.invoke('platform'),
  ipcRenderer: {
    invoke: (channel: string, ...args: any[]) => ipcRenderer.invoke(channel, ...args),
    on: (channel: string, callback: (...args: any[]) => void) => {
      ipcRenderer.on(channel, (_, ...args) => callback(...args))
    },
    removeListeners: (channel: string) => {
      ipcRenderer.removeAllListeners(channel)
    }
  }
})

export type { IElectronAPI }
