const api = require('../../../utils/api')
const { store, setMembers, setCurrentMemberId } = require('../../../utils/store')

Page({
  data: {
    members: [],
    currentMemberId: null,
    medications: [],
    loading: true,
    yearMonth: '',
    selectedDate: '',
    dayLogs: [],
    showDayDetail: false,
    dayDetailLoading: false,
    missedReminders: [],
  },

  onLoad() {
    const cachedMembers = store.members
    const currentId = store.currentMemberId
    this.setData({ yearMonth: this.formatYearMonth(new Date()) })
    if (cachedMembers && cachedMembers.length) {
      this.setData({
        members: cachedMembers,
        currentMemberId: currentId || cachedMembers[0].id,
      })
    }
    this.loadMembers()
  },

  onShow() {
    const id = this.data.currentMemberId
    if (id) this.loadMedications(id)
  },

  formatYearMonth(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  },

  async onDayTap(e) {
    const date = e.detail.date
    this.setData({ selectedDate: date, showDayDetail: true, dayDetailLoading: true })
    try {
      const res = await api.getMedicationLogs(this.data.currentMemberId, date)
      this.setData({ dayLogs: res.data || [], dayDetailLoading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ dayDetailLoading: false })
    }
  },

  closeDayDetail() {
    this.setData({ showDayDetail: false, dayLogs: [] })
  },

  async markLogStatus(e) {
    const { logId, status } = e.currentTarget.dataset
    try {
      await api.updateMedicationLog(logId, { status })
      wx.showToast({ title: status === 'taken' ? '已标记打卡' : '已标记漏服', icon: 'success' })
      const updated = this.data.dayLogs.map(log =>
        log.id === logId ? { ...log, status } : log
      )
      this.setData({ dayLogs: updated })
      this.loadMedications(this.data.currentMemberId)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },

  onMonthChange(e) {
    this.setData({ yearMonth: e.detail.yearMonth })
  },

  onAIFabTap(e) {
    const { onAIFabTap } = require('../../../utils/page-base')
    onAIFabTap(e)
  },

  async loadMembers() {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      const currentId = this.data.currentMemberId || (members[0] && members[0].id)
      this.setData({ members, currentMemberId: currentId })
      if (currentId) this.loadMedications(currentId)
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadMedications(memberId) {
    this.setData({ loading: true })
    try {
      const [medRes, reminderRes] = await Promise.all([
        api.get(`/api/medications?member_id=${memberId}`),
        api.listReminders({ member_id: memberId, type: 'medication', status: 'pending' }),
      ])
      this.setData({
        medications: medRes.data || [],
        missedReminders: reminderRes.data || [],
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goToReminderDetail(e) {
    const id = e.currentTarget.dataset.id
    const memberId = this.data.currentMemberId
    wx.navigateTo({
      url: `/pkg-system/pages/reminder-add/reminder-add?member_id=${memberId}&id=${id}&edit=true`,
    })
  },

  selectMember(e) {
    const id = e.currentTarget.dataset.id
    setCurrentMemberId(id)
    this.setData({ currentMemberId: id })
    this.loadMedications(id)
  },

  goToAdd() {
    const memberId = this.data.currentMemberId
    if (!memberId) {
      wx.showToast({ title: '请先选择成员', icon: 'none' })
      return
    }
    wx.navigateTo({ url: `/pkg-medication/pages/medication-add/medication-add?member_id=${memberId}` })
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pkg-medication/pages/medication-add/medication-add?id=${id}` })
  },

  async deleteMedication(e) {
    const id = e.currentTarget.dataset.id
    const name = e.currentTarget.dataset.name
    const res = await wx.showModal({
      title: '确认删除',
      content: `确定删除 "${name}" 吗？`,
      confirmColor: '#EF4444',
    })
    if (!res.confirm) return

    try {
      await api.del(`/api/medications/${id}`)
      wx.showToast({ title: '已删除', icon: 'success' })
      if (this.data.currentMemberId) this.loadMedications(this.data.currentMemberId)
    } catch (err) {
      wx.showToast({ title: err.message || '删除失败', icon: 'none' })
    }
  },
})
