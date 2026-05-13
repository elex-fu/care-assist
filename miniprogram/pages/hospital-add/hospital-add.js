const api = require('../../utils/api')

Page({
  data: {
    memberId: '',
    form: {
      hospital: '',
      department: '',
      admission_date: '',
      discharge_date: '',
      diagnosis: '',
      doctor: '',
    },
  },

  onLoad(options) {
    this.setData({ memberId: options.member_id || '' })
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onDateChange(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  async submit() {
    const { memberId, form } = this.data
    if (!form.hospital.trim()) {
      wx.showToast({ title: '请输入医院名称', icon: 'none' })
      return
    }
    if (!form.admission_date) {
      wx.showToast({ title: '请选择入院日期', icon: 'none' })
      return
    }

    try {
      await api.post('/api/hospital-events', {
        member_id: memberId,
        hospital: form.hospital.trim(),
        department: form.department.trim() || undefined,
        admission_date: form.admission_date,
        discharge_date: form.discharge_date || undefined,
        diagnosis: form.diagnosis.trim() || undefined,
        doctor: form.doctor.trim() || undefined,
      })
      wx.showToast({ title: '创建成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '创建失败', icon: 'none' })
    }
  },
})
