const API_BASE = 'http://localhost:8000'

let refreshingPromise = null

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('access_token')
    wx.request({
      url: API_BASE + options.url,
      method: options.method || 'GET',
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.header || {}),
      },
      data: options.data,
      success: (res) => {
        if (res.statusCode === 401) {
          handle401(options, resolve, reject)
          return
        }
        if (res.data && res.data.code !== 0) {
          reject(new Error(res.data.message || '请求失败'))
          return
        }
        resolve(res.data)
      },
      fail: (err) => reject(err),
    })
  })
}

function handle401(originalOptions, resolve, reject) {
  if (!refreshingPromise) {
    refreshingPromise = refreshToken()
    refreshingPromise
      .then(() => {
        refreshingPromise = null
        // Retry original request
        request(originalOptions).then(resolve).catch(reject)
      })
      .catch((err) => {
        refreshingPromise = null
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('refresh_token')
        wx.reLaunch({ url: '/pages/index/index' })
        reject(err)
      })
  } else {
    // Wait for the in-flight refresh, then retry
    refreshingPromise
      .then(() => request(originalOptions).then(resolve).catch(reject))
      .catch(reject)
  }
}

function refreshToken() {
  const refreshToken = wx.getStorageSync('refresh_token')
  if (!refreshToken) {
    return Promise.reject(new Error('no refresh token'))
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/auth/refresh`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { refresh_token: refreshToken },
      success: (res) => {
        if (res.data && res.data.code === 0 && res.data.data.access_token) {
          wx.setStorageSync('access_token', res.data.data.access_token)
          resolve(res.data.data.access_token)
        } else {
          reject(new Error('refresh failed'))
        }
      },
      fail: reject,
    })
  })
}

function uploadFile(url, filePath, name = 'file', formData = {}) {
  const token = wx.getStorageSync('access_token')
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: API_BASE + url,
      filePath,
      name,
      header: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      formData,
      success: (res) => {
        try {
          const data = JSON.parse(res.data)
          if (data.code !== 0) {
            reject(new Error(data.message || '上传失败'))
            return
          }
          resolve(data)
        } catch (e) {
          reject(new Error('解析响应失败'))
        }
      },
      fail: reject,
    })
  })
}

module.exports = {
  get(url) { return request({ url, method: 'GET' }) },
  post(url, data) { return request({ url, method: 'POST', data }) },
  put(url, data) { return request({ url, method: 'PUT', data }) },
  del(url) { return request({ url, method: 'DELETE' }) },
  uploadFile,
}
