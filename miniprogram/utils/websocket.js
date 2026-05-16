const API_BASE = 'ws://localhost:8000'

class WSClient {
  constructor() {
    this.ws = null
    this.listeners = {}
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.connected = false
    this.token = null
    this.shouldReconnect = true
  }

  connect(token) {
    if (this.connected || this.ws) return
    this.token = token
    this.shouldReconnect = true

    const url = `${API_BASE}/api/ws?token=${encodeURIComponent(token)}`
    this.ws = wx.connectSocket({ url, protocols: ['health-protocol'] })

    this.ws.onOpen(() => {
      this.connected = true
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
        this.reconnectTimer = setTimeout(() => this.connect(this.token), 3000)
      }
    })

    this.ws.onError((err) => {
      console.error('WS error', err)
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
