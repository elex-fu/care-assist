const api = require('../../../utils/api')
const { store, setMembers, setCurrentMemberId } = require('../../../utils/store')

Page({
  data: {
    members: [],
    currentMemberId: null,
    medications: [],
    loading: true,
  },

  onLoad() {
    const cachedMembers = store.members
    const currentId = store.currentMemberId
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
      const res = await api.get(`/api/medications?member_id=${memberId}`)
      this.setData({ medications: res.data || [], loading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
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
