const API_BASE = 'ws://localhost:8000'

const env = (typeof wx !== 'undefined' && wx.getAccountInfoSync)
  ? wx.getAccountInfoSync().miniProgram.envVersion
  : 'release'
const isDev = env === 'develop'
const isLocalhost = API_BASE.includes('localhost')

class WSClient {
  constructor() {
    this.ws = null
    this.listeners = {}
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.connected = false
    this.token = null
    this.shouldReconnect = true
    this.reconnectCount = 0
    this.maxReconnect = (isDev && isLocalhost) ? 0 : 5
  }

  connect(token) {
    if (this.connected || this.ws) return
    this.token = token
    this.shouldReconnect = true

    if (isDev && isLocalhost && this.reconnectCount > this.maxReconnect) {
      console.warn('[dev] WebSocket localhost 连接已跳过，避免开发环境报错刷屏')
      return
    }

    const url = `${API_BASE}/api/ws?token=${encodeURIComponent(token)}`
    this.ws = wx.connectSocket({ url })

    this.ws.onOpen(() => {
      this.connected = true
      this.reconnectCount = 0
      this._startHeartbeat()
      this._emit('open', {})
    })

    this.ws.onMessage((res) => {
      try {
        const data = JSON.parse(res.data)
        this._emit(data.type, data)
      } catch (e) {
        console.error('WS message parse error', e)
      }
    })

    this.ws.onClose(() => {
      this.connected = false
      this.ws = null
      this._stopHeartbeat()
      this._emit('close', {})
      if (this.shouldReconnect) {
        this.reconnectCount++
        if (this.reconnectCount <= this.maxReconnect) {
          this.reconnectTimer = setTimeout(() => this.connect(this.token), 3000)
        } else if (isDev && isLocalhost) {
          console.warn('[dev] WebSocket localhost 重试已达上限，停止自动重连')
        }
      }
    })

    this.ws.onError((err) => {
      if (isDev && isLocalhost) {
        // 开发环境 localhost 预期会失败，降级为 warn 避免红色报错刷屏
        console.warn('[dev] WebSocket localhost 连接失败（预期行为）', err.errMsg || '')
      } else {
        console.error('WS error', err)
      }
      this._emit('error', err)
    })
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this._stopHeartbeat()
    if (this.ws) {
      this.ws.close({})
      this.ws = null
    }
    this.connected = false
  }

  send(data) {
    if (!this.connected || !this.ws) return false
    this.ws.send({ data: JSON.stringify(data) })
    return true
  }

  on(type, callback) {
    this.listeners[type] = callback
  }

  off(type) {
    delete this.listeners[type]
  }

  _emit(type, data) {
    const cb = this.listeners[type]
    if (cb) cb(data)
  }

  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' })
    }, 30000)
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

// Singleton instance
let instance = null

module.exports = {
  getClient() {
    if (!instance) instance = new WSClient()
    return instance
  },
}
