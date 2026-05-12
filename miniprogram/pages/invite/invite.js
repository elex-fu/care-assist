const api = require('../../utils/api')

Page({
  data: {
    inviteLink: '',
  },

  async onLoad() {
    try {
      const res = await api.post('/api/members/invite', {})
      this.setData({ inviteLink: res.data.invite_link })
    } catch (err) {
      wx.showToast({ title: err.message || '获取失败', icon: 'none' })
    }
  },

  copyLink() {
    wx.setClipboardData({
      data: this.data.inviteLink,
      success: () => wx.showToast({ title: '已复制', icon: 'success' }),
    })
  },
})
