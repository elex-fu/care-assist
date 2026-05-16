const api = require('../../utils/api')
const { store } = require('../../utils/store')

Page({
  data: {
    members: [],
    memberId: '',
    exporting: false,
    exportData: null,
    showResult: false,
  },

  onLoad() {
    const members = store.members || []
    const currentMember = store.currentMember
    const memberId = currentMember ? currentMember.id : (members[0] ? members[0].id : '')
    this.setData({ members, memberId })
  },

  onMemberChange(e) {
    const idx = parseInt(e.detail.value)
    const member = this.data.members[idx]
    if (!member) return
    this.setData({ memberId: member.id, showResult: false, exportData: null })
  },

  async doExport() {
    const { memberId } = this.data
    if (!memberId) {
      wx.showToast({ title: '请选择成员', icon: 'none' })
      return
    }
    this.setData({ exporting: true })
    try {
      const res = await api.get(`/api/members/${memberId}/export`)
      this.setData({ exportData: res.data, showResult: true })
    } catch (err) {
      wx.showToast({ title: err.message || '导出失败', icon: 'none' })
    } finally {
      this.setData({ exporting: false })
    }
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
    this.setData({ showResult: false, exportData: null })
  },
})
