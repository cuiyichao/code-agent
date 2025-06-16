import store from '@/store'

class WebSocketService {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectTimeout = null
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    const wsUrl = import.meta.env.VITE_APP_WS_URL || 'ws://localhost:8000'
    
    this.socket = new WebSocket(wsUrl)
    
    this.socket.onopen = this.onOpen.bind(this)
    this.socket.onclose = this.onClose.bind(this)
    this.socket.onmessage = this.onMessage.bind(this)
    this.socket.onerror = this.onError.bind(this)
  }

  /**
   * Handle WebSocket open event
   */
  onOpen() {
    this.isConnected = true
    this.reconnectAttempts = 0
    store.commit('SET_SOCKET_CONNECTION', true)
    console.log('WebSocket connected')
  }

  /**
   * Handle WebSocket close event
   */
  onClose(event) {
    this.isConnected = false
    store.commit('SET_SOCKET_CONNECTION', false)
    console.log(`WebSocket disconnected: ${event.code} ${event.reason}`)
    
    this.attemptReconnect()
  }

  /**
   * Handle WebSocket message event
   */
  onMessage(event) {
    try {
      const data = JSON.parse(event.data)
      
      switch (data.type) {
        case 'ANALYSIS_COMPLETE':
          store.dispatch('analysis/fetchAnalysisResults', data.projectId)
          store.dispatch('showNotification', {
            title: 'Analysis Complete',
            message: `Analysis for project ${data.projectName} is complete`,
            type: 'success'
          })
          break
          
        case 'ANALYSIS_FAILED':
          store.dispatch('showNotification', {
            title: 'Analysis Failed',
            message: data.message || 'Analysis failed',
            type: 'error'
          })
          break
          
        case 'NOTIFICATION':
          store.dispatch('showNotification', {
            title: data.title || 'Notification',
            message: data.message,
            type: data.notificationType || 'info'
          })
          break
          
        default:
          console.log('Unknown WebSocket message type', data)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message', error)
    }
  }

  /**
   * Handle WebSocket error event
   */
  onError(error) {
    console.error('WebSocket error:', error)
    store.dispatch('showNotification', {
      title: 'Connection Error',
      message: 'Failed to connect to server',
      type: 'error'
    })
  }

  /**
   * Attempt to reconnect
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached')
      return
    }
    
    this.reconnectAttempts++
    
    const timeout = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    console.log(`Attempting to reconnect in ${timeout}ms (attempt ${this.reconnectAttempts})`)
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }
    
    this.reconnectTimeout = setTimeout(() => {
      console.log('Reconnecting...')
      this.connect()
    }, timeout)
  }

  /**
   * Send message to WebSocket server
   * @param {Object} data - Data to send
   */
  send(data) {
    if (!this.isConnected) {
      console.error('WebSocket is not connected')
      return
    }
    
    this.socket.send(JSON.stringify(data))
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
      this.isConnected = false
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }
}

// Create singleton instance
const webSocketService = new WebSocketService()

export default webSocketService 