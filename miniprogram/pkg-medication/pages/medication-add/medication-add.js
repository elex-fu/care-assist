const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

const FREQUENCY_OPTIONS = ['每日1次', '每日2次', '每日3次', '每周1次', '按需']

Page({
  data: {
    memberId: '',
    editId: '',
    name: '',
    dosage: '',
    frequencyIndex: 0,
    frequency: '每日1次',
    timeSlots: ['08:00'],
    startDate: formatDateFull(new Date()),
    endDate: '',
    notes: '',
    statusIndex: 0,
    status: 'active',
    statusOptions: ['active', 'paused', 'completed'],
    statusLabels: ['进行中', '已暂停', '已完成'],
  },

  onLoad(options) {
    const memberId = options.member_id
    const editId = options.id
    if (memberId) this.setData({ memberId })
    if (editId) {
      this.setData({ editId })
      this.loadMedication(editId)
    }
  },

  async loadMedication(id) {
    try {
      const res = await api.get(`/api/medications/${id}`)
      const med = res.data.medication
      const freqIdx = FREQUENCY_OPTIONS.indexOf(med.frequency)
      const statusIdx = this.data.statusOptions.indexOf(med.status)
      this.setData({
        name: med.name,
        dosage: med.dosage,
        frequencyIndex: freqIdx >= 0 ? freqIdx : 0,
        frequency: med.frequency,
        timeSlots: med.time_slots || ['08:00'],
        startDate: med.start_date,
        endDate: med.end_date || '',
        notes: med.notes || '',
        statusIndex: statusIdx >= 0 ? statusIdx : 0,
        status: med.status,
        memberId: med.member_id,
      })
      wx.setNavigationBarTitle({ title: '编辑用药' })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  onNameInput(e) {
    this.setData({ name: e.detail.value })
  },

  onDosageInput(e) {
    this.setData({ dosage: e.detail.value })
  },

  onFrequencyChange(e) {
    const idx = parseInt(e.detail.value)
    const freq = FREQUENCY_OPTIONS[idx]
    let slots = this.data.timeSlots
    if (freq === '每日1次') slots = slots.slice(0, 1)
    else if (freq === '每日2次') slots = slots.length < 2 ? [...slots, '20:00'] : slots.slice(0, 2)
    else if (freq === '每日3次') slots = slots.length < 3 ? [...slots, '12:00', '20:00'] : slots.slice(0, 3)
    else if (freq === '每周1次') slots = slots.slice(0, 1)
    this.setData({ frequencyIndex: idx, frequency: freq, timeSlots: slots })
  },

  onTimeChange(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({ [`timeSlots[${idx}]`]: e.detail.value })
  },

  onStartDateChange(e) {
    this.setData({ startDate: e.detail.value })
  },

  onEndDateChange(e) {
    this.setData({ endDate: e.detail.value })
  },

  onNotesInput(e) {
    this.setData({ notes: e.detail.value })
  },

  onStatusChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ statusIndex: idx, status: this.data.statusOptions[idx] })
  },

  async submit() {
    const { memberId, editId, name, dosage, frequency, timeSlots, startDate, status, notes, endDate } = this.data
    if (!name.trim()) {
      wx.showToast({ title: '请输入药品名称', icon: 'none' })
      return
    }
    if (!dosage.trim()) {
      wx.showToast({ title: '请输入剂量', icon: 'none' })
      return
    }

    const payload = {
      name: name.trim(),
      dosage: dosage.trim(),
      frequency,
      time_slots: timeSlots,
      start_date: startDate,
      status,
    }
    if (endDate) payload.end_date = endDate
    if (notes) payload.notes = notes.trim()

    try {
      if (editId) {
        await api.patch(`/api/medications/${editId}`, payload)
        wx.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await api.post('/api/medications', { ...payload, member_id: memberId })
        wx.showToast({ title: '添加成功', icon: 'success' })
      }
      setTimeout(() => wx.navigateBack(), 1200)
    } catch (err) {
      wx.showToast({ title: err.message || '操作失败', icon: 'none' })
    }
  },
})
