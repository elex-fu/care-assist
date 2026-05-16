const api = require('../../utils/api')

Page({
  data: {
    year: new Date().getFullYear(),
    summary: null,
    loading: false,
    members: [],
    achievements: [],
  },

  onLoad(options) {
    const year = parseInt(options.year) || new Date().getFullYear()
    this.setData({ year })
    this.loadSummary(year)
  },

  async loadSummary(year) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/summary/annual?year=${year}`)
      const data = res.data || {}
      this.setData({
        summary: data,
        members: data.members || [],
        achievements: data.achievements || [],
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  onShareAppMessage() {
    const { year, summary } = this.data
    return {
      title: `${year}年家庭健康总结 — ${summary ? summary.indicator_count + '项指标记录' : ''}`,
      path: `/pages/annual-summary/annual-summary?year=${year}`,
    }
  },
})
