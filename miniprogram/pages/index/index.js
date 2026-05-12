Page({
  data: {
    status: 'loading',
  },

  onLoad() {
    this.checkHealth()
  },

  async checkHealth() {
    try {
      const res = await wx.request({
        url: `${getApp().globalData.apiBase}/health`,
      })
      this.setData({
        status: res.data.status === 'ok' ? 'connected' : 'error',
      })
    } catch {
      this.setData({ status: 'error' })
    }
  },
})
