const api = require('../../utils/api')

Page({
  data: {
    member: null,
    loading: true,
  },

  onLoad(options) {
    const id = options.id
    if (id) {
      this.loadMember(id)
    }
  },

  async loadMember(id) {
    try {
      // For now, fetch family members and find the one
      const res = await api.get('/api/members')
      const members = res.data.members || []
      const member = members.find(m => m.id === id)
      this.setData({ member, loading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },
})
