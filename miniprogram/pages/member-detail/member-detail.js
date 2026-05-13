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
    if (id) {
      this.loadMember(id)
      this.loadTimeline(id)
      this.loadIndicators(id)
      this.loadReports(id)
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

  formatDateFull,
  getStatusColor,
  getStatusLabel,
})
