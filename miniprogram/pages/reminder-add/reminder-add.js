const api = require('../../utils/api')

Page({
  data: {
    memberId: '',
    editId: '',
    isEdit: false,
    form: {
      title: '',
      type: 'checkup',
      scheduled_date: '',
      description: '',
      priority: 'normal',
    },
    types: ['vaccine', 'checkup', 'review', 'medication'],
    priorities: ['critical', 'high', 'normal', 'low'],
  },

  onLoad(options) {
    const memberId = options.member_id || ''
    const editId = options.id || ''
    const isEdit = options.edit === 'true'
    this.setData({ memberId, editId, isEdit })

    if (isEdit && editId) {
      this.loadReminder(editId)
    }
  },

  async loadReminder(id) {
    try {
      const res = await api.get(`/api/reminders?member_id=${this.data.memberId}`)
      const reminders = res.data || []
      const reminder = reminders.find(r => r.id === id)
      if (!reminder) {
        wx.showToast({ title: '未找到提醒', icon: 'none' })
        return
      }
      this.setData({
        form: {
          title: reminder.title,
          type: reminder.type,
          scheduled_date: reminder.scheduled_date,
          description: reminder.description || '',
          priority: reminder.priority,
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

  onDateChange(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onTypeChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ 'form.type': this.data.types[idx] })
  },

  onPriorityChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ 'form.priority': this.data.priorities[idx] })
  },

  async submit() {
    const { memberId, isEdit, editId, form } = this.data
    if (!form.title.trim()) {
      wx.showToast({ title: '请输入标题', icon: 'none' })
      return
    }
    if (!form.scheduled_date) {
      wx.showToast({ title: '请选择计划日期', icon: 'none' })
      return
    }

    const payload = {
      title: form.title.trim(),
      type: form.type,
      scheduled_date: form.scheduled_date,
      priority: form.priority,
    }
    if (form.description) payload.description = form.description.trim()

    try {
      if (isEdit) {
        await api.patch(`/api/reminders/${editId}`, payload)
        wx.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await api.post('/api/reminders', { ...payload, member_id: memberId })
        wx.showToast({ title: '添加成功', icon: 'success' })
      }
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },

  async deleteReminder() {
    const { isEdit, editId } = this.data
    if (!isEdit || !editId) return

    wx.showModal({
      title: '删除提醒',
      content: '确认删除此提醒？',
      confirmColor: '#EF4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.del(`/api/reminders/${editId}`)
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
