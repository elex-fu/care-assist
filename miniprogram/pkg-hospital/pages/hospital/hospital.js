const api = require('../../../utils/api')
const { getHospitalStatusLabel } = require('../../../utils/format')

Page({
  data: {
    memberId: '',
    events: [],
    loading: false,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    this.setData({ memberId })
    if (memberId) {
      this.loadEvents(memberId)
    }
  },

  async loadEvents(memberId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/hospital-events?member_id=${memberId}`)
      this.setData({ events: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToAdd() {
    wx.navigateTo({
      url: `/pkg-hospital/pages/hospital-add/hospital-add?member_id=${this.data.memberId}`,
    })
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pkg-hospital/pages/hospital-detail/hospital-detail?member_id=${this.data.memberId}&event_id=${id}`,
    })
  },

  computeDays(admissionDate, dischargeDate) {
    const start = new Date(admissionDate)
    const end = dischargeDate ? new Date(dischargeDate) : new Date()
    const diff = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1
    return diff > 0 ? diff : 1
  },

  getHospitalStatusLabel,
})
