Page({
  data: {
    status: 'loading',
  },

  onLoad() {
    this.checkLogin()
  },

  async checkLogin() {
    const token = wx.getStorageSync('access_token')
    if (token) {
      wx.switchTab({ url: '/pages/home/home' })
    } else {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },
})
