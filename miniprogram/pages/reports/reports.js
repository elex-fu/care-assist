const api = require('../../utils/api')
const { formatDateFull } = require('../../utils/format')

Page({
  data: {
    memberId: '',
    memberName: '',
    reports: [],
    loading: false,
    hasMore: false,
    page: 1,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    const memberName = options.member_name || '成员'
    this.setData({ memberId, memberName })
    if (memberId) {
      this.loadReports()
    }
  },

  onPullDownRefresh() {
    this.setData({ page: 1 })
    this.loadReports().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadReports() {
    const { memberId, page } = this.data
    if (!memberId) return
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/reports?member_id=${memberId}`)
      const reports = res.data.reports || []
      this.setData({
        reports,
        loading: false,
        hasMore: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goToReportDetail(e) {
    const reportId = e.currentTarget.dataset.id
    const { memberId } = this.data
    if (!reportId || !memberId) return
    wx.navigateTo({
      url: `/pkg-system/pages/report-detail/report-detail?member_id=${memberId}&report_id=${reportId}`,
    })
  },

  goToUpload() {
    wx.switchTab({ url: '/pages/upload/upload' })
  },

  getTypeLabel(type) {
    const map = { lab: '检验报告', diagnosis: '诊断报告', prescription: '处方', discharge: '出院小结' }
    return map[type] || '报告'
  },

  getStatusLabel(status) {
    const map = { completed: '已识别', pending: '待处理', processing: '识别中', failed: '失败' }
    return map[status] || status
  },

  getStatusClass(status) {
    return status || ''
  },

  formatDateFull,
})
