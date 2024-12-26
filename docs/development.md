## IPC 通信
项目使用 Electron 的 IPC 机制进行主进程和渲染进程间的通信。所有 IPC 通道都在 `src/renderer/src/types/electron.d.ts` 中定义了类型，确保类型安全。

### 可用的 IPC 通道：
- `check-file-permission`: 检查文件权限状态
- `modify-ids`: 修改 IDs
- `set-file-permission`: 设置文件权限
- `get-current-ids`: 获取当前 IDs 