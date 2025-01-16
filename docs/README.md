## IPC 通信
项目使用 Electron 的 IPC 机制进行主进程和渲染进程间的通信。所有 IPC 通道都在 `src/renderer/src/types/electron.d.ts` 中定义了类型，确保类型安全。

### 主要功能
- 检查和设置文件权限
- 修改 ID
- 备份和恢复存储数据
- 检查软件更新
- 打开指定页面

## 安装与启动

```bash
git clone https://github.com/GalacticDevOps/ez-cursor-free.git
cd ez-cursor-free
pnpm install
pnpm run dev
```

### 可用的 IPC 通道：
- `check-file-permission`：检查文件是否为只读。
```typescript
返回类型：Promise<{ isReadOnly: boolean }>
```

- `modify-ids`：修改 ID，并返回修改结果。
```typescript
返回类型：Promise<ModifyResult>
```

- `set-file-permission`：设置文件的权限。
```typescript
参数：value: boolean
返回类型：Promise<ModifyResult>
```

- `get-current-ids`：获取当前的 IDs。
```typescript
返回类型：Promise<CurrentIds>
```

- `backup-storage`：执行备份存储操作。
```typescript
返回类型：Promise<ModifyResult>
```

- `restore-storage`：恢复存储数据。
```typescript
返回类型：Promise<ModifyResult>
```

- `check-backup-exists`：检查备份是否存在。
```typescript
返回类型：Promise<{ exists: boolean }>
```

- `check-updates`：检查是否有可用的更新。
```typescript
返回类型：Promise<{ hasUpdate: boolean, latestVersion: string, downloadUrl: string, releaseNotes: string } | null>
```

- `open-release-page`：打开指定页面。
```typescript
参数：url: string
返回类型：Promise<{ success: boolean }>
```

### 示例代码
调用 check-file-permission 通道：
```typescript
window.electron.ipcRenderer.invoke('check-file-permission').then(result => {
  console.log(result.isReadOnly);  // 输出文件是否只读
});
```

### 贡献
欢迎贡献代码！

如果你有好的想法或者发现问题，欢迎通过以下方式参与贡献：

提交 [Issues](https://github.com/GalacticDevOps/ez-cursor-free/issues)
提交 [Pull Requests](https://github.com/GalacticDevOps/ez-cursor-free/pulls) 来修复问题或添加新功能。