const api = require('../../../utils/api')
const { store } = require('../../../utils/store')
const { formatDateFull } = require('../../../utils/format')

Page({
  data: {
    members: [],
    memberId: '',
    formatIndex: 0,
    formats: ['JSON', 'Excel', 'PDF'],
    startDate: '',
    endDate: formatDateFull(new Date()),
    exporting: false,
    exportData: null,
    showResult: false,
    downloadedFile: '',
  },

  onLoad() {
    const members = store.members || []
    const currentMember = store.currentMember
    const memberId = currentMember ? currentMember.id : (members[0] ? members[0].id : '')
    const today = formatDateFull(new Date())
    const thirtyDaysAgo = formatDateFull(new Date(Date.now() - 30 * 86400000))
    this.setData({ members, memberId, startDate: thirtyDaysAgo, endDate: today })
  },

  onMemberChange(e) {
    const idx = parseInt(e.detail.value)
    const member = this.data.members[idx]
    if (!member) return
    this.setData({ memberId: member.id, showResult: false, exportData: null, downloadedFile: '' })
  },

  onFormatChange(e) {
    this.setData({ formatIndex: parseInt(e.detail.value), showResult: false, exportData: null, downloadedFile: '' })
  },

  onStartDateChange(e) {
    this.setData({ startDate: e.detail.value })
  },

  onEndDateChange(e) {
    this.setData({ endDate: e.detail.value })
  },

  async doExport() {
    const { memberId, formatIndex, formats, startDate, endDate } = this.data
    if (!memberId) {
      wx.showToast({ title: '请选择成员', icon: 'none' })
      return
    }

    const format = formats[formatIndex]

    if (format === 'JSON') {
      this.setData({ exporting: true })
      try {
        const res = await api.get(`/api/members/${memberId}/export`)
        this.setData({ exportData: res.data, showResult: true, downloadedFile: '' })
      } catch (err) {
        wx.showToast({ title: err.message || '导出失败', icon: 'none' })
      } finally {
        this.setData({ exporting: false })
      }
      return
    }

    // Excel or PDF: use downloadFile
    this.setData({ exporting: true })
    const token = wx.getStorageSync('access_token')
    let url = `http://localhost:8000/api/export/${format.toLowerCase()}?member_id=${memberId}`
    if (format === 'Excel' && startDate && endDate) {
      url += `&start_date=${startDate}&end_date=${endDate}`
    }

    wx.downloadFile({
      url,
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ downloadedFile: res.tempFilePath, showResult: true, exportData: null })
          wx.showToast({ title: '下载成功', icon: 'success' })
        } else {
          wx.showToast({ title: '下载失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '下载失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ exporting: false })
      },
    })
  },

  previewFile() {
    const { downloadedFile } = this.data
    if (!downloadedFile) return
    wx.openDocument({
      filePath: downloadedFile,
      showMenu: true,
    })
  },

  copyData() {
    const { exportData } = this.data
    if (!exportData) return
    const text = JSON.stringify(exportData, null, 2)
    wx.setClipboardData({
      data: text,
      success: () => wx.showToast({ title: '已复制到剪贴板', icon: 'success' }),
    })
  },

  goBack() {
    this.setData({ showResult: false, exportData: null, downloadedFile: '' })
  },
})
