<template>
  <div class="main-layout" :class="{ 'dark-mode': isDarkMode }">
    <!-- Header -->
    <header class="header">
      <div class="logo">
        <router-link to="/">
          <h1>CodeAnalysis</h1>
        </router-link>
      </div>
      
      <div class="header-actions">
        <el-tooltip content="Toggle Dark Mode" placement="bottom">
          <el-button
            circle
            :icon="isDarkMode ? 'Sunny' : 'Moon'"
            @click="toggleDarkMode"
          />
        </el-tooltip>
        
        <el-badge :value="notifications.length || ''" :hidden="!notifications.length">
          <el-dropdown trigger="click" @command="handleNotificationCommand">
            <el-button circle icon="Bell" />
            <template #dropdown>
              <el-dropdown-menu v-if="notifications.length">
                <el-dropdown-item v-for="notification in notifications" :key="notification.id">
                  <div class="notification-item">
                    <div class="notification-title">{{ notification.title }}</div>
                    <div class="notification-message">{{ notification.message }}</div>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item divided command="clear">Clear All</el-dropdown-item>
              </el-dropdown-menu>
              <el-dropdown-menu v-else>
                <el-dropdown-item disabled>No notifications</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-badge>
      </div>
    </header>

    <!-- Sidebar -->
    <aside class="sidebar">
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        :router="true"
      >
        <el-menu-item index="/">
          <el-icon><Grid /></el-icon>
          <span>Projects</span>
        </el-menu-item>
        
        <el-menu-item index="/new">
          <el-icon><Plus /></el-icon>
          <span>New Project</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <div class="connection-status">
          <el-tag size="small" :type="isConnected ? 'success' : 'danger'">
            {{ isConnected ? 'Connected' : 'Disconnected' }}
          </el-tag>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <router-view />
    </main>
    
    <!-- Global notification system -->
    <el-notification
      v-for="notification in activeNotifications"
      :key="notification.id"
      :title="notification.title"
      :message="notification.message"
      :type="notification.type"
      :duration="notification.timeout"
      @close="removeNotification(notification.id)"
    />
  </div>
</template>

<script>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useStore } from 'vuex'
import { useRoute } from 'vue-router'
import webSocketService from '@/utils/websocket'

export default {
  name: 'MainLayout',
  
  setup() {
    const store = useStore()
    const route = useRoute()
    
    // Get active menu item based on route
    const activeMenu = computed(() => route.path)
    
    // Get dark mode state from store
    const isDarkMode = computed(() => store.getters.isDarkMode)
    
    // Toggle dark mode
    const toggleDarkMode = () => {
      store.dispatch('toggleDarkMode')
    }
    
    // Get notifications from store
    const notifications = computed(() => store.state.notifications)
    
    // Handle notification dropdown commands
    const handleNotificationCommand = (command) => {
      if (command === 'clear') {
        // Clear all notifications
        notifications.value.forEach(notification => {
          store.commit('REMOVE_NOTIFICATION', notification.id)
        })
      }
    }
    
    // Remove notification
    const removeNotification = (id) => {
      store.commit('REMOVE_NOTIFICATION', id)
    }
    
    // Visible notifications
    const activeNotifications = ref([])
    
    // WebSocket connection status
    const isConnected = computed(() => store.state.socketConnected)
    
    // Connect to WebSocket on component mount
    onMounted(() => {
      webSocketService.connect()
    })
    
    // Disconnect from WebSocket on component unmount
    onUnmounted(() => {
      webSocketService.disconnect()
    })
    
    return {
      activeMenu,
      isDarkMode,
      toggleDarkMode,
      notifications,
      handleNotificationCommand,
      removeNotification,
      activeNotifications,
      isConnected
    }
  }
}
</script>

<style scoped>
.main-layout {
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar main";
  grid-template-columns: 220px 1fr;
  grid-template-rows: 60px 1fr;
  height: 100vh;
}

.dark-mode {
  background-color: #121212;
  color: #eaeaea;
}

.header {
  grid-area: header;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.logo h1 {
  margin: 0;
  font-size: 1.5rem;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.sidebar {
  grid-area: sidebar;
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-footer {
  padding: 10px;
  border-top: 1px solid var(--el-border-color-light);
}

.connection-status {
  display: flex;
  justify-content: center;
}

.main-content {
  grid-area: main;
  padding: 20px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.notification-title {
  font-weight: bold;
}

.notification-message {
  font-size: 0.9em;
  opacity: 0.8;
}
</style>