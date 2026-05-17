const api = require('../../../utils/api')
const { getEventTypeLabel, getOcrStatusLabel, getStatusColor } = require('../../../utils/format')

Page({
  data: {
    memberId: '',
    eventId: '',
    event: null,
    activeTab: 'daily', // daily | watch | compare
    loading: false,

    // Daily tab
    dailyEvents: [],

    // Watch tab
    watchIndicators: [],

    // Compare tab
    compareData: null,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    const eventId = options.event_id || ''
    this.setData({ memberId, eventId })
    if (memberId && eventId) {
      this.loadEvent(memberId, eventId)
    }
  },

  async loadEvent(memberId, eventId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/hospital-events?member_id=${memberId}`)
      const events = res.data || []
      const event = events.find(e => e.id === eventId)
      if (!event) {
        wx.showToast({ title: '未找到住院记录', icon: 'none' })
        return
      }
      this.setData({ event })
      this.loadTabData('daily')
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    this.loadTabData(tab)
  },

  async loadTabData(tab) {
    const { eventId, memberId } = this.data
    if (!eventId) return

    if (tab === 'daily') {
      try {
        const res = await api.get(`/api/health-events?member_id=${memberId}`)
        this.setData({ dailyEvents: res.data || [] })
      } catch (err) {
        console.error('loadDaily error', err)
      }
    } else if (tab === 'watch') {
      try {
        const res = await api.get(`/api/hospital-events/${eventId}/watch`)
        this.setData({ watchIndicators: res.data || [] })
      } catch (err) {
        console.error('loadWatch error', err)
      }
    } else if (tab === 'compare') {
      try {
        const res = await api.get(`/api/hospital-events/${eventId}/compare`)
        this.setData({ compareData: res.data || null })
      } catch (err) {
        console.error('loadCompare error', err)
      }
    }
  },

  computeDays() {
    const event = this.data.event
    if (!event) return 0
    const start = new Date(event.admission_date)
    const end = event.discharge_date ? new Date(event.discharge_date) : new Date()
    const diff = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1
    return diff > 0 ? diff : 1
  },

  getStatusColor(status) {
    const map = { normal: '#10B981', low: '#F59E0B', high: '#F59E0B', critical: '#EF4444' }
    return map[status] || '#94A3B8'
  },

  async discharge() {
    const { eventId, event } = this.data
    if (!eventId || !event) return
    if (event.status === 'discharged') {
      wx.showToast({ title: '已出院', icon: 'none' })
      return
    }

    wx.showModal({
      title: '办理出院',
      content: '确认办理出院？',
      confirmColor: '#2563EB',
      success: async (res) => {
        if (res.confirm) {
          const today = new Date().toISOString().split('T')[0]
          try {
            await api.patch(`/api/hospital-events/${eventId}`, {
              discharge_date: today,
              status: 'discharged',
            })
            wx.showToast({ title: '出院成功', icon: 'success' })
            this.loadEvent(this.data.memberId, eventId)
          } catch (err) {
            wx.showToast({ title: err.message || '操作失败', icon: 'none' })
          }
        }
      },
    })
  },
})
