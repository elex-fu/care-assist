Component({
  properties: {
    src: String,
    mode: {
      type: String,
      value: 'aspectFill',
    },
    width: {
      type: String,
      value: '100%',
    },
    height: {
      type: String,
      value: '100%',
    },
    radius: {
      type: String,
      value: '0',
    },
    placeholder: {
      type: String,
      value: '#F1F5F9',
    },
  },

  data: {
    loaded: false,
    showImage: false,
  },

  ready() {
    // Use IntersectionObserver for better control than native lazy-load
    const observer = wx.createIntersectionObserver(this, { thresholds: [0.1], initialRatio: 0 })
    observer.relativeToViewport({ bottom: 100 }).observe('.lazy-image-wrap', (res) => {
      if (res.intersectionRatio > 0) {
        this.setData({ showImage: true })
        observer.disconnect()
      }
    })
  },

  methods: {
    onLoad() {
      this.setData({ loaded: true })
    },

    onError() {
      this.setData({ loaded: true })
    },
  },
})
