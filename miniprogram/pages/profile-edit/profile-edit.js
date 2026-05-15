const api = require('../../utils/api')
const { store, setMembers } = require('../../utils/store')

Page({
  data: {
    member: null,
    form: {
      name: '',
      gender: 'male',
      birth_date: '',
      blood_type: '',
      type: 'adult',
    },
    bloodTypes: ['A', 'B', 'AB', 'O'],
    subscription: {
      daily_digest: false,
      urgent_alert: false,
      review_reminder: false,
    },
    loading: false,
  },

  async onLoad() {
    this.loadProfile()
  },

  async loadProfile() {
    this.setData({ loading: true })
    try {
      const res = await api.get('/api/members/me')
      const member = res.data
      this.setData({
        member,
        form: {
          name: member.name || '',
          gender: member.gender || 'male',
          birth_date: member.birth_date || '',
          blood_type: member.blood_type || '',
          type: member.type || 'adult',
        },
        subscription: {
          daily_digest: member.subscription_status ? member.subscription_status.daily_digest : false,
          urgent_alert: member.subscription_status ? member.subscription_status.urgent_alert : false,
          review_reminder: member.subscription_status ? member.subscription_status.review_reminder : false,
        },
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
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

  onDateChange(e) {
    this.setData({ 'form.birth_date': e.detail.value })
  },

  onSubscriptionChange(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`subscription.${field}`]: e.detail.value })
  },

  async saveProfile() {
    const { form } = this.data
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入姓名', icon: 'none' })
      return
    }

    const payload = {
      name: form.name.trim(),
      gender: form.gender,
      type: form.type,
    }
    if (form.birth_date) payload.birth_date = form.birth_date
    if (form.blood_type) payload.blood_type = form.blood_type

    try {
      await api.put('/api/members/me', payload)
      wx.showToast({ title: '保存成功', icon: 'success' })
      // Update store
      const membersRes = await api.get('/api/members')
      const members = membersRes.data.members || []
      setMembers(members)
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
    }
  },

  async saveSubscription() {
    const { subscription } = this.data
    try {
      await api.put('/api/members/me/subscription', {
        daily_digest: subscription.daily_digest,
        urgent_alert: subscription.urgent_alert,
        review_reminder: subscription.review_reminder,
      })
      wx.showToast({ title: '订阅设置已保存', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' })
    }
  },
})
