Component({
  data: {
    safeBottom: 0,
    windowWidth: 375,
    windowHeight: 812,
    translateX: 0,
    translateY: 0,
    animating: false,
  },

  lifetimes: {
    attached() {
      const sys = wx.getSystemInfoSync()
      this.setData({
        safeBottom: sys.safeAreaInsetBottom || 0,
        windowWidth: sys.windowWidth,
        windowHeight: sys.windowHeight,
      })
    },
  },

  methods: {
    onTap() {
      if (this._isDragging) return
      const pages = getCurrentPages()
      const route = pages.length ? `/${pages[pages.length - 1].route}` : ''
      this.triggerEvent('tap', { pageContext: route })
    },

    onTouchStart(e) {
      this._isDragging = false
      const touch = e.touches[0]
      this._startX = touch.clientX
      this._startY = touch.clientY
      this._startTranslateX = this.data.translateX
      this._startTranslateY = this.data.translateY
      this.setData({ animating: false })
    },

    onTouchMove(e) {
      const touch = e.touches[0]
      const deltaX = touch.clientX - this._startX
      const deltaY = touch.clientY - this._startY

      if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
        this._isDragging = true
      }

      const fabSize = 56
      const marginRight = 16
      const marginBottom = this.data.safeBottom + 80
      const maxX = this.data.windowWidth - fabSize - marginRight
      const maxY = this.data.windowHeight - fabSize - marginBottom

      let newX = this._startTranslateX + deltaX
      let newY = this._startTranslateY + deltaY

      // Clamp within screen bounds.
      newX = Math.max(-marginRight, Math.min(newX, maxX))
      newY = Math.max(-marginBottom, Math.min(newY, maxY))

      this.setData({ translateX: newX, translateY: newY })
    },

    onTouchEnd() {
      if (!this._isDragging) return

      const fabSize = 56
      const marginRight = 16
      const marginBottom = this.data.safeBottom + 80
      const maxX = this.data.windowWidth - fabSize - marginRight
      const halfScreen = this.data.windowWidth / 2
      const currentCenterX = marginRight + this.data.translateX + fabSize / 2

      // Snap to nearest horizontal edge.
      let targetX
      if (currentCenterX < halfScreen) {
        targetX = -marginRight + 8
      } else {
        targetX = maxX - 8
      }

      // Clamp vertical position.
      const maxY = this.data.windowHeight - fabSize - marginBottom
      const targetY = Math.max(-marginBottom + 8, Math.min(this.data.translateY, maxY - 8))

      this.setData({
        translateX: targetX,
        translateY: targetY,
        animating: true,
      })

      setTimeout(() => {
        this.setData({ animating: false })
      }, 300)
    },
  },
})
