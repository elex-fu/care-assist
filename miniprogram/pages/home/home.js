const api = require('../../utils/api')
const { store, setMembers } = require('../../utils/store')
const { getMemberTypeLabel, getLatestStatusLabel } = require('../../utils/format')

Page({
  data: {
    family: null,
    members: [],
    aiSummary: '',
    loading: true,
    hospitalMap: {},
    elderMode: false,
  },

  onShow() {
    this.setData({ elderMode: store.elderMode || false })
    this.loadDashboard()
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
      this.checkHospitalStatus(data.members || [])
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
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

  goToSearch() {
    wx.navigateTo({ url: '/pages/search/search' })
  },

  async checkHospitalStatus(members) {
    const hospitalMap = {}
    await Promise.all(
      members.map(async (m) => {
        try {
          const res = await api.get(`/api/hospital-events?member_id=${m.id}&status=active`)
          if (res.data && res.data.length > 0) {
            hospitalMap[m.id] = res.data[0]
          }
        } catch (err) {
          // ignore
        }
      })
    )
    this.setData({ hospitalMap })
  },

  goToMemberDetail(e) {
    const id = e.currentTarget.dataset.id
    const member = this.data.members.find(m => m.id === id)
    const hospitalEvent = this.data.hospitalMap[id]

    if (hospitalEvent) {
      wx.navigateTo({
        url: `/pkg-hospital/pages/hospital-detail/hospital-detail?member_id=${id}&event_id=${hospitalEvent.id}`,
      })
      return
    }

    if (member && member.type === 'child') {
      wx.navigateTo({ url: `/pkg-child/pages/child-dashboard/child-dashboard?member_id=${id}` })
      return
    }

    wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },

  getMemberTypeLabel,
  getLatestStatusLabel,
})
