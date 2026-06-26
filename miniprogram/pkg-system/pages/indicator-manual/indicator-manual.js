const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

Page({
  data: {
    memberId: null,
    query: '',
    suggestions: [],
    selected: null,
    value: '',
    recordDate: formatDateFull(new Date()),
    submitting: false,
    searchTimer: null,
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

  onUnload() {
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer)
    }
  },

  onQueryInput(e) {
    const query = e.detail.value
    this.setData({ query })
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer)
    }
    if (!query.trim()) {
      this.setData({ suggestions: [] })
      return
    }
    const timer = setTimeout(() => {
      this.fetchSuggestions(query)
    }, 300)
    this.setData({ searchTimer: timer })
  },

  clearQuery() {
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer)
    }
    this.setData({ query: '', suggestions: [] })
  },

  async fetchSuggestions(query) {
    try {
      const res = await api.get(`/api/indicators/metadata?q=${encodeURIComponent(query)}&limit=10`)
      this.setData({ suggestions: res.data || [] })
    } catch (err) {
      console.error('fetchSuggestions failed', err)
      wx.showToast({ title: err.message || '搜索失败', icon: 'none' })
    }
  },

  selectIndicator(e) {
    const idx = e.currentTarget.dataset.index
    const selected = this.data.suggestions[idx]
    this.setData({
      selected,
      suggestions: [],
      query: '',
      value: '',
    })
  },

  changeIndicator() {
    this.setData({ selected: null, value: '' })
  },

  onValueInput(e) {
    this.setData({ value: e.detail.value })
  },

  onDateChange(e) {
    this.setData({ recordDate: e.detail.value })
  },

  async submit() {
    const { memberId, selected, value, recordDate } = this.data
    const numericValue = parseFloat(value)

    if (!selected) {
      wx.showToast({ title: '请选择指标', icon: 'none' })
      return
    }
    if (isNaN(numericValue) || value.trim() === '') {
      wx.showToast({ title: '请输入有效数值', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.post('/api/indicators', {
        member_id: memberId,
        indicator_key: selected.key,
        indicator_name: selected.name,
        value: numericValue,
        unit: selected.unit,
        record_date: recordDate,
      })
      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1200)
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
      this.setData({ submitting: false })
    }
  },
})
