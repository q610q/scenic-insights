import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as ElIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './assets/styles/main.css'

// perf #11: element-plus 通过 unplugin 按需引入 + 自动注入样式
// (见 vite.config.ts); 此处仅保留 icons 全局注册 (体积小, 全局便利)

const app = createApp(App)

// Register all Element Plus icons globally
for (const [k, v] of Object.entries(ElIconsVue)) {
  app.component(k, v as never)
}

app.use(createPinia())
app.use(router)
app.mount('#app')
