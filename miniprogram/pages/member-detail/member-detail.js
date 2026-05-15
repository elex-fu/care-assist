const api = require('../../utils/api')
const { store, setMembers } = require('../../utils/store')
const { formatDateFull, getStatusColor, getStatusLabel } = require('../../utils/format')

Page({
  data: {
    member: null,
    activeTab: 'timeline', // timeline | indicators | reports | ai
    loading: false,

    // Timeline
    events: [],
    showEventForm: false,
    eventForm: {
      type: 'visit',
      event_date: '',
      hospital: '',
      diagnosis: '',
      notes: '',
    },
    eventTypes: ['visit', 'lab', 'medication', 'symptom', 'hospital', 'vaccine', 'checkup', 'milestone'],

    // Indicators
    indicators: [],

    // Reports
    reports: [],

    // AI
    aiLoading: false,
    aiMessages: [],
    aiInput: '',
    aiConversationId: null,
  },

  onLoad(options) {
    const id = options.id
    const tab = options.tab
    if (id) {
      this.loadMember(id)
      this.loadTimeline(id)
      this.loadIndicators(id)
      this.loadReports(id)
    }
    if (tab && ['timeline', 'indicators', 'reports', 'ai'].includes(tab)) {
      this.setData({ activeTab: tab })
    }
  },

  async loadMember(id) {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      const member = members.find(m => m.id === id)
      this.setData({ member })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  async loadTimeline(memberId) {
    try {
      const res = await api.get(`/api/health-events?member_id=${memberId}`)
      this.setData({ events: res.data || [] })
    } catch (err) {
      console.error('loadTimeline error', err)
    }
  },

  async loadIndicators(memberId) {
    try {
      const res = await api.get(`/api/indicators?member_id=${memberId}`)
      this.setData({ indicators: res.data || [] })
    } catch (err) {
      console.error('loadIndicators error', err)
    }
  },

  async loadReports(memberId) {
    try {
      const res = await api.get(`/api/reports?member_id=${memberId}`)
      this.setData({ reports: res.data.reports || [] })
    } catch (err) {
      console.error('loadReports error', err)
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
  },

  // AI Tab helpers
  onAiInput(e) {
    this.setData({ aiInput: e.detail.value })
  },

  async sendAiMessage() {
    const { member, aiInput, aiConversationId, aiMessages } = this.data
    const text = aiInput.trim()
    if (!text || !member) return

    let convId = aiConversationId
    if (!convId) {
      try {
        const createRes = await api.post('/api/ai-conversations', {
          member_id: member.id,
          page_context: 'member_detail',
        })
        convId = createRes.data.id
        this.setData({ aiConversationId: convId })
      } catch (err) {
        wx.showToast({ title: '创建对话失败', icon: 'none' })
        return
      }
    }

    const newMessages = [...aiMessages, { role: 'user', content: text }]
    this.setData({ aiMessages: newMessages, aiInput: '', aiLoading: true })

    try {
      const res = await api.post(`/api/ai-conversations/${convId}/messages`, {
        user_message: text,
      })
      this.setData({
        aiMessages: res.data.messages || [],
        aiLoading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' })
      this.setData({ aiLoading: false })
    }
  },

  goToIndicatorsPage() {
    wx.switchTab({ url: '/pages/indicators/indicators' })
  },

  goToUploadPage() {
    wx.switchTab({ url: '/pages/upload/upload' })
  },

  goToHospitals() {
    const memberId = this.data.member && this.data.member.id
    if (!memberId) return
    wx.navigateTo({
      url: `/pages/hospital/hospital?member_id=${memberId}`,
    })
  },

  goToVaccines() {
    const memberId = this.data.member && this.data.member.id
    if (!memberId) return
    wx.navigateTo({
      url: `/pages/vaccine/vaccine?member_id=${memberId}`,
    })
  },

  goToReportDetail(e) {
    const reportId = e.currentTarget.dataset.id
    const memberId = this.data.member && this.data.member.id
    if (!reportId || !memberId) return
    wx.navigateTo({
      url: `/pages/report-detail/report-detail?member_id=${memberId}&report_id=${reportId}`,
    })
  },

  // Timeline event creation
  toggleEventForm() {
    this.setData({ showEventForm: !this.data.showEventForm })
  },

  onEventInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`eventForm.${field}`]: e.detail.value })
  },

  onEventDateChange(e) {
    this.setData({ 'eventForm.event_date': e.detail.value })
  },

  onEventTypeChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ 'eventForm.type': this.data.eventTypes[idx] })
  },

  async submitEvent() {
    const { member, eventForm } = this.data
    if (!member) return
    if (!eventForm.event_date) {
      wx.showToast({ title: '请选择日期', icon: 'none' })
      return
    }

    try {
      await api.post('/api/health-events', {
        member_id: member.id,
        type: eventForm.type,
        event_date: eventForm.event_date,
        hospital: eventForm.hospital.trim() || undefined,
        diagnosis: eventForm.diagnosis.trim() || undefined,
        notes: eventForm.notes.trim() || undefined,
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.setData({
        showEventForm: false,
        eventForm: { type: 'visit', event_date: '', hospital: '', diagnosis: '', notes: '' },
      })
      this.loadTimeline(member.id)
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
    }
  },

  formatDateFull,
  getStatusColor,
  getStatusLabel,
})
