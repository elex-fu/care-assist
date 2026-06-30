const { compareIndicators, getChronicTrend } = require('../../utils/api')

const COLORS = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

Component({
  properties: {
    visible: Boolean,
    memberId: String,
    indicatorKeys: { type: Array, value: [] },
    packageKey: String,
    title: String,
  },
  data: {
    series: [],
    colors: COLORS,
  },
  observers: {
    'visible,memberId,indicatorKeys,packageKey': function (visible, memberId, indicatorKeys, packageKey) {
      if (visible && memberId && (packageKey || (indicatorKeys && indicatorKeys.length))) {
        this.loadData()
      }
    }
  },
  methods: {
    async loadData() {
      try {
        let series = []
        if (this.data.packageKey) {
          const res = await getChronicTrend(this.data.memberId, this.data.packageKey, 180)
          series = (res.data && res.data.series) ? res.data.series : []
        } else {
          const res = await compareIndicators(this.data.memberId, this.data.indicatorKeys)
          series = res.data && res.data.series ? res.data.series : []
        }
        this.setData({ series })
        this.drawChart(series)
      } catch (err) {
        wx.showToast({ title: err.message || '加载趋势失败', icon: 'none' })
      }
    },
    drawChart(series) {
      if (!series || !series.length) return
      const query = wx.createSelectorQuery().in(this)
      query.select('#trendCanvas').fields({ node: true, size: true }).exec((res) => {
        if (!res || !res[0]) return
        const canvas = res[0].node
        const ctx = canvas.getContext('2d')
        const dpr = wx.getSystemInfoSync().pixelRatio
        const width = res[0].width
        const height = res[0].height
        canvas.width = width * dpr
        canvas.height = height * dpr
        ctx.scale(dpr, dpr)
        ctx.clearRect(0, 0, width, height)

        const padding = { top: 24, right: 16, bottom: 32, left: 40 }
        const chartW = width - padding.left - padding.right
        const chartH = height - padding.top - padding.bottom

        // Collect all values and dates
        const allValues = []
        const allDates = new Set()
        series.forEach(s => {
          s.points.forEach(p => {
            allValues.push(p.value)
            allDates.add(p.record_date)
          })
        })
        if (!allValues.length) return

        const dates = Array.from(allDates).sort()
        const minVal = Math.min(...allValues)
        const maxVal = Math.max(...allValues)
        const valRange = maxVal - minVal || 1

        const xFor = (date) => {
          const idx = dates.indexOf(date)
          return padding.left + (dates.length <= 1 ? chartW / 2 : idx * chartW / (dates.length - 1))
        }
        const yFor = (value) => padding.top + chartH - ((value - minVal) / valRange) * chartH

        // Axes
        ctx.strokeStyle = '#E2E8F0'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(padding.left, padding.top)
        ctx.lineTo(padding.left, padding.top + chartH)
        ctx.lineTo(padding.left + chartW, padding.top + chartH)
        ctx.stroke()

        // Y-axis labels
        ctx.fillStyle = '#94A3B8'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'right'
        for (let i = 0; i <= 4; i++) {
          const v = minVal + (valRange * i / 4)
          const y = yFor(v)
          ctx.fillText(v.toFixed(1), padding.left - 6, y + 3)
        }

        // X-axis labels
        ctx.textAlign = 'center'
        dates.forEach((d, i) => {
          const x = xFor(d)
          const label = d.slice(5)
          ctx.fillText(label, x, padding.top + chartH + 14)
        })

        series.forEach((s, idx) => {
          const color = COLORS[idx % COLORS.length]
          ctx.strokeStyle = color
          ctx.fillStyle = color
          ctx.lineWidth = 2

          ctx.beginPath()
          s.points.forEach((p, i) => {
            const x = xFor(p.record_date)
            const y = yFor(p.value)
            if (i === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
          })
          ctx.stroke()

          s.points.forEach(p => {
            const x = xFor(p.record_date)
            const y = yFor(p.value)
            ctx.beginPath()
            ctx.arc(x, y, 3, 0, Math.PI * 2)
            ctx.fill()
          })
        })
      })
    },
    close() {
      this.triggerEvent('close')
    },
    noop() {}
  }
})
