const api = require('../../utils/api')
const { store, setMembers } = require('../../utils/store')

Page({
  data: {
    family: null,
    members: [],
    aiSummary: '',
    loading: true,
  },

  onLoad() {
    // Prefer store data to avoid flicker
    const cachedFamily = store.family
    const cachedMembers = store.members
    if (cachedFamily || (cachedMembers && cachedMembers.length)) {
      this.setData({
        family: cachedFamily,
        members: cachedMembers || [],
        loading: true,
      })
    }
    this.loadDashboard()
  },

  onShow() {
    // Refresh when coming back
    this.loadDashboard()
  },

  onPullDownRefresh() {
    this.loadDashboard().finally(() => wx.stopPullDownRefresh())
  },

  async loadDashboard() {
    try {
      const res = await api.get('/api/home/dashboard')
      const data = res.data
      setMembers(data.members || [])
      store.family = data.family
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

  goToUpload() {
    wx.switchTab({ url: '/pages/upload/upload' })
  },
})
