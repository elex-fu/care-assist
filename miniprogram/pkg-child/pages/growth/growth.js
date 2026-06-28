const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

const TYPE_OPTIONS = [
  { key: 'height', name: '身高', unit: 'cm' },
  { key: 'weight', name: '体重', unit: 'kg' },
  { key: 'head_circumference', name: '头围', unit: 'cm' },
  { key: 'bmi', name: 'BMI', unit: 'kg/m²' },
]

Page({
  data: {
    memberId: null,
    records: [],
    percentileCurve: [],
    typeIndex: 0,
    typeOptions: TYPE_OPTIONS,
    showAddForm: false,
    value: '',
    recordedAt: formatDateFull(new Date()),
    submitting: false,
  },

  onLoad(options) {
    const memberId = options.member_id
    if (!memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.setData({ memberId })
    this.loadRecords()
  },

  async loadRecords() {
    const { memberId, typeOptions, typeIndex } = this.data
    const type = typeOptions[typeIndex].key
    try {
      const res = await api.get(`/api/child/growth/chart?member_id=${memberId}&record_type=${type}`)
      const chartData = res.data || {}
      this.setData({
        records: chartData.records || [],
        percentileCurve: chartData.percentile_curve || [],
      })
      if (chartData.records && chartData.records.length) {
        this.drawChart(chartData)
      }
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  drawChart(chartData) {
    const ctx = wx.createCanvasContext('growthChart')
    const padding = { top: 20, right: 16, bottom: 32, left: 48 }
    const query = wx.createSelectorQuery().in(this)
    query.select('.growth-chart').boundingClientRect((rect) => {
      if (!rect) return
      const width = rect.width
      const height = rect.height
      const chartW = width - padding.left - padding.right
      const chartH = height - padding.top - padding.bottom

      const records = [...(chartData.records || [])].sort(
        (a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)
      )
      const curve = chartData.percentile_curve || []

      // Collect all Y values (records + percentile curve) to set common scale.
      const allValues = records.map(r => parseFloat(r.value))
      curve.forEach(p => {
        allValues.push(p.p3, p.p97)
      })
      const minValue = Math.min(...allValues)
      const maxValue = Math.max(...allValues)
      const valueRange = (maxValue - minValue) || 1
      const valueAt = (v) => padding.top + chartH - ((v - minValue) / valueRange) * chartH

      // X scale: use age in months (from curve or records).
      const minAge = curve.length ? curve[0].age_months : 0
      const maxAge = curve.length ? curve[curve.length - 1].age_months : (records[0].age_months || 12)
      const ageRange = (maxAge - minAge) || 1
      const xAt = (age) => padding.left + ((age - minAge) / ageRange) * chartW

      // Background
      ctx.setFillStyle('#FFFFFF')
      ctx.fillRect(0, 0, width, height)

      // Grid lines
      ctx.setStrokeStyle('#F1F5F9')
      ctx.setLineWidth(1)
      for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH / 4) * i
        ctx.beginPath()
        ctx.moveTo(padding.left, y)
        ctx.lineTo(padding.left + chartW, y)
        ctx.stroke()
      }

      // Axes
      ctx.setStrokeStyle('#CBD5E1')
      ctx.beginPath()
      ctx.moveTo(padding.left, padding.top)
      ctx.lineTo(padding.left, padding.top + chartH)
      ctx.lineTo(padding.left + chartW, padding.top + chartH)
      ctx.stroke()

      // Y-axis labels
      ctx.setFillStyle('#64748B')
      ctx.setFontSize(9)
      ctx.setTextAlign('right')
      for (let i = 0; i <= 4; i++) {
        const value = maxValue - (valueRange / 4) * i
        const y = padding.top + (chartH / 4) * i + 3
        ctx.fillText(value.toFixed(1), padding.left - 6, y)
      }

      // X-axis labels (age in months)
      ctx.setFillStyle('#64748B')
      ctx.setFontSize(9)
      ctx.setTextAlign('center')
      const ageSteps = [minAge, Math.round((minAge + maxAge) / 2), maxAge]
      ageSteps.forEach(age => {
        const x = xAt(age)
        ctx.fillText(`${age}月`, x, padding.top + chartH + 14)
      })

      // WHO percentile curves
      const drawPercentileLine = (key, color, width, dashed = false) => {
        if (curve.length < 2) return
        ctx.setStrokeStyle(color)
        ctx.setLineWidth(width)
        if (dashed) {
          ctx.setLineDash([4, 4], 0)
        } else {
          ctx.setLineDash([], 0)
        }
        ctx.beginPath()
        curve.forEach((p, index) => {
          const x = xAt(p.age_months)
          const y = valueAt(p[key])
          if (index === 0) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        })
        ctx.stroke()
      }

      drawPercentileLine('p3', '#FEF2F2', 1, true)
      drawPercentileLine('p15', '#FEF3C7', 1, true)
      drawPercentileLine('p50', '#94A3B8', 2, false)
      drawPercentileLine('p85', '#FEF3C7', 1, true)
      drawPercentileLine('p97', '#FEF2F2', 1, true)
      ctx.setLineDash([], 0)

      // Legend for P50
      ctx.setFillStyle('#94A3B8')
      ctx.setFontSize(9)
      ctx.setTextAlign('left')
      ctx.fillText('P50', padding.left + 4, padding.top + 10)

      // User data points and line
      const points = records.map((r) => ({
        x: xAt(r.age_months != null ? r.age_months : 0),
        y: valueAt(parseFloat(r.value)),
        value: r.value,
        age: r.age_months,
        status: r.status,
      }))

      if (points.length > 1) {
        ctx.setStrokeStyle('#2563EB')
        ctx.setLineWidth(2)
        ctx.beginPath()
        ctx.moveTo(points[0].x, points[0].y)
        for (let i = 1; i < points.length; i++) {
          ctx.lineTo(points[i].x, points[i].y)
        }
        ctx.stroke()
      }

      // Points
      points.forEach((p) => {
        const color = p.status === 'normal' ? '#2563EB' : (p.status === 'watch' ? '#F59E0B' : '#EF4444')
        ctx.setFillStyle(color)
        ctx.beginPath()
        ctx.arc(p.x, p.y, 5, 0, Math.PI * 2)
        ctx.fill()
      })

      ctx.draw()
    }).exec()
  },

  onTypeChange(e) {
    this.setData({ typeIndex: parseInt(e.detail.value) })
    this.loadRecords()
  },

  openAddForm() {
    this.setData({
      showAddForm: true,
      value: '',
      recordedAt: formatDateFull(new Date()),
    })
  },

  closeAddForm() {
    this.setData({ showAddForm: false })
  },

  onValueInput(e) {
    this.setData({ value: e.detail.value })
  },

  onDateChange(e) {
    this.setData({ recordedAt: e.detail.value })
  },

  async submit() {
    const { memberId, typeOptions, typeIndex, value, recordedAt } = this.data
    const typeInfo = typeOptions[typeIndex]
    const numericValue = parseFloat(value)

    if (isNaN(numericValue) || value.trim() === '') {
      wx.showToast({ title: '请输入有效数值', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.post('/api/child/growth', {
        member_id: memberId,
        record_type: typeInfo.key,
        value: numericValue,
        unit: typeInfo.unit,
        recorded_at: recordedAt,
      })
      wx.showToast({ title: '保存成功', icon: 'success' })
      this.setData({ showAddForm: false, submitting: false })
      this.loadRecords()
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
      this.setData({ submitting: false })
    }
  },

  async deleteRecord(e) {
    const id = e.currentTarget.dataset.id
    const res = await wx.showModal({
      title: '确认删除',
      content: '确定删除这条记录吗？',
      confirmColor: '#EF4444',
    })
    if (!res.confirm) return

    try {
      await api.del(`/api/child/growth/${id}`)
      wx.showToast({ title: '已删除', icon: 'success' })
      this.loadRecords()
    } catch (err) {
      wx.showToast({ title: err.message || '删除失败', icon: 'none' })
    }
  },

  goToMilestones() {
    wx.navigateTo({ url: `/pkg-child/pages/milestone/milestone?member_id=${this.data.memberId}` })
  },
  onAIFabTap(e) {
    const { onAIFabTap } = require('../../../utils/page-base')
    onAIFabTap(e)
  },
})
