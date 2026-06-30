const { getApiBase } = require('./config')

const API_BASE = getApiBase()
const IS_DEV_LOCAL = API_BASE.includes('localhost') || API_BASE.includes('127.0.0.1')
const DEV_TIMEOUT_MS = 15000

let refreshingPromise = null
const MAX_RETRIES = 3
const RETRY_DELAY_BASE = 500

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function request(options, attempt = 1) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('access_token')
    const start = Date.now()
    const url = API_BASE + options.url
    const method = options.method || 'GET'
    if (IS_DEV_LOCAL) {
      console.log(`[api] ${method} ${options.url} (attempt ${attempt})`)
    }
    wx.request({
      url,
      method,
      timeout: IS_DEV_LOCAL ? DEV_TIMEOUT_MS : undefined,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.header || {}),
      },
      data: options.data,
      success: (res) => {
        const elapsed = Date.now() - start
        if (IS_DEV_LOCAL) {
          console.log(`[api] ${method} ${options.url} -> ${res.statusCode} in ${elapsed}ms`)
        }
        if (res.statusCode === 401) {
          handle401(options, resolve, reject)
          return
        }
        if (res.statusCode >= 500 && attempt <= MAX_RETRIES) {
          const backoff = RETRY_DELAY_BASE * Math.pow(2, attempt - 1)
          delay(backoff).then(() => request(options, attempt + 1).then(resolve).catch(reject))
          return
        }
        if (res.data && res.data.code !== 0) {
          reject(new Error(res.data.message || '请求失败'))
          return
        }
        resolve(res.data)
      },
      fail: (err) => {
        const elapsed = Date.now() - start
        if (IS_DEV_LOCAL) {
          console.warn(`[api] ${method} ${options.url} failed in ${elapsed}ms:`, err.errMsg || err)
        }
        if (attempt <= MAX_RETRIES) {
          const backoff = RETRY_DELAY_BASE * Math.pow(2, attempt - 1)
          delay(backoff).then(() => request(options, attempt + 1).then(resolve).catch(reject))
          return
        }
        reject(err)
      },
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

  // AI
  getQuickQuestions(memberId, pageContext = '') {
    let url = `/api/ai-conversations/quick-questions?member_id=${memberId}`
    if (pageContext) url += `&page_context=${encodeURIComponent(pageContext)}`
    return request({ url, method: 'GET' })
  },
  sendMessage(conversationId, userMessage) {
    return request({
      url: `/api/ai-conversations/${conversationId}/messages`,
      method: 'POST',
      data: { user_message: userMessage },
    })
  },
  sendStructuredMessage(conversationId, userMessage) {
    return request({
      url: `/api/ai-conversations/${conversationId}/structured-messages`,
      method: 'POST',
      data: { user_message: userMessage },
    })
  },

  // Indicators
  compareIndicators(memberId, indicatorKeys) {
    const keys = indicatorKeys.map(k => `indicator_keys=${encodeURIComponent(k)}`).join('&')
    return request({ url: `/api/indicators/compare?member_id=${memberId}&${keys}`, method: 'GET' })
  },
  getChronicTrend(memberId, packageKey, days = 180) {
    return request({
      url: `/api/indicators/chronic/${packageKey}/trend?member_id=${memberId}&days=${days}`,
      method: 'GET',
    })
  },

  // Medication
  getMedicationCalendar(memberId, yearMonth) {
    return request({
      url: `/api/medications/calendar?member_id=${memberId}&year_month=${yearMonth}`,
      method: 'GET',
    })
  },
  getMedicationLogs(memberId, date) {
    return request({
      url: `/api/medications/logs?member_id=${memberId}&date=${date}`,
      method: 'GET',
    })
  },
  updateMedicationLog(logId, payload) {
    return request({
      url: `/api/medications/logs/${logId}`,
      method: 'PATCH',
      data: payload,
    })
  },

  // Vaccine
  generateVaccineSchedule(memberId) {
    return request({ url: `/api/vaccines/schedule?member_id=${memberId}`, method: 'POST' })
  },

  // Report
  generateReportAISummary(reportId) {
    return request({ url: `/api/reports/${reportId}/ai-summary`, method: 'POST' })
  },

  // Reminder
  createReminderFromReport(payload) {
    return request({ url: '/api/reminders/from-report', method: 'POST', data: payload })
  },
  listReminders(params) {
    const qs = Object.entries(params)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&')
    return request({ url: `/api/reminders?${qs}`, method: 'GET' })
  },
  getReminderTemplateIds() {
    return request({ url: '/api/reminders/template-ids', method: 'GET' })
  },
  recordReminderSubscription(templateIds) {
    return request({ url: '/api/reminders/subscribe', method: 'POST', data: { template_ids: templateIds } })
  },
}
