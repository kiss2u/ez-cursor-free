import type { CurrentIds } from '@renderer/types'
import type { ModifyResult } from '../../main/types'

interface IpcRenderer {
  invoke(channel: 'check-file-permission'): Promise<{ isReadOnly: boolean }>
  invoke(channel: 'modify-ids'): Promise<ModifyResult>
  invoke(channel: 'set-file-permission', value: boolean): Promise<ModifyResult>
  invoke(channel: 'get-current-ids'): Promise<CurrentIds>
  invoke(channel: 'backup-storage'): Promise<ModifyResult>
  invoke(channel: 'restore-storage'): Promise<ModifyResult>
  invoke(channel: 'check-backup-exists'): Promise<{ exists: boolean }>
}

declare global {
  interface Window {
    electron: {
      ipcRenderer: IpcRenderer
    }
  }
}

export {} 