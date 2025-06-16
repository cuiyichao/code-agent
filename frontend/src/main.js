import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import 'highlight.js/styles/github.css'
import webSocketService from './utils/websocket'

// Global CSS
import './assets/css/main.css'

const app = createApp(App)

// Register Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Register global components
app.component('VChart', VChart)

// Use plugins
app.use(store)
app.use(router)
app.use(ElementPlus)

// Initialize WebSocket when app is ready
app.config.globalProperties.$socket = webSocketService

// Mount the app
app.mount('#app')

// Connect to WebSocket service when app is mounted
webSocketService.connect()
