const { store, getCurrentMember, isCreator, clearAll } = require('../../utils/store')
const api = require('../../utils/api')

Page({
  data: {
    member: null,
    family: null,
    members: [],
    creator: false,
    version: '1.0.0',
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  loadData() {
    const member = getCurrentMember()
    const family = store.family
    const members = store.members || []
    this.setData({
      member,
      family,
      members,
      creator: isCreator(),
    })
  },

  goToMemberAdd() {
    wx.navigateTo({ url: '/pages/member-add/member-add' })
  },

  goToInvite() {
    wx.navigateTo({ url: '/pages/invite/invite' })
  },

  goToReminders() {
    wx.navigateTo({ url: '/pages/reminder/reminder' })
  },

  goToProfileEdit() {
    wx.navigateTo({ url: '/pages/profile-edit/profile-edit' })
  },

  goToMemberDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },

  async deleteMember(e) {
    const id = e.currentTarget.dataset.id
    const name = e.currentTarget.dataset.name
    const res = await wx.showModal({
      title: '确认删除',
      content: `确定要删除成员 "${name}" 吗？相关数据将被一并删除。`,
      confirmColor: '#EF4444',
    })
    if (!res.confirm) return

    try {
      await api.del(`/api/members/${id}`)
      wx.showToast({ title: '已删除', icon: 'success' })
      // Refresh members
      const membersRes = await api.get('/api/members')
      const members = membersRes.data.members || []
      this.setData({ members })
    } catch (err) {
      wx.showToast({ title: err.message || '删除失败', icon: 'none' })
    }
  },

  async logout() {
    const res = await wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
    })
    if (!res.confirm) return

    clearAll()
    wx.reLaunch({ url: '/pages/index/index' })
  },
})
