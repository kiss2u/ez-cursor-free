interface CurrentIds {
  machineId: string
  macMachineId: string
  devDeviceId: string
  sqmId: string
  configPath: string
}

interface ModifyResult {
  success: boolean
  error?: string
}

interface IpcRenderer {
  invoke(channel: string, ...args: any[]): Promise<any>
  on(channel: string, listener: (...args: any[]) => void): void
  removeListener(channel: string, listener: (...args: any[]) => void): void
  removeListeners(channel: string): void
}

interface IElectronAPI {
  ipcRenderer: IpcRenderer
}

interface Window {
  electron: IElectronAPI
  electronAPI: unknown
} 