Component({
  data: { safeBottom: 0 },
  lifetimes: {
    attached() {
      const sys = wx.getSystemInfoSync()
      this.setData({ safeBottom: sys.safeAreaInsetBottom || 0 })
    }
  },
  methods: {
    onTap() {
      const pages = getCurrentPages()
      const route = pages.length ? `/${pages[pages.length - 1].route}` : ''
      this.triggerEvent('tap', { pageContext: route })
    }
  }
})
