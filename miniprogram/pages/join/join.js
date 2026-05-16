const api = require('../../utils/api')
const { store } = require('../../utils/store')

Page({
  data: {
    token: '',
    name: '',
    loading: false,
    hasToken: false,
  },

  onLoad(options) {
    const token = options.token || ''
    this.setData({ token, hasToken: !!token })
    if (!token) {
      wx.showToast({ title: '邀请链接无效', icon: 'none' })
    }
  },

  onInput(e) {
    this.setData({ name: e.detail.value })
  },

  async join() {
    const { token, name } = this.data
    if (!token) {
      wx.showToast({ title: '邀请链接无效', icon: 'none' })
      return
    }
    if (!name.trim()) {
      wx.showToast({ title: '请输入您的姓名', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.post(`/api/members/join?token=${encodeURIComponent(token)}&name=${encodeURIComponent(name.trim())}`, {})
      const member = res.data
      // Save token and member info
      store.token = wx.getStorageSync('access_token')
      store.currentMember = member
      wx.showToast({ title: '加入成功', icon: 'success' })
      setTimeout(() => {
        wx.reLaunch({ url: '/pages/home/home' })
      }, 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '加入失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToLogin() {
    wx.reLaunch({ url: '/pages/index/index' })
  },
})
