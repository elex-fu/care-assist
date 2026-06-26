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
      const res = await api.get(`/api/child/growth?member_id=${memberId}&record_type=${type}`)
      this.setData({ records: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
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
})
