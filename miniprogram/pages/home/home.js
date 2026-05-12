const api = require('../../utils/api')

Page({
  data: {
    family: null,
    members: [],
    aiSummary: '',
    loading: true,
  },

  onLoad() {
    this.loadDashboard()
  },

  onPullDownRefresh() {
    this.loadDashboard().finally(() => wx.stopPullDownRefresh())
  },

  async loadDashboard() {
    try {
      const res = await api.get('/api/home/dashboard')
      const data = res.data
      this.setData({
        family: data.family,
        members: data.members,
        aiSummary: data.ai_summary,
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goToMemberDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },

  goToAddMember() {
    wx.navigateTo({ url: '/pages/member-add/member-add' })
  },

  goToInvite() {
    wx.navigateTo({ url: '/pages/invite/invite' })
  },
})
