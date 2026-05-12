const api = require('../../utils/api')

Page({
  data: {
    step: 'login', // 'login' | 'register'
    creatorName: '',
    loading: false,
  },

  onInput(e) {
    this.setData({ creatorName: e.detail.value })
  },

  async onLogin() {
    this.setData({ loading: true })
    try {
      const wxRes = await wx.login()
      const res = await api.post('/api/auth/login', { code: wxRes.code })
      this.saveAndGoHome(res.data)
    } catch (err) {
      if (err.message && err.message.includes('未注册')) {
        this.setData({ step: 'register', loading: false })
      } else {
        wx.showToast({ title: err.message || '登录失败', icon: 'none' })
        this.setData({ loading: false })
      }
    }
  },

  async onRegister() {
    const { creatorName } = this.data
    if (!creatorName.trim()) {
      wx.showToast({ title: '请输入您的姓名', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const wxRes = await wx.login()
      const res = await api.post(`/api/auth/register?creator_name=${encodeURIComponent(creatorName)}`, { code: wxRes.code })
      this.saveAndGoHome(res.data)
    } catch (err) {
      wx.showToast({ title: err.message || '注册失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  saveAndGoHome(data) {
    wx.setStorageSync('access_token', data.access_token)
    wx.setStorageSync('refresh_token', data.refresh_token)
    wx.setStorageSync('current_member', data.member)
    wx.switchTab({ url: '/pages/home/home' })
  },
})