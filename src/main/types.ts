export interface StorageData {
  [key: string]: string;
}

export interface ModifyResult {
  success: boolean;
  error?: string;
}

export interface CurrentIds {
  configPath: string;
  machineId: string;
  macMachineId: string;
  devDeviceId: string;
  sqmId: string;
}

export interface FilePermissionResult {
  isReadOnly: boolean;
} 