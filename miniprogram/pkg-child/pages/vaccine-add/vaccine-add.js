const api = require('../../../utils/api')

Page({
  data: {
    memberId: '',
    editId: '',
    isEdit: false,
    form: {
      vaccine_name: '',
      dose: 1,
      scheduled_date: '',
      actual_date: '',
      status: 'pending',
      location: '',
      batch_no: '',
      reaction: '',
    },
    statuses: ['pending', 'completed', 'upcoming', 'overdue'],
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    const editId = options.id || ''
    const isEdit = options.edit === 'true'
    this.setData({ memberId, editId, isEdit })

    if (isEdit && editId) {
      this.loadVaccine(editId)
    }
  },

  async loadVaccine(id) {
    try {
      const res = await api.get(`/api/vaccines?member_id=${this.data.memberId}`)
      const vaccines = res.data || []
      const vaccine = vaccines.find(v => v.id === id)
      if (!vaccine) {
        wx.showToast({ title: '未找到记录', icon: 'none' })
        return
      }
      this.setData({
        form: {
          vaccine_name: vaccine.vaccine_name,
          dose: vaccine.dose,
          scheduled_date: vaccine.scheduled_date,
          actual_date: vaccine.actual_date || '',
          status: vaccine.status,
          location: vaccine.location || '',
          batch_no: vaccine.batch_no || '',
          reaction: vaccine.reaction || '',
        },
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onNumberInput(e) {
    const { field } = e.currentTarget.dataset
    const val = parseInt(e.detail.value) || 1
    this.setData({ [`form.${field}`]: val })
  },

  onDateChange(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onStatusChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ 'form.status': this.data.statuses[idx] })
  },

  async submit() {
    const { memberId, isEdit, editId, form } = this.data
    if (!form.vaccine_name.trim()) {
      wx.showToast({ title: '请输入疫苗名称', icon: 'none' })
      return
    }
    if (!form.scheduled_date) {
      wx.showToast({ title: '请选择计划日期', icon: 'none' })
      return
    }

    const payload = {
      vaccine_name: form.vaccine_name.trim(),
      dose: form.dose,
      scheduled_date: form.scheduled_date,
      status: form.status,
    }
    if (form.actual_date) payload.actual_date = form.actual_date
    if (form.location) payload.location = form.location.trim()
    if (form.batch_no) payload.batch_no = form.batch_no.trim()
    if (form.reaction) payload.reaction = form.reaction.trim()

    try {
      if (isEdit) {
        await api.patch(`/api/vaccines/${editId}`, payload)
        wx.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await api.post('/api/vaccines', { ...payload, member_id: memberId })
        wx.showToast({ title: '添加成功', icon: 'success' })
      }
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },

  async deleteVaccine() {
    const { isEdit, editId } = this.data
    if (!isEdit || !editId) return

    wx.showModal({
      title: '删除记录',
      content: '确认删除此疫苗记录？',
      confirmColor: '#EF4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.del(`/api/vaccines/${editId}`)
            wx.showToast({ title: '已删除', icon: 'success' })
            setTimeout(() => wx.navigateBack(), 1000)
          } catch (err) {
            wx.showToast({ title: err.message || '删除失败', icon: 'none' })
          }
        }
      },
    })
  },
})
