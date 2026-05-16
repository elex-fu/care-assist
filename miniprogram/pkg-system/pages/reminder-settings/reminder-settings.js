const api = require('../../../utils/api')

Page({
  data: {
    loading: false,
    saving: false,
    settings: {
      daily_digest: false,
      urgent_alert: false,
      review_reminder: false,
    },
  },

  onLoad() {
    this.loadSettings()
  },

  async loadSettings() {
    this.setData({ loading: true })
    try {
      const res = await api.get('/api/members/me')
      const sub = res.data.subscription_status || {}
      this.setData({
        settings: {
          daily_digest: sub.daily_digest === true,
          urgent_alert: sub.urgent_alert === true,
          review_reminder: sub.review_reminder === true,
        },
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  onToggle(e) {
    const { field } = e.currentTarget.dataset
    const { settings } = this.data
    this.setData({
      [`settings.${field}`]: !settings[field],
    })
  },

  async saveSettings() {
    const { settings } = this.data
    this.setData({ saving: true })
    try {
      await api.put('/api/members/me/subscription', {
        daily_digest: settings.daily_digest,
        urgent_alert: settings.urgent_alert,
        review_reminder: settings.review_reminder,
      })
      wx.showToast({ title: '保存成功', icon: 'success' })
      this.setData({ saving: false })
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
      this.setData({ saving: false })
    }
  },
})
