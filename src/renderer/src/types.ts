export interface ModifyOptions {
  setReadOnly: boolean;
}

export interface StorageData {
  'telemetry.machineId'?: string;
  'telemetry.macMachineId'?: string;
  'telemetry.devDeviceId'?: string;
  'telemetry.sqmId'?: string;
  [key: string]: any;
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