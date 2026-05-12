const api = require('../../utils/api')

Page({
  data: {
    form: {
      name: '',
      gender: 'male',
      type: 'adult',
      birth_date: '',
      blood_type: '',
      allergies: [],
      chronic_diseases: [],
    },
    bloodTypes: ['A', 'B', 'AB', 'O'],
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onGenderChange(e) {
    this.setData({ 'form.gender': e.detail.value })
  },

  onTypeChange(e) {
    this.setData({ 'form.type': e.detail.value })
  },

  onBloodTypeChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ 'form.blood_type': this.data.bloodTypes[idx] })
  },

  async submit() {
    const { form } = this.data
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入姓名', icon: 'none' })
      return
    }
    try {
      await api.post(`/api/members?name=${encodeURIComponent(form.name)}&gender=${form.gender}&type=${form.type}`, {})
      wx.showToast({ title: '添加成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
    }
  },
})
