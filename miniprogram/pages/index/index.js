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
      const completed = wx.getStorageSync('onboarding_completed')
      if (!completed) {
        wx.redirectTo({ url: '/pages/onboarding/onboarding' })
      } else {
        wx.switchTab({ url: '/pages/home/home' })
      }
    } else {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },
})
