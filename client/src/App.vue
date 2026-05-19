<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const isFullScreen = computed(() => route.meta?.fullscreen === true)
</script>

<template>
  <div class="app-root" :class="{ fullscreen: isFullScreen }">
    <header v-if="!isFullScreen" class="app-header">
      <div class="brand">
        <span class="brand-emoji">🗺</span>
        <span class="brand-text">旅游数据可视化</span>
      </div>
      <nav class="app-nav">
        <RouterLink to="/">大屏</RouterLink>
        <RouterLink to="/explore">筛选探索</RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-root { min-height: 100vh; display: flex; flex-direction: column; background: #f5f7fa; }
.app-root.fullscreen { background: #0a0e1a; }
.app-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 24px; background: #ffffff; border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.brand { display: flex; gap: 8px; align-items: center; font-weight: 600; font-size: 16px; }
.brand-emoji { font-size: 20px; }
.app-nav { display: flex; gap: 20px; }
.app-nav a { color: #64748b; text-decoration: none; font-weight: 500; padding: 6px 12px; border-radius: 6px; }
.app-nav a:hover { background: #f1f5f9; }
.app-nav a.router-link-active { color: #2563eb; background: #eff6ff; }
.app-main { flex: 1; min-width: 0; }
</style>
