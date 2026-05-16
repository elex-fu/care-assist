const api = require('../../utils/api')

Page({
  data: {
    keyword: '',
    results: [],
    loading: false,
    searched: false,
  },

  onInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  onConfirm() {
    this.doSearch()
  },

  clearKeyword() {
    this.setData({ keyword: '', results: [], searched: false })
  },

  async doSearch() {
    const { keyword } = this.data
    const trimmed = keyword.trim()
    if (!trimmed) return

    this.setData({ loading: true, searched: true })
    try {
      const res = await api.get(`/api/search?q=${encodeURIComponent(trimmed)}&limit=20`)
      this.setData({ results: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '搜索失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  getGroupLabel(entityType) {
    const map = {
      indicator: '指标',
      report: '报告',
      health_event: '健康事件',
      hospital_event: '住院',
      reminder: '提醒',
      vaccine: '疫苗',
    }
    return map[entityType] || '其他'
  },

  getResultIcon(entityType) {
    const map = {
      indicator: '📊',
      report: '📄',
      health_event: '📅',
      hospital_event: '🏥',
      reminder: '⏰',
      vaccine: '💉',
    }
    return map[entityType] || '📋'
  },

  onResultTap(e) {
    const item = e.currentTarget.dataset.item
    if (!item) return

    switch (item.entity_type) {
      case 'indicator':
        wx.navigateTo({
          url: `/pages/member-detail/member-detail?id=${item.member_id}&tab=indicators`,
        })
        break
      case 'report':
        wx.navigateTo({
          url: `/pkg-system/pages/report-detail/report-detail?member_id=${item.member_id}&report_id=${item.id}`,
        })
        break
      case 'hospital_event':
        wx.navigateTo({
          url: `/pkg-hospital/pages/hospital-detail/hospital-detail?member_id=${item.member_id}&event_id=${item.id}`,
        })
        break
      case 'health_event':
        wx.navigateTo({
          url: `/pages/member-detail/member-detail?id=${item.member_id}&tab=timeline`,
        })
        break
      default:
        wx.navigateTo({
          url: `/pages/member-detail/member-detail?id=${item.member_id}`,
        })
    }
  },

  askAi() {
    wx.switchTab({ url: '/pages/ai/ai' })
  },
})
