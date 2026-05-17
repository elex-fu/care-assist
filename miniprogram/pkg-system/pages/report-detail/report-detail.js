const api = require('../../../utils/api')
const { getReportTypeLabel, getOcrStatusLabel } = require('../../../utils/format')

Page({
  data: {
    memberId: '',
    reportId: '',
    report: null,
    loading: false,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    const reportId = options.report_id || ''
    this.setData({ memberId, reportId })
    if (memberId && reportId) {
      this.loadReport(memberId, reportId)
    }
  },

  async loadReport(memberId, reportId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/reports?member_id=${memberId}`)
      const reports = res.data.reports || []
      const report = reports.find(r => r.id === reportId)
      if (!report) {
        wx.showToast({ title: '未找到报告', icon: 'none' })
        return
      }
      this.setData({ report })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  getTypeLabel: getReportTypeLabel,
  getStatusLabel: getOcrStatusLabel,
  getStatusClass(status) {
    return status || ''
  },

  addToIndicators() {
    const { memberId, report } = this.data
    if (!memberId) {
      wx.showToast({ title: '无法获取成员信息', icon: 'none' })
      return
    }
    wx.switchTab({
      url: '/pages/indicators/indicators',
      success: () => {
        wx.showToast({ title: '指标已同步到指标中心', icon: 'success' })
      },
    })
  },

  async deleteReport() {
    const { reportId, report } = this.data
    if (!reportId || !report) return

    wx.showModal({
      title: '删除报告',
      content: '确认删除此报告？删除后不可恢复。',
      confirmColor: '#EF4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.del(`/api/reports/${reportId}`)
            wx.showToast({ title: '已删除', icon: 'success' })
            setTimeout(() => wx.navigateBack(), 1000)
          } catch (err) {
            wx.showToast({ title: err.message || '删除失败', icon: 'none' })
          }
        }
      },
    })
  },
})
