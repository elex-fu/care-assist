const api = require('../../../utils/api')
const { store } = require('../../../utils/store')

Page({
  data: {
    memberId: '',
    members: [],
    reminders: [],
    statusFilter: '', // '' | 'pending' | 'completed' | 'overdue'
    loading: false,
  },

  onLoad() {
    const members = store.members || []
    const currentMember = store.currentMember
    const memberId = currentMember ? currentMember.id : (members[0] ? members[0].id : '')
    this.setData({ members, memberId })
    if (memberId) {
      this.loadReminders(memberId)
    }
  },

  onShow() {
    const { memberId } = this.data
    if (memberId) {
      this.loadReminders(memberId)
    }
  },

  async loadReminders(memberId) {
    this.setData({ loading: true })
    try {
      let url = `/api/reminders?member_id=${memberId}`
      if (this.data.statusFilter) {
        url += `&status=${this.data.statusFilter}`
      }
      const res = await api.get(url)
      this.setData({ reminders: res.data || [] })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onMemberChange(e) {
    const idx = parseInt(e.detail.value)
    const member = this.data.members[idx]
    if (!member) return
    this.setData({ memberId: member.id })
    this.loadReminders(member.id)
  },

  setStatusFilter(e) {
    const status = e.currentTarget.dataset.status
    this.setData({ statusFilter: status })
    this.loadReminders(this.data.memberId)
  },

  goToAdd() {
    wx.navigateTo({
      url: `/pkg-system/pages/reminder-add/reminder-add?member_id=${this.data.memberId}`,
    })
  },

  goToEdit(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pkg-system/pages/reminder-add/reminder-add?member_id=${this.data.memberId}&id=${id}&edit=true`,
    })
  },

  async completeReminder(e) {
    const id = e.currentTarget.dataset.id
    if (!id) return
    try {
      await api.patch(`/api/reminders/${id}`, { status: 'completed' })
      wx.showToast({ title: '已完成', icon: 'success' })
      this.loadReminders(this.data.memberId)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },

  getTypeLabel(type) {
    const map = { vaccine: '疫苗', checkup: '体检', review: '复查', medication: '用药' }
    return map[type] || type
  },

  getStatusLabel(status) {
    const map = { pending: '待处理', completed: '已完成', overdue: '已逾期' }
    return map[status] || status
  },

  getPriorityLabel(priority) {
    const map = { critical: '紧急', high: '高', normal: '普通', low: '低' }
    return map[priority] || priority
  },
})
