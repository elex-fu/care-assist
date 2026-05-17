const api = require('../../utils/api')
const { store, setMembers } = require('../../utils/store')
const { formatDateFull, getStatusColor, getStatusLabel, getEventTypeLabel, getOcrStatusLabel, getMemberTypeLabel } = require('../../utils/format')

Page({
  data: {
    member: null,
    activeTab: 'timeline', // timeline | indicators | reports | ai
    loading: false,
    elderMode: false,

    // Timeline
    events: [],
    showEventForm: false,
    editEventId: '',
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

    // Abnormal guide
    showAbnormalGuide: false,
    selectedIndicator: null,
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

  onShow() {
    this.setData({ elderMode: store.elderMode || false })
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
      const aiMessages = (res.data.messages || []).map(m => ({
        ...m,
        _blocks: m.role === 'assistant' ? this.parseStructuredContent(m.content) : null,
      }))
      this.setData({
        aiMessages,
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
      url: `/pkg-hospital/pages/hospital/hospital?member_id=${memberId}`,
    })
  },

  goToVaccines() {
    const memberId = this.data.member && this.data.member.id
    if (!memberId) return
    wx.navigateTo({
      url: `/pkg-child/pages/vaccine/vaccine?member_id=${memberId}`,
    })
  },

  goToMedications() {
    const memberId = this.data.member && this.data.member.id
    if (!memberId) return
    wx.navigateTo({
      url: `/pkg-medication/pages/medication/medication?member_id=${memberId}`,
    })
  },

  goToReportsPage() {
    const memberId = this.data.member && this.data.member.id
    const memberName = this.data.member && this.data.member.name
    if (!memberId) return
    wx.navigateTo({
      url: `/pages/reports/reports?member_id=${memberId}&member_name=${memberName}`,
    })
  },

  goToReportDetail(e) {
    const reportId = e.currentTarget.dataset.id
    const memberId = this.data.member && this.data.member.id
    if (!reportId || !memberId) return
    wx.navigateTo({
      url: `/pkg-system/pages/report-detail/report-detail?member_id=${memberId}&report_id=${reportId}`,
    })
  },

  // Timeline event creation and editing
  toggleEventForm() {
    const { showEventForm } = this.data
    if (showEventForm) {
      // Cancel edit
      this.setData({
        showEventForm: false,
        editEventId: '',
        eventForm: { type: 'visit', event_date: '', hospital: '', diagnosis: '', notes: '' },
      })
    } else {
      this.setData({ showEventForm: true })
    }
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
    const { member, eventForm, editEventId } = this.data
    if (!member) return
    if (!eventForm.event_date) {
      wx.showToast({ title: '请选择日期', icon: 'none' })
      return
    }

    const payload = {
      type: eventForm.type,
      event_date: eventForm.event_date,
      hospital: eventForm.hospital.trim() || undefined,
      diagnosis: eventForm.diagnosis.trim() || undefined,
      notes: eventForm.notes.trim() || undefined,
    }

    try {
      if (editEventId) {
        await api.patch(`/api/health-events/${editEventId}`, payload)
        wx.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await api.post('/api/health-events', { ...payload, member_id: member.id })
        wx.showToast({ title: '添加成功', icon: 'success' })
      }
      this.setData({
        showEventForm: false,
        editEventId: '',
        eventForm: { type: 'visit', event_date: '', hospital: '', diagnosis: '', notes: '' },
      })
      this.loadTimeline(member.id)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },

  onTimelineCardTap(e) {
    const item = e.detail && e.detail.event ? e.detail.event : null
    const eventId = item ? item.id : null
    if (!eventId || !item) return

    wx.showActionSheet({
      itemList: ['编辑', '删除'],
      itemColor: '#1E293B',
      success: (res) => {
        if (res.tapIndex === 0) {
          this.startEditEvent(eventId, item)
        } else if (res.tapIndex === 1) {
          this.deleteEvent(eventId)
        }
      },
    })
  },

  startEditEvent(eventId, item) {
    this.setData({
      editEventId: eventId,
      showEventForm: true,
      eventForm: {
        type: item.type || 'visit',
        event_date: item.event_date || '',
        hospital: item.hospital || '',
        diagnosis: item.diagnosis || '',
        notes: item.notes || '',
      },
    })
  },

  deleteEvent(eventId) {
    const { member } = this.data
    wx.showModal({
      title: '删除事件',
      content: '确认删除此时间轴事件？',
      confirmColor: '#EF4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.del(`/api/health-events/${eventId}`)
            wx.showToast({ title: '已删除', icon: 'success' })
            if (member) this.loadTimeline(member.id)
          } catch (err) {
            wx.showToast({ title: err.message || '删除失败', icon: 'none' })
          }
        }
      },
    })
  },

  formatDateFull,
  getStatusColor,
  getStatusLabel,
  getMemberTypeLabel,

  onIndicatorTap(e) {
    const id = e.currentTarget.dataset.id
    const indicator = this.data.indicators.find(i => i.id === id)
    if (!indicator) return
    if (indicator.status === 'normal') {
      wx.navigateTo({
        url: `/pages/indicators/indicators?member_id=${this.data.member.id}&indicator_key=${indicator.indicator_key}`,
      })
      return
    }
    this.setData({
      selectedIndicator: indicator,
      showAbnormalGuide: true,
    })
  },

  onGuideClose() {
    this.setData({ showAbnormalGuide: false, selectedIndicator: null })
  },

  onGuideAction(e) {
    const { action, indicator } = e.detail
    const memberId = this.data.member && this.data.member.id
    if (action === 'book_checkup') {
      wx.navigateTo({ url: `/pkg-system/pages/reminder-add/reminder-add?member_id=${memberId}&type=checkup` })
    } else if (action === 'ai_chat') {
      this.setData({ activeTab: 'ai', showAbnormalGuide: false })
    } else if (action === 'hospital') {
      wx.navigateTo({ url: `/pkg-hospital/pages/hospital-add/hospital-add?member_id=${memberId}` })
    } else if (action === 'medication') {
      wx.navigateTo({ url: `/pkg-medication/pages/medication/medication?member_id=${memberId}` })
    } else if (action === 'diet' || action === 'exercise') {
      this.setData({ activeTab: 'ai', showAbnormalGuide: false })
      setTimeout(() => {
        this.setData({
          aiInput: `${indicator.indicator_name} ${action === 'diet' ? '饮食' : '运动'}建议`,
        })
        this.sendAiMessage()
      }, 300)
    }
    this.setData({ showAbnormalGuide: false })
  },

  // Parse assistant message into structured blocks for rich rendering
  parseStructuredContent(content) {
    if (!content || content.length < 20) return null

    const blocks = []
    const lines = content.split('\n')

    const indicatorRegex = /^([一-龥a-zA-Z]+)\s+([\d.]+)\s*(g\/L|mmol\/L|U\/L|μmol\/L|umol\/L|10\^\d+\/L|10\*\*\d+\/L|mmHg|bpm|kg|cm|mg\/dL|%|°C|个\/μL|×10\^\d+\/L|×10\*\*\d+\/L|\/L|μL|ml|mL|L)?\s*([↑↓→]|正常|偏高|偏低|异常|高|低)?/
    const questionRegex = /^(\d+)\.\s*(.+)/

    let currentText = ''
    let indicatorRows = []
    let questionList = []
    let actions = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

      const indMatch = line.match(indicatorRegex)
      const qMatch = line.match(questionRegex)

      if (indMatch && indMatch[2]) {
        if (currentText) {
          blocks.push({ type: 'text', content: currentText.trim() })
          currentText = ''
        }
        indicatorRows.push({
          name: indMatch[1],
          value: indMatch[2],
          unit: indMatch[3] || '',
          status: indMatch[4] || '',
        })
      } else if (qMatch) {
        if (currentText) {
          blocks.push({ type: 'text', content: currentText.trim() })
          currentText = ''
        }
        questionList.push({ num: qMatch[1], text: qMatch[2] })
      } else {
        if (indicatorRows.length > 0) {
          blocks.push({ type: 'indicator_table', rows: indicatorRows })
          indicatorRows = []
        }
        if (questionList.length > 0) {
          blocks.push({ type: 'question_list', items: questionList })
          questionList = []
        }
        currentText += line + '\n'
      }
    }

    if (currentText) {
      blocks.push({ type: 'text', content: currentText.trim() })
    }
    if (indicatorRows.length > 0) {
      blocks.push({ type: 'indicator_table', rows: indicatorRows })
    }
    if (questionList.length > 0) {
      blocks.push({ type: 'question_list', items: questionList })
    }

    if (content.includes('就诊摘要') || content.includes('摘要') || content.includes('报告')) {
      actions.push({ label: '查看就诊摘要', action: 'view_summary' })
    }
    if (content.includes('提醒') || content.includes('添加')) {
      actions.push({ label: '添加到提醒', action: 'add_reminder' })
    }
    if (content.includes('指标') || content.includes('趋势')) {
      actions.push({ label: '查看指标趋势', action: 'view_trend' })
    }

    if (actions.length > 0) {
      blocks.push({ type: 'actions', items: actions })
    }

    const hasStructure = blocks.some(b => b.type !== 'text')
    return hasStructure ? blocks : null
  },

  onAiAction(e) {
    const action = e.currentTarget.dataset.action
    const memberId = this.data.member && this.data.member.id
    if (action === 'view_summary') {
      wx.showToast({ title: '查看摘要功能开发中', icon: 'none' })
    } else if (action === 'add_reminder') {
      wx.navigateTo({ url: `/pkg-system/pages/reminder-add/reminder-add?member_id=${memberId}` })
    } else if (action === 'view_trend') {
      this.setData({ activeTab: 'indicators' })
    }
  },
})
