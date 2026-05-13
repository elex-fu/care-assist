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
    let url = `/api/members?name=${encodeURIComponent(form.name)}&gender=${form.gender}&type=${form.type}`
    if (form.birth_date) {
      url += `&birth_date=${form.birth_date}`
    }
    if (form.blood_type) {
      url += `&blood_type=${form.blood_type}`
    }
    // Note: allergies and chronic_diseases are collected in form but not sent
    // because backend POST /api/members does not support them yet.
    try {
      await api.post(url, {})
      wx.showToast({ title: '添加成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      wx.showToast({ title: err.message || '添加失败', icon: 'none' })
    }
  },
})
