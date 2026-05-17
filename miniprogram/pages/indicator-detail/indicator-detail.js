const api = require('../../utils/api')
const { getStatusLabel } = require('../../utils/format')

Page({
  data: {
    memberId: '',
    indicatorKey: '',
    indicatorName: '',
    unit: '',
    current: null,
    history: [],
    thresholdLower: null,
    thresholdUpper: null,
    chartRange: 'all',
    chartData: [],
  },

  onLoad(options) {
    const { member_id, indicator_key, indicator_name, unit } = options
    if (!member_id || !indicator_key) {
      wx.showToast({ title: '参数错误', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.setData({
      memberId: member_id,
      indicatorKey: indicator_key,
      indicatorName: indicator_name || indicator_key,
      unit: unit || '',
    })
    this.loadData()
  },

  async loadData() {
    try {
      const res = await api.get(`/api/indicators?member_id=${this.data.memberId}&indicator_key=${this.data.indicatorKey}`)
      const items = res.data || []
      if (items.length === 0) {
        this.setData({ history: [], current: null })
        return
      }

      const current = items[0]
      this.setData({
        current,
        history: items,
        thresholdLower: current.lower_limit != null ? Number(current.lower_limit) : null,
        thresholdUpper: current.upper_limit != null ? Number(current.upper_limit) : null,
      })

      this.prepareChartData()
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  prepareChartData() {
    const { history, chartRange } = this.data
    let filtered = [...history]

    if (chartRange !== 'all') {
      const days = parseInt(chartRange)
      const cutoff = new Date()
      cutoff.setDate(cutoff.getDate() - days)
      filtered = filtered.filter(item => new Date(item.record_date) >= cutoff)
    }

    // Sort ascending by date for chart
    filtered.sort((a, b) => new Date(a.record_date) - new Date(b.record_date))

    this.setData({ chartData: filtered }, () => {
      this.drawChart()
    })
  },

  setChartRange(e) {
    const range = e.currentTarget.dataset.range
    this.setData({ chartRange: range }, () => {
      this.prepareChartData()
    })
  },

  drawChart() {
    const { chartData, thresholdLower, thresholdUpper } = this.data
    if (chartData.length < 2) return

    const query = wx.createSelectorQuery().in(this)
    query.select('#trendCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0]) return
        const canvas = res[0].node
        const ctx = canvas.getContext('2d')
        const dpr = wx.getSystemInfoSync().pixelRatio
        const width = res[0].width
        const height = res[0].height

        canvas.width = width * dpr
        canvas.height = height * dpr
        ctx.scale(dpr, dpr)

        // Clear
        ctx.clearRect(0, 0, width, height)

        const padding = { top: 20, right: 16, bottom: 32, left: 44 }
        const chartW = width - padding.left - padding.right
        const chartH = height - padding.top - padding.bottom

        // Extract values
        const values = chartData.map(d => Number(d.value))
        const minVal = Math.min(...values, thresholdLower != null ? thresholdLower : Infinity)
        const maxVal = Math.max(...values, thresholdUpper != null ? thresholdUpper : -Infinity)
        const range = maxVal - minVal || 1
        const padRange = range * 0.15
        const yMin = Math.max(0, minVal - padRange)
        const yMax = maxVal + padRange

        // Helper: value to Y
        const getY = (v) => padding.top + chartH - ((v - yMin) / (yMax - yMin)) * chartH
        const getX = (i) => padding.left + (i / (chartData.length - 1)) * chartW

        // Draw reference range band
        if (thresholdLower != null && thresholdUpper != null) {
          const y1 = getY(thresholdUpper)
          const y2 = getY(thresholdLower)
          ctx.fillStyle = 'rgba(16, 185, 129, 0.08)'
          ctx.fillRect(padding.left, y1, chartW, y2 - y1)
        }

        // Draw grid lines (Y axis)
        ctx.strokeStyle = '#F1F5F9'
        ctx.lineWidth = 1
        const ySteps = 4
        for (let i = 0; i <= ySteps; i++) {
          const val = yMin + (yMax - yMin) * (i / ySteps)
          const y = getY(val)
          ctx.beginPath()
          ctx.moveTo(padding.left, y)
          ctx.lineTo(padding.left + chartW, y)
          ctx.stroke()

          // Y labels
          ctx.fillStyle = '#94A3B8'
          ctx.font = '10px sans-serif'
          ctx.textAlign = 'right'
          ctx.fillText(val.toFixed(1), padding.left - 6, y + 3)
        }

        // Draw line
        ctx.strokeStyle = '#2563EB'
        ctx.lineWidth = 2.5
        ctx.lineJoin = 'round'
        ctx.lineCap = 'round'
        ctx.beginPath()
        chartData.forEach((d, i) => {
          const x = getX(i)
          const y = getY(Number(d.value))
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.stroke()

        // Draw points
        chartData.forEach((d, i) => {
          const x = getX(i)
          const y = getY(Number(d.value))

          ctx.beginPath()
          ctx.arc(x, y, 4, 0, Math.PI * 2)
          ctx.fillStyle = '#2563EB'
          ctx.fill()
          ctx.lineWidth = 2
          ctx.strokeStyle = '#FFFFFF'
          ctx.stroke()
        })

        // X labels (dates)
        ctx.fillStyle = '#94A3B8'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'center'
        const labelStep = Math.max(1, Math.floor(chartData.length / 5))
        chartData.forEach((d, i) => {
          if (i % labelStep !== 0 && i !== chartData.length - 1) return
          const x = getX(i)
          const dateStr = this.formatShortDate(d.record_date)
          ctx.fillText(dateStr, x, height - 10)
        })
      })
  },

  onChartTouch(e) {
    // Placeholder for future interactive tooltip
  },

  goBack() {
    wx.navigateBack()
  },

  goToSourceReport() {
    const { current } = this.data
    if (!current || !current.source_report_id) return
    wx.navigateTo({
      url: `/pkg-system/pages/report-detail/report-detail?report_id=${current.source_report_id}`,
    })
  },

  formatDate(dateStr) {
    if (!dateStr) return '--'
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()}`
  },

  formatShortDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()}`
  },

  getStatusLabel,
})
