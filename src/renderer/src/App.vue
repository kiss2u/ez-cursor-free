<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import type { CurrentIds } from '@renderer/types'
import type { IElectronAPI } from '../../preload'

declare global {
  interface Window {
    electron: IElectronAPI
  }
}

const configPath = ref('')
const currentIds = ref<CurrentIds>({
  machineId: '',
  macMachineId: '',
  devDeviceId: '',
  sqmId: '',
  configPath: ''
})
const isLoading = ref(false)
const message = ref('')
const setReadOnly = ref(false)
const messageTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const messageType = ref<'success' | 'error' | 'warning' | 'info'>('success')
const backupExists = ref(false)
const updateInfo = ref<{
  hasUpdate: boolean
  latestVersion: string
  downloadUrl: string
  releaseNotes: string
} | null>(null)
const isKeepAliveRunning = ref(false)

const showMessage = (msg: string, type: 'success' | 'error' | 'warning' | 'info' = 'success') => {
  message.value = msg
  messageType.value = type
  if (messageTimer.value) {
    clearTimeout(messageTimer.value)
  }
  messageTimer.value = setTimeout(() => {
    message.value = ''
    messageType.value = 'success'
  }, 3000)
}

const closeMessage = () => {
  message.value = ''
  messageType.value = 'success'
  if (messageTimer.value) {
    clearTimeout(messageTimer.value)
  }
}

const checkFilePermission = async () => {
  try {
    const data = await window.electron.ipcRenderer.invoke('check-file-permission')
    setReadOnly.value = data.isReadOnly
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '检查文件权限失败', 'error')
  }
}

const modifyIds = async () => {
  try {
    isLoading.value = true
    await checkFilePermission()
    
    if (setReadOnly.value) {
      showMessage('文件为只读模式，请先取消只读设置', 'error')
      return
    }
    
    const result = await window.electron.ipcRenderer.invoke('modify-ids')
    
    if (result.success) {
      showMessage('修改成功！请重启 Cursor 以使更改生效。', 'success')
      await loadCurrentIds()
      await checkFilePermission()
    } else {
      showMessage(result.error || '修改失败', 'error')
    }
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '发生错误', 'error')
  } finally {
    isLoading.value = false
  }
}

watch(setReadOnly, async (newValue) => {
  try {
    const result = await window.electron.ipcRenderer.invoke('set-file-permission', newValue)
    if (result.success) {
      showMessage(`已${newValue ? '启用' : '关闭'}只读模式`, 'warning')
    } else {
      showMessage(result.error || '设置失败', 'error')
      setReadOnly.value = !newValue
    }
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '设置失败', 'error')
    setReadOnly.value = !newValue
  }
})

const loadCurrentIds = async () => {
  try {
    const data = await window.electron.ipcRenderer.invoke('get-current-ids')
    currentIds.value = data
    configPath.value = data.configPath
    await checkFilePermission()
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '无法加载当前 ID', 'error')
  }
}

const checkBackupExists = async () => {
  try {
    const result = await window.electron.ipcRenderer.invoke('check-backup-exists')
    backupExists.value = result.exists
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '检查备份状态失败', 'error')
  }
}

const backupStorage = async () => {
  try {
    const result = await window.electron.ipcRenderer.invoke('backup-storage')
    if (result.success) {
      showMessage('备份成功', 'success')
      await checkBackupExists()
    } else {
      showMessage(result.error || '备份失败', 'error')
    }
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '备份失败', 'error')
  }
}

const restoreStorage = async () => {
  if (!backupExists.value) {
    showMessage('没有可用的备份', 'error')
    return
  }

  try {
    await checkFilePermission()
    
    if (setReadOnly.value) {
      showMessage('文件为只读模式，请先取消只读设置', 'error')
      return
    }

    const result = await window.electron.ipcRenderer.invoke('restore-storage')
    if (result.success) {
      showMessage('还原成功！请重启 Cursor 以使更改生效。', 'success')
      await loadCurrentIds()
    } else {
      showMessage(result.error || '还原失败', 'error')
    }
  } catch (error) {
    const err = error as Error
    showMessage(err.message || '还原失败', 'error')
  }
}

const checkUpdate = async () => {
  try {
    const result = await window.electron.ipcRenderer.invoke('check-updates')
    if (result) {
      updateInfo.value = result
      showMessage(`发现新版本 ${result.latestVersion}，点击查看详情`, 'warning')
    }
  } catch (error) {
    console.error('检查更新失败:', error)
  }
}

const openReleasePage = async () => {
  if (updateInfo.value) {
    await window.electron.ipcRenderer.invoke('open-release-page', updateInfo.value.downloadUrl)
  }
}

const checkPythonEnvironment = async () => {
  try {
    const result = await window.electron.ipcRenderer.invoke('check-python-env')
    
    if (!result.success) {
      if (result.needsInstall) {
        showMessage(`${result.error}${result.hint ? `\n${result.hint}` : ''}`, 'error')
        if (!result.pythonPath) {  // 只有在真的找不到 Python 时才打开下载页面
          setTimeout(() => {
            window.electron.ipcRenderer.invoke('open-release-page', 'https://www.python.org/downloads/')
          }, 2000)
        }
        return false
      }
      showMessage('Python 环境检测失败: ' + result.error, 'error')
      return false
    }

    if (!result.isVersionValid) {
      showMessage(`需要 Python 3.8 或更高版本，当前版本: ${result.pythonVersion}`, 'error')
      setTimeout(() => {
        window.electron.ipcRenderer.invoke('open-release-page', 'https://www.python.org/downloads/')
      }, 2000)
      return false
    }

    if (!result.isDependenciesInstalled) {
      showMessage('正在安装依赖...', 'info')
      const installResult = await window.electron.ipcRenderer.invoke('install-requirements', 'workspace')
      
      if (!installResult.success) {
        showMessage('依赖安装失败: ' + installResult.error, 'error')
        return false
      }
      
      showMessage('依赖安装成功', 'success')
    }

    return true
  } catch (error) {
    showMessage('环境检测失败，请确保 Python 已添加到系统环境变量中', 'error')
    return false
  }
}

const openGithubStar = () => {
  window.electron.ipcRenderer.invoke('open-release-page', 'https://github.com/GalacticDevOps/ez-cursor-free')
}

const startKeepAlive = async () => {
  try {
    isKeepAliveRunning.value = true
    
    const shouldContinue = await new Promise<boolean>(resolve => {
      const starMessage = document.createElement('div')
      starMessage.className = 'star-message'
      starMessage.innerHTML = `
        <div class="star-content">
          <h3>感谢您的 ⭐️</h3>
          <p>如果这个工具对你有帮助，请为本项目点个 Star！</p>
          <div class="star-buttons">
            <button class="star-btn primary">去点亮 ⭐️</button>
            <button class="star-btn secondary">下次一定</button>
          </div>
        </div>
      `
      document.body.appendChild(starMessage)

      const primaryBtn = starMessage.querySelector('.star-btn.primary')
      const secondaryBtn = starMessage.querySelector('.star-btn.secondary')

      primaryBtn?.addEventListener('click', () => {
        openGithubStar()
        starMessage.remove()
        resolve(true)
      })

      secondaryBtn?.addEventListener('click', () => {
        openGithubStar()
        starMessage.remove()
        resolve(true)
      })
    })

    if (!shouldContinue) {
      isKeepAliveRunning.value = false
      return
    }

    showMessage('正在检查环境...', 'info')
    
    if (!await checkPythonEnvironment()) {
      isKeepAliveRunning.value = false
      return
    }

    showMessage('正在启动重置程序...', 'info')
    
    const result = await window.electron.ipcRenderer.invoke('run-python-script')
    
    if (result.success) {
      showMessage('已完成重置', 'success')
      // await window.electron.ipcRenderer.invoke('open-file', 'cursor_accounts.txt')
    } else {
      showMessage(result.error || '重置程序启动失败', 'error')
    }
  } catch (error) {
    const err = error as any
    const errorMessage = err.error || err.message || '执行出错'
    showMessage(errorMessage, 'error')
  } finally {
    isKeepAliveRunning.value = false
  }
}

// 初始化时检查备份状态
onMounted(async () => {
  await checkBackupExists()
  await checkUpdate()
})

loadCurrentIds()
</script>

<template>
  <div class="container">
    <div class="header">
      <svg class="cursor-logo" fill="currentColor" viewBox="0 0 69 13" xmlns="http://www.w3.org/2000/svg">
        <path d="M.61621 6.43836c0-3.50869 2.23066-5.4743 5.49005-5.4743h3.91414v2.09026H6.23091c-1.99579 0-3.35255 1.13895-3.35255 3.38404 0 2.2451 1.35676 3.38404 3.35255 3.38404h3.78949v2.0903H6.10626c-3.25939 0-5.49005-1.99582-5.49005-5.47434ZM12.0472 8.41982V.96549h2.1834v7.00164c0 1.35676.702 1.83964 1.8554 1.83964h1.3095c1.139 0 1.8554-.48288 1.8554-1.83964V.96549h2.1677v7.47008c0 2.35533-1.5588 3.47723-3.6648 3.47723h-2.0273c-2.1205 0-3.6806-1.1232-3.6806-3.49298h.0013ZM23.7734.96549h6.4716c2.2149 0 3.3223 1.18487 3.3223 3.08749 0 1.21636-.5773 2.19917-1.4971 2.46422.9513.10891 1.404.79517 1.404 1.62182v3.77378H31.275V8.65338c0-.57734-.1719-.9828-.9513-.9828h-4.3511v4.24222h-2.1992V.96548Zm6.1763 4.66338c.9986 0 1.404-.53011 1.404-1.30952 0-.84241-.4054-1.29379-1.4341-1.29379h-3.9457v2.60463h3.9772l-.0014-.00132ZM35.5162 9.83815h6.0359c.7334 0 1.2006-.40545 1.2006-1.13895 0-.76367-.4829-1.06022-1.2479-1.1232l-3.0416-.23356c-1.9183-.1404-3.2278-1.10746-3.2278-3.16623 0-2.04302 1.4499-3.21214 3.3525-3.21214h5.9729v2.07451h-5.8482c-.8424 0-1.2794.40545-1.2794 1.1232 0 .74793.4684 1.06022 1.2951 1.13895l3.0875.21781c1.8869.14041 3.1347 1.13895 3.1347 3.15048 0 1.93408-1.3252 3.24368-3.2436 3.24368h-6.1921V9.83815h.0014ZM46.0576 6.42277c0-3.32237 2.4013-5.64488 5.6147-5.64488h.0315c3.2122 0 5.6305 2.32382 5.6305 5.64488 0 3.3368-2.417 5.67633-5.6305 5.67633h-.0315c-3.2121 0-5.6147-2.33953-5.6147-5.67633Zm5.6305 3.55593c1.98 0 3.4312-1.404 3.4312-3.54018 0-2.12044-1.4499-3.54019-3.4312-3.54019-1.9656 0-3.4156 1.41975-3.4156 3.54019 0 2.13618 1.45 3.54018 3.4156 3.54018ZM59.0635.96549h6.4715c2.2149 0 3.3224 1.18487 3.3224 3.08749 0 1.21636-.5774 2.19917-1.4972 2.46422.9513.10891 1.404.79517 1.404 1.62182v3.77378h-2.1991V8.65338c0-.57734-.1719-.9828-.9514-.9828h-4.3511v4.24222h-2.1991V.96548Zm6.1763 4.66338c.9985 0 1.404-.53011 1.404-1.30952 0-.84241-.4055-1.29379-1.4342-1.29379H61.264v2.60463h3.9771l-.0013-.00132Z"></path>
      </svg>
    </div>

    <div class="content-card">
      <div class="section">
        <h2>配置文件路径</h2>
        <div class="path">{{ configPath }}</div>
      </div>

      <div class="section" v-if="currentIds">
        <h2>当前 ID</h2>
        <div class="id-grid">
          <div class="id-item">
            <span class="label">Machine ID</span>
            <span class="value">{{ currentIds.machineId }}</span>
          </div>
          <div class="id-item">
            <span class="label">Mac Machine ID</span>
            <span class="value">{{ currentIds.macMachineId }}</span>
          </div>
          <div class="id-item">
            <span class="label">Dev Device ID</span>
            <span class="value">{{ currentIds.devDeviceId }}</span>
          </div>
          <div class="id-item">
            <span class="label">SQM ID</span>
            <span class="value">{{ currentIds.sqmId }}</span>
          </div>
        </div>
      </div>

      <div class="section function-section">
        <h2>功能区</h2>
        <div class="function-controls">
          <div class="main-controls">
            <button 
              class="primary-btn"
              :class="{ 'loading': isKeepAliveRunning }"
              :disabled="isKeepAliveRunning"
              @click="startKeepAlive"
            >
              {{ isKeepAliveRunning ? '重置中...' : '一键重置' }}
            </button>

            <button 
              class="primary-btn"
              :class="{ 
                'loading': isLoading,
                'disabled': setReadOnly
              }" 
              @click="modifyIds"
              :disabled="isLoading || setReadOnly"
            >
              {{ isLoading ? '修改中...' : '修改 ID' }}
            </button>
          </div>

          <div class="backup-controls">
            <button 
              class="secondary-btn"
              @click="backupStorage"
              :disabled="isLoading || !currentIds.configPath"
            >
              备份
            </button>
            <button 
              class="secondary-btn"
              @click="restoreStorage"
              :disabled="isLoading || setReadOnly || !backupExists"
            >
              还原
            </button>
          </div>

          <label class="toggle-option">
            <input 
              type="checkbox" 
              v-model="setReadOnly"
            >
            <span class="toggle-label">只读</span>
          </label>
        </div>
      </div>
    </div>

    <div class="message-container" v-if="message">
      <div class="message" :class="{ 
        'show': message, 
        'error': messageType === 'error',
        'warning': messageType === 'warning',
        'info': messageType === 'info'
      }">
        <svg class="message-icon" viewBox="0 0 24 24">
          <path v-if="messageType === 'success'" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm4.59-12.42L10 14.17l-2.59-2.58L6 13l4 4 8-8z"/>
          <path v-else-if="messageType === 'error'" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
          <path v-else d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-4h2v-2h-2v2zm0-4h2V8h-2v4z"/>
        </svg>
        <span class="message-text">{{ message }}</span>
        <button class="message-close" @click="closeMessage">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
      </div>
    </div>

    <div 
      v-if="updateInfo" 
      class="update-banner"
      @click="openReleasePage"
    >
      <div class="update-content">
        <svg class="update-icon" viewBox="0 0 24 24">
          <path d="M21 10.12h-6.78l2.74-2.82c-2.73-2.7-7.15-2.8-9.88-.1-2.73 2.71-2.73 7.08 0 9.79s7.15 2.71 9.88 0C18.32 15.65 19 14.08 19 12.1h2c0 1.98-.88 4.55-2.64 6.29-3.51 3.48-9.21 3.48-12.72 0-3.5-3.47-3.53-9.11-.02-12.58s9.14-3.47 12.65 0L21 3v7.12zM12.5 8v4.25l3.5 2.08-.72 1.21L11 13V8h1.5z"/>
        </svg>
        <span>发现新版本 {{ updateInfo.latestVersion }}，点击查看详情</span>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  --apple-blue: #0071e3;
  --apple-blue-hover: #0077ED;
  --background: #fbfbfd;
  --card-background: #ffffff;
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --border-color: #d2d2d7;
  --scrollbar-bg: #f1f1f1;
  --scrollbar-thumb: #c1c1c1;
  --scrollbar-thumb-hover: #a8a8a8;
}

body {
  margin: 0;
  background: var(--background);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Icons', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
  -webkit-app-region: no-drag;
}

#app {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  overflow: hidden;
}

.container {
  max-width: 980px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 500px;
  padding-top: 0;
  position: relative;
  height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 8px;
  flex-shrink: 0;
  -webkit-app-region: drag;
  padding-top: 24px;
}

.header * {
  -webkit-app-region: no-drag;
}

.cursor-logo {
  height: 16px;
  color: var(--text-primary);
}

h1 {
  font-size: 32px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

h2 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.content-card {
  background: var(--card-background);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  -webkit-app-region: no-drag;
}

.section {
  margin-bottom: 12px;
}

.section:last-child {
  margin-bottom: 0;
}

.path {
  font-size: 14px;
  color: var(--text-secondary);
  word-break: break-all;
  background: var(--background);
  padding: 8px;
  border-radius: 8px;
}

.id-grid {
  display: grid;
  gap: 8px;
  grid-template-rows: repeat(4, auto);
}

.id-item {
  display: grid;
  grid-template-columns: minmax(120px, 140px) 1fr;
  gap: 12px;
  align-items: center;
  padding: 8px;
  background: var(--background);
  border-radius: 8px;
}

.label {
  color: var(--text-secondary);
  font-size: 14px;
}

.value {
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
}

.actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.primary-btn {
  background: var(--apple-blue);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 980px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 120px;
}

.primary-btn:hover:not(:disabled) {
  background: var(--apple-blue-hover);
}

.primary-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--text-secondary);
}

.primary-btn.disabled:hover {
  background: var(--text-secondary);
}

.primary-btn:disabled {
  cursor: not-allowed;
}

.primary-btn.loading {
  position: relative;
  color: transparent;
}

.primary-btn.loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  top: 50%;
  left: 50%;
  margin: -8px 0 0 -8px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s infinite linear;
}

.toggle-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-option input {
  margin: 0;
}

.toggle-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.message-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  justify-content: center;
  width: 100%;
  max-width: 480px;
  padding: 0 20px;
  box-sizing: border-box;
}

.message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  background: #67c23a;
  color: #fff;
  font-size: 14px;
  opacity: 0;
  transform: translateY(-20px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 100%;
  position: relative;
  pointer-events: auto;
  line-height: 1.4;
  text-align: left;
  padding-right: 40px;
}

.message.error {
  background: #f56c6c;
}

.message.warning {
  background: #e6a23c;
}

.message.info {
  background: var(--apple-blue);
}

.message.show {
  opacity: 1;
  transform: translateY(0);
}

.message-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
  flex-shrink: 0;
}

.message.warning .message-icon {
  fill: #fff;
  opacity: 0.9;
}

.message-close {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: currentColor;
  opacity: 0.8;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
  pointer-events: auto;
  flex-shrink: 0;
}

.message-close:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

.message-close svg {
  fill: currentColor;
  width: 14px;
  height: 14px;
}

.message.warning .message-close svg {
  fill: #fff;
  opacity: 0.9;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .container {
    padding: 12px;
    height: 500px;
  }
  
  h1 {
    font-size: 24px;
  }
  
  .content-card {
    padding: 12px;
  }
  
  .id-item {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  
  .actions {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .primary-btn {
    width: 100%;
  }

  ::-webkit-scrollbar {
    width: 4px;
    height: 4px;
  }
  
  ::-webkit-scrollbar-thumb {
    border-width: 1px;
  }

  .message {
    min-width: auto;
    width: calc(100vw - 32px);
    padding-right: 32px;
  }
}

@media (max-height: 600px) {
  .header {
    margin-bottom: 4px;
  }

  .cursor-logo {
    height: 12px;
  }

  h1 {
    font-size: 20px;
  }

  h2 {
    font-size: 16px;
    margin-bottom: 8px;
  }

  .content-card {
    padding: 16px;
  }

  .id-grid {
    gap: 8px;
  }

  .actions {
    margin-top: 16px;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #000000;
    --card-background: #1c1c1e;
    --text-primary: #ffffff;
    --text-secondary: #86868b;
    --border-color: #38383a;
    --scrollbar-bg: #2c2c2e;
    --scrollbar-thumb: #424244;
    --scrollbar-thumb-hover: #48484a;
  }
}

.backup-actions {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}

.secondary-btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--button-secondary-bg);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.secondary-btn:hover:not(:disabled) {
  background: var(--button-secondary-hover);
}

.secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.update-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: var(--apple-blue);
  color: white;
  padding: 4px 8px;
  text-align: center;
  cursor: pointer;
  z-index: 1000;
  transition: background-color 0.2s;
  font-size: 12px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.95;
}

.update-banner:hover {
  background: var(--apple-blue-hover);
  opacity: 1;
}

.update-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.update-icon {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.keep-alive-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.keep-alive-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-text {
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--background);
}

.status-text.info {
  color: var(--apple-blue);
  background: rgba(0, 113, 227, 0.1);
}

.status-text.success {
  color: #52c41a;
  background: rgba(82, 196, 26, 0.1);
}

.status-text.error {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

/* 保活按钮样式 */
.keep-alive-btn {
  background: var(--apple-blue);
  order: -1; /* 确保保活按钮在最前面 */
}

.keep-alive-btn.loading {
  position: relative;
  color: transparent;
}

.keep-alive-btn.loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  top: 50%;
  left: 50%;
  margin: -8px 0 0 -8px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s infinite linear;
}

/* 消息提示样式优化 */
.message {
  min-width: 240px;
  max-width: 480px;
  text-align: center;
}

.message.info {
  background: var(--apple-blue);
}

@media (max-width: 768px) {
  .actions {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .keep-alive-btn {
    order: 0;
  }
}

/* 功能区样式 */
.function-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.function-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.function-item {
  display: flex;
  gap: 8px;
}

.function-item button {
  flex: 1;
}

.backup-group {
  display: flex;
  gap: 8px;
}

.toggle-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

/* 按钮样式优化 */
.primary-btn, .secondary-btn {
  width: 100%;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.keep-alive-btn {
  background: var(--apple-blue);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .function-grid {
    grid-template-columns: 1fr;
  }

  .backup-group {
    flex-direction: row;
  }

  .backup-group button {
    flex: 1;
  }
}

/* 功能区样式优化 */
.function-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.function-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主要按钮组样式 */
.main-controls {
  display: flex;
  gap: 8px;
}

/* 按钮样式优化 */
.primary-btn {
  padding: 6px 12px;
  min-width: 80px;
  height: 32px;
  font-size: 13px;
  border-radius: 6px;
}

.secondary-btn {
  padding: 6px 12px;
  height: 32px;
  font-size: 13px;
  min-width: 60px;
}

/* 备份按钮组样式 */
.backup-controls {
  display: flex;
  gap: 8px;
}

/* 只读模式开关样式 */
.toggle-option {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 8px;
  background: var(--background);
  border-radius: 6px;
  min-width: 60px;
  justify-content: center;
}

.toggle-label {
  font-size: 13px;
  white-space: nowrap;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .function-controls {
    flex-wrap: wrap;
    gap: 8px;
  }

  .main-controls {
    flex: 1;
    min-width: 200px;
  }

  .backup-controls {
    flex: 1;
    min-width: 140px;
  }

  .toggle-option {
    margin-left: 0;
    flex: 0 0 auto;
  }

  .primary-btn,
  .secondary-btn {
    flex: 1;
  }
}

/* 移除不需要的样式 */
.function-grid,
.function-item,
.toggle-section {
  display: none;
}

/* 添加 info 类型的消息样式 */
.message.info {
  background: var(--apple-blue);
}

/* 移除未使用的样式 */
.keep-alive-log,
.status-text {
  display: none;
}

/* 添加消息文本样式 */
.message-text {
  flex: 1;
  min-width: 0; /* 防止文本溢出 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre-wrap; /* 保留换行符并自动换行 */
  word-wrap: break-word; /* 允许长单词换行 */
  margin-right: 4px; /* 与关闭按钮保持间距 */
}

/* 响应式调整 */
@media (max-width: 768px) {
  .message-container {
    padding: 0 16px;
  }

  .message {
    font-size: 13px;
    padding: 10px 14px;
    padding-right: 36px;
  }

  .message-text {
    line-height: 1.3;
  }
}

/* Star 消息样式 */
.star-message {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease-out;
}

.star-content {
  background: var(--card-background);
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-width: 320px;
  width: 90%;
  text-align: center;
  animation: slideUp 0.3s ease-out;
}

.star-content h3 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
}

.star-content p {
  margin: 0 0 20px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.star-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.star-btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.star-btn.primary {
  background: var(--apple-blue);
  color: white;
}

.star-btn.primary:hover {
  background: var(--apple-blue-hover);
}

.star-btn.secondary {
  background: var(--background);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.star-btn.secondary:hover {
  background: var(--button-secondary-hover);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
