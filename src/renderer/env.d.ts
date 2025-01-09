/// <reference types="vite/client" />

// 只需要声明模块，不需要重复声明全局 Window 接口
declare module '@electron-toolkit/preload' {
  export const electronAPI: any
}

// 扩展已有的 Window 接口
interface Window {
  electron: import('../preload/types').IElectronAPI
  electronAPI: import('../preload/types').IElectronAPI
} 