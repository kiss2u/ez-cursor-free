import type { CurrentIds } from '@renderer/types'

interface IpcRenderer {
  invoke(channel: 'check-file-permission'): Promise<{ isReadOnly: boolean }>
  invoke(channel: 'modify-ids'): Promise<{ success: boolean; error?: string }>
  invoke(channel: 'set-file-permission', value: boolean): Promise<{ success: boolean; error?: string }>
  invoke(channel: 'get-current-ids'): Promise<CurrentIds>
}

declare global {
  interface Window {
    electron: {
      ipcRenderer: IpcRenderer
    }
  }
}

export {} 