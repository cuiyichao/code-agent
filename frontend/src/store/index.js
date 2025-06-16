import { createStore } from 'vuex'
import projects from './modules/projects'
import analysis from './modules/analysis'

const store = createStore({
  modules: {
    projects,
    analysis
  },
  // Global state
  state: {
    darkMode: localStorage.getItem('darkMode') === 'true' || false,
    notifications: [],
    socketConnected: false
  },
  mutations: {
    TOGGLE_DARK_MODE(state) {
      state.darkMode = !state.darkMode
      localStorage.setItem('darkMode', state.darkMode)
    },
    ADD_NOTIFICATION(state, notification) {
      state.notifications.push({
        id: Date.now(),
        ...notification
      })
    },
    REMOVE_NOTIFICATION(state, id) {
      state.notifications = state.notifications.filter(notification => notification.id !== id)
    },
    SET_SOCKET_CONNECTION(state, status) {
      state.socketConnected = status
    }
  },
  actions: {
    toggleDarkMode({ commit }) {
      commit('TOGGLE_DARK_MODE')
    },
    showNotification({ commit }, notification) {
      commit('ADD_NOTIFICATION', notification)
      // Auto-remove notifications after timeout
      setTimeout(() => {
        commit('REMOVE_NOTIFICATION', notification.id)
      }, notification.timeout || 5000)
    }
  },
  getters: {
    isDarkMode: state => state.darkMode,
    allNotifications: state => state.notifications,
    isSocketConnected: state => state.socketConnected
  }
})

export default store