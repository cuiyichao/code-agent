import axios from 'axios'
import store from '@/store'

// Create axios instance
const http = axios.create({
  baseURL: import.meta.env.VITE_APP_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
http.interceptors.request.use(
  config => {
    // You can add auth token here if needed
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
http.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const { status, data } = error.response || {}
    
    // Show error notification
    store.dispatch('showNotification', {
      title: 'Error',
      message: data?.message || error.message || 'Request failed',
      type: 'error'
    })
    
    if (status === 401) {
      // Handle unauthorized access
      // store.dispatch('auth/logout')
    }
    
    return Promise.reject(error)
  }
)

export default http 