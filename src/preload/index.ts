import { contextBridge, ipcRenderer } from 'electron'
import { IElectronAPI } from './types'

// 创建一个事件监听器管理器
const listeners: { [key: string]: ((...args: any[]) => void)[] } = {}

// 自定义的 IPC 通信接口
const api: IElectronAPI = {
  platform: () => ipcRenderer.invoke('platform'),
  ipcRenderer: {
    invoke: (channel: string, ...args: any[]): Promise<any> => 
      ipcRenderer.invoke(channel, ...args),
    
    on: (channel: string, callback: (...args: any[]) => void): void => {
      if (!listeners[channel]) {
        listeners[channel] = []
      }
      listeners[channel].push(callback)
      ipcRenderer.on(channel, callback)
    },
    
    removeListener: (channel: string, callback: (...args: any[]) => void): void => {
      ipcRenderer.removeListener(channel, callback)
    },
    
    removeListeners: (channel: string): void => {
      if (listeners[channel]) {
        listeners[channel].forEach(callback => {
          ipcRenderer.removeListener(channel, callback)
        })
        listeners[channel] = []
      }
    }
  }
}

// 暴露 API
contextBridge.exposeInMainWorld('electron', api)
contextBridge.exposeInMainWorld('electronAPI', api)

export type { IElectronAPI }
