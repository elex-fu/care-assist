const api = require('../../utils/api')
const { store, setMembers, getMemberById } = require('../../utils/store')
const { formatDateFull, getStatusColor, getStatusLabel, getTrendArrow, getTrendLabel } = require('../../utils/format')

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
    members: [],
    currentMemberId: null,
    indicators: [],
    loading: true,
    showAddForm: false,
    showTrendPopup: false,
    trendData: null,
    elderMode: false,

    // Add form fields
    indicatorIndex: 0,
    indicatorValue: '',
    indicatorUnit: COMMON_INDICATORS[0].unit,
    recordDate: formatDateFull(new Date()),
  },

  onLoad() {
    const cachedMembers = store.members
    if (cachedMembers && cachedMembers.length) {
      this.setData({
        members: cachedMembers,
        currentMemberId: store.currentMemberId || cachedMembers[0].id,
      })
    }
    this.loadMembers()
  },

  onShow() {
    this.setData({ elderMode: store.elderMode || false })
    const id = this.data.currentMemberId
    if (id) this.loadIndicators(id)
  },

  onPullDownRefresh() {
    const id = this.data.currentMemberId
    if (id) {
      this.loadIndicators(id).finally(() => wx.stopPullDownRefresh())
    } else {
      wx.stopPullDownRefresh()
    }
  },

  async loadMembers() {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      const currentId = this.data.currentMemberId || (members[0] && members[0].id)
      this.setData({ members, currentMemberId: currentId })
      if (currentId) this.loadIndicators(currentId)
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadIndicators(memberId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/indicators?member_id=${memberId}`)
      this.setData({
        indicators: res.data || [],
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  selectMember(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ currentMemberId: id })
    this.loadIndicators(id)
  },

  async showTrend(e) {
    const { key, name } = e.currentTarget.dataset
    const memberId = this.data.currentMemberId
    if (!memberId || !key) return
    try {
      const res = await api.get(`/api/indicators/trend?member_id=${memberId}&indicator_key=${key}`)
      this.setData({
        trendData: { ...res.data, indicator_name: name || res.data.indicator_name },
        showTrendPopup: true,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载趋势失败', icon: 'none' })
    }
  },

  closeTrendPopup() {
    this.setData({ showTrendPopup: false, trendData: null })
  },

  openAddForm() {
    const member = getMemberById(this.data.currentMemberId)
    const today = formatDateFull(new Date())
    this.setData({
      showAddForm: true,
      indicatorIndex: 0,
      indicatorValue: '',
      indicatorUnit: COMMON_INDICATORS[0].unit,
      recordDate: today,
    })
  },

  goToBatch() {
    const memberId = this.data.currentMemberId
    if (!memberId) {
      wx.showToast({ title: '请先选择成员', icon: 'none' })
      return
    }
    wx.navigateTo({ url: `/pkg-system/pages/indicator-batch/indicator-batch?member_id=${memberId}` })
  },

  closeAddForm() {
    this.setData({ showAddForm: false })
  },

  onIndicatorChange(e) {
    const index = e.detail.value
    this.setData({
      indicatorIndex: index,
      indicatorUnit: COMMON_INDICATORS[index].unit,
    })
  },

  onValueInput(e) {
    this.setData({ indicatorValue: e.detail.value })
  },

  onDateChange(e) {
    this.setData({ recordDate: e.detail.value })
  },

  async submitIndicator() {
    const { currentMemberId, indicatorIndex, indicatorValue, recordDate } = this.data
    const indicator = COMMON_INDICATORS[indicatorIndex]
    const value = parseFloat(indicatorValue)

    if (!currentMemberId) {
      wx.showToast({ title: '请先选择成员', icon: 'none' })
      return
    }
    if (isNaN(value) || indicatorValue.trim() === '') {
      wx.showToast({ title: '请输入有效数值', icon: 'none' })
      return
    }

    try {
      await api.post('/api/indicators', {
        member_id: currentMemberId,
        indicator_key: indicator.key,
        indicator_name: indicator.name,
        value,
        unit: indicator.unit,
        record_date: recordDate,
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.setData({ showAddForm: false })
      this.loadIndicators(currentMemberId)
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
    }
  },

  formatDateLabel(dateStr) {
    return formatDateFull(dateStr)
  },

  preventClose() {
    // Do nothing — catches tap on sheet to prevent overlay close
  },

  getStatusColor,
  getStatusLabel,
  getTrendArrow,
  getTrendLabel,
})
