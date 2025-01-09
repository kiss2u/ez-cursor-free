// 定义 IPC 通信接口
interface IpcRendererInterface {
  invoke: (channel: string, ...args: any[]) => Promise<any>
  on: (channel: string, callback: (...args: any[]) => void) => void
  removeListener: (channel: string, callback: (...args: any[]) => void) => void
  removeListeners: (channel: string) => void
}

// 定义 Electron API 接口
export interface IElectronAPI {
  platform: () => Promise<string>
  ipcRenderer: IpcRendererInterface
} 