const api = require('../../utils/api')

Page({
  data: {
    memberId: '',
    vaccines: [],
    loading: false,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    this.setData({ memberId })
    if (memberId) {
      this.loadVaccines(memberId)
    }
  },

  async loadVaccines(memberId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/vaccines?member_id=${memberId}`)
      this.setData({ vaccines: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToAdd() {
    wx.navigateTo({
      url: `/pages/vaccine-add/vaccine-add?member_id=${this.data.memberId}`,
    })
  },

  goToEdit(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/vaccine-add/vaccine-add?member_id=${this.data.memberId}&id=${id}&edit=true`,
    })
  },

  getStatusLabel(status) {
    const map = {
      pending: '待接种',
      completed: '已完成',
      upcoming: '即将接种',
      overdue: '已逾期',
    }
    return map[status] || status
  },

  getStatusClass(status) {
    return status || ''
  },
})
