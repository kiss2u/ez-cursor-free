<script setup lang="ts">
import { reactive } from 'vue'

const versions = reactive({
  node: process.versions.node,
  chrome: process.versions.chrome,
  electron: process.versions.electron
})
</script>

<template>
  <ul class="versions">
    <li class="electron-version">Electron v{{ versions.electron }}</li>
    <li class="chrome-version">Chromium v{{ versions.chrome }}</li>
    <li class="node-version">Node v{{ versions.node }}</li>
  </ul>
</template>
