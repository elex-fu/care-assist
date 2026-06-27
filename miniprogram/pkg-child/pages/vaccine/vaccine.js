const api = require('../../../utils/api')
const { generateVaccineSchedule } = require('../../../utils/api')

Page({
  data: {
    memberId: '',
    vaccines: [],
    loading: false,
    generating: false,
    overdueCount: 0,
    upcomingCount: 0,
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    this.setData({ memberId })
    if (memberId) {
      this.loadVaccines(memberId)
    }
  },

  async loadVaccines(memberId) {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/vaccines?member_id=${memberId}`)
      const vaccines = res.data || []
      const { overdueCount, upcomingCount } = this.computeVaccineCounts(vaccines)
      this.setData({ vaccines, overdueCount, upcomingCount })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  computeVaccineCounts(vaccines) {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const nearDays = 7
    let overdueCount = 0
    let upcomingCount = 0
    vaccines.forEach(v => {
      if (v.status === 'overdue') {
        overdueCount++
        return
      }
      if (v.status === 'upcoming') {
        upcomingCount++
        return
      }
      if (v.status === 'pending') {
        const scheduled = v.scheduled_date ? new Date(v.scheduled_date) : null
        if (scheduled) {
          scheduled.setHours(0, 0, 0, 0)
          const diff = Math.floor((scheduled - today) / (1000 * 60 * 60 * 24))
          if (diff >= -1 && diff <= nearDays) {
            upcomingCount++
          }
        }
      }
    })
    return { overdueCount, upcomingCount }
  },

  goToAdd() {
    wx.navigateTo({
      url: `/pkg-child/pages/vaccine-add/vaccine-add?member_id=${this.data.memberId}`,
    })
  },

  goToEdit(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pkg-child/pages/vaccine-add/vaccine-add?member_id=${this.data.memberId}&id=${id}&edit=true`,
    })
  },

  async generateSchedule() {
    if (!this.data.memberId) return
    this.setData({ generating: true })
    try {
      const res = await generateVaccineSchedule(this.data.memberId)
      wx.showToast({
        title: `生成 ${res.data.records.length} 条计划`,
        icon: 'none',
      })
      this.loadVaccines(this.data.memberId)
    } catch (err) {
      wx.showToast({ title: err.message || '生成失败', icon: 'none' })
    } finally {
      this.setData({ generating: false })
    }
  },

  onAIFabTap(e) {
    const { onAIFabTap } = require('../../../utils/page-base')
    onAIFabTap(e)
  },

  getStatusLabel(status) {
    const map = {
      pending: '待接种',
      completed: '已完成',
      upcoming: '即将接种',
      overdue: '已逾期',
    }
    return map[status] || status
  },

  getStatusClass(status) {
    return status || ''
  },
})
