import { ElectronAPI } from '@electron-toolkit/preload'
import { CurrentIds, ModifyResult, FilePermissionResult } from '../main/types'

interface IpcRenderer {
  invoke(channel: 'get-current-ids'): Promise<CurrentIds>
  invoke(channel: 'modify-ids'): Promise<ModifyResult>
  invoke(channel: 'set-file-permission', isReadOnly: boolean): Promise<ModifyResult>
  invoke(channel: 'check-file-permission'): Promise<FilePermissionResult>
  invoke<T>(channel: string, ...args: any[]): Promise<T>
}

declare global {
  interface Window {
    electron: Omit<ElectronAPI, 'ipcRenderer'> & {
      ipcRenderer: IpcRenderer
    }
    api: unknown
  }
}
