Page({
  data: {
    current: 0,
  },

  onSwiperChange(e) {
    this.setData({ current: e.detail.current })
  },

  nextStep() {
    const next = this.data.current + 1
    if (next < 4) {
      this.setData({ current: next })
    }
  },

  finishOnboarding() {
    wx.setStorageSync('onboarding_completed', true)
    wx.switchTab({ url: '/pages/home/home' })
  },
})
