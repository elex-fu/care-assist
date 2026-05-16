const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

const COMMON_INDICATORS = [
  { key: 'systolic_bp', name: '收缩压', unit: 'mmHg' },
  { key: 'diastolic_bp', name: '舒张压', unit: 'mmHg' },
  { key: 'heart_rate', name: '心率', unit: '次/分' },
  { key: 'fasting_glucose', name: '空腹血糖', unit: 'mmol/L' },
  { key: 'hba1c', name: '糖化血红蛋白', unit: '%' },
  { key: 'weight', name: '体重', unit: 'kg' },
  { key: 'height', name: '身高', unit: 'cm' },
  { key: 'temperature', name: '体温', unit: '°C' },
]

Page({
  data: {
    memberId: null,
    recordDate: formatDateFull(new Date()),
    rows: [
      { index: 0, value: '' },
    ],
    indicatorNames: COMMON_INDICATORS.map(i => i.name),
    submitting: false,
  },

  onLoad(options) {
    const memberId = options.member_id
    if (!memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
      return
    }
    this.setData({ memberId })
  },

  onDateChange(e) {
    this.setData({ recordDate: e.detail.value })
  },

  onRowIndicatorChange(e) {
    const idx = e.currentTarget.dataset.idx
    const index = e.detail.value
    this.setData({ [`rows[${idx}].index`]: parseInt(index) })
  },

  onRowValueInput(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({ [`rows[${idx}].value`]: e.detail.value })
  },

  addRow() {
    const rows = this.data.rows
    rows.push({ index: 0, value: '' })
    this.setData({ rows })
  },

  removeRow(e) {
    const idx = e.currentTarget.dataset.idx
    const rows = this.data.rows.filter((_, i) => i !== idx)
    if (!rows.length) {
      rows.push({ index: 0, value: '' })
    }
    this.setData({ rows })
  },

  async submitBatch() {
    const { memberId, recordDate, rows } = this.data

    const items = []
    for (const row of rows) {
      const indicator = COMMON_INDICATORS[row.index]
      const val = parseFloat(row.value)
      if (isNaN(val) || row.value.trim() === '') continue
      items.push({
        indicator_key: indicator.key,
        indicator_name: indicator.name,
        value: val,
        unit: indicator.unit,
        record_date: recordDate,
      })
    }

    if (!items.length) {
      wx.showToast({ title: '请至少填写一项有效指标', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.post('/api/indicators/batch', {
        member_id: memberId,
        items,
      })
      wx.showToast({ title: `成功添加 ${items.length} 项`, icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1200)
    } catch (err) {
      wx.showToast({ title: err.message || '提交失败', icon: 'none' })
      this.setData({ submitting: false })
    }
  },
})
