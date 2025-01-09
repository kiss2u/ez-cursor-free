import { app, shell, BrowserWindow, ipcMain, net } from 'electron'
import { join, dirname } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'
import { homedir } from 'os'
import { existsSync, readFileSync, writeFileSync, chmodSync, statSync, copyFileSync, mkdirSync as mkdir } from 'fs'
import { platform } from 'os'
import { StorageData, ModifyResult, CurrentIds } from './types'
import { compare } from 'semver'
import { spawn } from 'child_process'

function getStoragePath(): string {
  const home = homedir()
  
  switch (platform()) {
    case 'win32':
      return join(home, 'AppData', 'Roaming', 'Cursor', 'User', 'globalStorage', 'storage.json')
    case 'darwin':
      return join(home, 'Library', 'Application Support', 'Cursor', 'User', 'globalStorage', 'storage.json')
    case 'linux':
      return join(home, '.config', 'Cursor', 'User', 'globalStorage', 'storage.json')
    default:
      throw new Error('不支持的操作系统')
  }
}

function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c == 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

function generateMachineId(): string {
  // 生成32字节的十六进制字符串
  const bytes = new Array(32).fill(0).map(() => Math.floor(Math.random() * 256))
  return bytes.map(b => b.toString(16).padStart(2, '0')).join('')
}

function generateSqmId(): string {
  // 生成带大括号的UUID格式
  return `{${generateUUID().toUpperCase()}}`
}

function createWindow(): void {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 550,
    show: false,
    autoHideMenuBar: true,
    frame: true,
    resizable: false,
    maximizable: false,
    fullscreenable: false,
    center: true,
    icon: join(__dirname,'../../resources/icon.png'),
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  // 设置窗口大小限制
  mainWindow.setMinimumSize(800, 550)

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.electron')

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // IPC Handlers
  ipcMain.handle('get-current-ids', async (): Promise<CurrentIds> => {
    try {
      const configPath = getStoragePath()
      let data: StorageData = {}
      
      if (existsSync(configPath)) {
        const content = readFileSync(configPath, 'utf8')
        data = JSON.parse(content)
      }

      return {
        configPath,
        machineId: data['telemetry.machineId'] || '',
        macMachineId: data['telemetry.macMachineId'] || '',
        devDeviceId: data['telemetry.devDeviceId'] || '',
        sqmId: data['telemetry.sqmId'] || ''
      }
    } catch (error) {
      const err = error as Error
      throw new Error(`读取配置失败: ${err.message || '未知错误'}`)
    }
  })

  ipcMain.handle('modify-ids', async (): Promise<ModifyResult> => {
    try {
      const configPath = getStoragePath()
      let data: StorageData = {}
      
      if (existsSync(configPath)) {
        const content = readFileSync(configPath, 'utf8')
        data = JSON.parse(content)
      }

      // 生成新的 ID
      data['telemetry.machineId'] = generateMachineId()
      data['telemetry.macMachineId'] = generateUUID()
      data['telemetry.devDeviceId'] = generateUUID()
      data['telemetry.sqmId'] = generateSqmId()

      // 写入文件
      writeFileSync(configPath, JSON.stringify(data, null, 2))

      return { success: true }
    } catch (error) {
      const err = error as Error
      return { success: false, error: err.message || '未知错误' }
    }
  })

  ipcMain.handle('set-file-permission', async (_, isReadOnly: boolean): Promise<ModifyResult> => {
    try {
      const configPath = getStoragePath()
      chmodSync(configPath, isReadOnly ? 0o444 : 0o666)
      return { success: true }
    } catch (error) {
      const err = error as Error
      return { success: false, error: err.message || '未知错误' }
    }
  })

  ipcMain.handle('check-file-permission', async (): Promise<{ isReadOnly: boolean }> => {
    try {
      const configPath = getStoragePath()
      const stats = statSync(configPath)
      // 检查文件是否为只读模式
      const isReadOnly = (stats.mode & 0o222) === 0
      return { isReadOnly }
    } catch (error) {
      const err = error as Error
      throw new Error(`检查文件权限失败: ${err.message || '未知错误'}`)
    }
  })

  ipcMain.handle('backup-storage', async (): Promise<ModifyResult> => {
    try {
      const sourcePath = getStoragePath()
      const backupPath = getBackupPath()
      
      if (!existsSync(sourcePath)) {
        return { success: false, error: '配置文件不存在' }
      }
      
      copyFileSync(sourcePath, backupPath)
      return { success: true }
    } catch (error) {
      const err = error as Error
      return { success: false, error: err.message || '备份失败' }
    }
  })

  ipcMain.handle('restore-storage', async (): Promise<ModifyResult> => {
    try {
      const sourcePath = getBackupPath()
      const targetPath = getStoragePath()
      
      if (!existsSync(sourcePath)) {
        return { success: false, error: '备份文件不存在' }
      }
      
      // 验证备份文件格式
      try {
        const content = readFileSync(sourcePath, 'utf8')
        JSON.parse(content) // 验证 JSON 格式
      } catch {
        return { success: false, error: '备份文件格式错误' }
      }
      
      copyFileSync(sourcePath, targetPath)
      return { success: true }
    } catch (error) {
      const err = error as Error
      return { success: false, error: err.message || '还原失败' }
    }
  })

  ipcMain.handle('check-backup-exists', async (): Promise<{ exists: boolean }> => {
    const backupPath = getBackupPath()
    return { exists: existsSync(backupPath) }
  })

  ipcMain.handle('check-updates', async () => {
    return await checkForUpdates()
  })

  ipcMain.handle('open-release-page', async (_, url: string) => {
    shell.openExternal(url)
    return { success: true }
  })

  // 添加保活处理器
  ipcMain.handle('start-keep-alive', async () => {
    return new Promise((resolve, reject) => {
      try {
        const extDir = copyExtensionFiles()
        if (!extDir) {
          reject({ success: false, error: '插件目录准备失败，请检查文件权限' })
          return
        }

        const pythonScriptPath = join(__dirname, '../../workspace/cursor_pro_keep_alive.py')
        if (!existsSync(pythonScriptPath)) {
          reject({ success: false, error: 'Python脚本不存在' })
          return
        }

        const pythonProcess = spawn('python', [
          '-u',  // 无缓冲输出
          pythonScriptPath,
          '--extension-path', extDir
        ], {
          env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',
            LANG: 'zh_CN.UTF-8',
            PYTHONUNBUFFERED: '1'  // 确保Python输出无缓冲
          }
        })
        
        pythonProcess.stdout.setEncoding('utf-8')
        pythonProcess.stderr.setEncoding('utf-8')
        
        let output = ''
        let error = ''
        
        pythonProcess.stdout.on('data', (data) => {
          const message = data.toString()
          output += message
          BrowserWindow.getAllWindows().forEach(window => {
            window.webContents.send('keep-alive-output', message)
          })
        })

        pythonProcess.stderr.on('data', (data) => {
          const message = data.toString()
          error += message
          BrowserWindow.getAllWindows().forEach(window => {
            window.webContents.send('keep-alive-error', message)
          })
        })

        pythonProcess.on('close', (code) => {
          if (code === 0) {
            resolve({ success: true, output })
          } else {
            reject({ 
              success: false, 
              error: error || `Python进程退出，代码: ${code}`, 
              output 
            })
          }
        })

        pythonProcess.on('error', (err) => {
          reject({ 
            success: false, 
            error: `启动Python进程失败: ${err.message}`, 
            output 
          })
        })
      } catch (error) {
        reject({ 
          success: false, 
          error: `执行出错: ${error instanceof Error ? error.message : String(error)}` 
        })
      }
    })
  })

  createWindow()

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// In this file you can include the rest of your app"s specific main process
// code. You can also put them in separate files and require them here.

// 获取备份文件路径
function getBackupPath(): string {
  const storagePath = getStoragePath()
  return join(dirname(storagePath), 'storage.json.backup')
}

// 添加检查更新函数
async function checkForUpdates(): Promise<{
  hasUpdate: boolean
  latestVersion: string
  downloadUrl: string
  releaseNotes: string
} | null> {
  try {
    const request = net.request({
      method: 'GET',
      url: 'https://api.github.com/repos/GalacticDevOps/ez-cursor-free/releases/latest'
    })

    return new Promise((resolve, reject) => {
      let data = ''
      
      request.on('response', (response) => {
        response.on('data', (chunk) => {
          data += chunk
        })
        
        response.on('end', () => {
          try {
            const release = JSON.parse(data)
            const currentVersion = app.getVersion()
            const latestVersion = release.tag_name.replace('v', '')
            
            // 直接使用 semver 比较完整的版本号（包括预发布标签）
            const hasUpdate = compare(latestVersion, currentVersion) > 0
            
            // 不要更新到预发布版本，除非当前也是预发布版本
            const isCurrentPrerelease = currentVersion.includes('-')
            const isLatestPrerelease = latestVersion.includes('-')
            
            // 只在以下情况显示更新：
            // 1. 最新版本是正式版本且版本号更高
            // 2. 当前是预发布版本，且最新版本更新（无论是否为预发布）
            if (hasUpdate && (!isLatestPrerelease || isCurrentPrerelease)) {
              resolve({
                hasUpdate: true,
                latestVersion,
                downloadUrl: release.html_url,
                releaseNotes: release.body || '暂无更新说明'
              })
            } else {
              resolve(null)
            }
          } catch (error) {
            reject(error)
          }
        })
      })
      
      request.on('error', (error) => {
        reject(error)
      })
      
      request.end()
    })
  } catch (error) {
    console.error('检查更新失败:', error)
    return null
  }
}

// 修改 copyExtensionFiles 函数
function copyExtensionFiles() {
  // 直接使用目标目录，不需要源目录
  const destExtDir = join(app.getPath('userData'), 'turnstilePatch')
  
  try {
    // 创建插件文件内容
    const manifest = {
      name: "Turnstile Patch",
      version: "1.0",
      manifest_version: 2,
      description: "Patch for Turnstile verification",
      permissions: [
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
      ],
      content_scripts: [{
        matches: ["<all_urls>"],
        js: ["content.js"],
        run_at: "document_start"
      }]
    }
    
    const contentScript = `
// Turnstile patch content script
(function() {
  const script = document.createElement('script');
  script.textContent = \`
    if (window.turnstile) {
      const originalRender = window.turnstile.render;
      window.turnstile.render = function(container, options) {
        options = options || {};
        const originalCallback = options.callback;
        options.callback = function(token) {
          console.log('Turnstile token:', token);
          if (typeof originalCallback === 'function') {
            originalCallback(token);
          }
        };
        return originalRender(container, options);
      };
    }

    // 监听动态加载的 turnstile
    Object.defineProperty(window, 'turnstile', {
      set: function(value) {
        if (value && value.render) {
          const originalRender = value.render;
          value.render = function(container, options) {
            options = options || {};
            const originalCallback = options.callback;
            options.callback = function(token) {
              console.log('Turnstile token:', token);
              if (typeof originalCallback === 'function') {
                originalCallback(token);
              }
            };
            return originalRender(container, options);
          };
        }
        delete window.turnstile;
        window.turnstile = value;
      },
      get: function() {
        return window._turnstile;
      },
      configurable: true
    });
  \`;
  document.documentElement.appendChild(script);
  script.remove();
})();
    `.trim()

    // 确保目标目录存在
    if (!existsSync(destExtDir)) {
      try {
        mkdir(destExtDir)
      } catch (error) {
        console.error('创建目标目录失败:', error)
        return null
      }
    }

    try {
      // 直接写入文件到目标目录
      const manifestPath = join(destExtDir, 'manifest.json')
      const contentPath = join(destExtDir, 'content.js')

      writeFileSync(manifestPath, JSON.stringify(manifest, null, 2))
      writeFileSync(contentPath, contentScript)

      // 验证文件是否创建成功
      if (!existsSync(manifestPath) || !existsSync(contentPath)) {
        console.error('文件创建验证失败')
        return null
      }

      return destExtDir
    } catch (error) {
      console.error('创建插件文件失败:', error)
      return null
    }
  } catch (error) {
    console.error('插件目录准备失败:', error)
    return null
  }
}
