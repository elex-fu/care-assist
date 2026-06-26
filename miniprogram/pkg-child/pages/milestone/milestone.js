const api = require('../../../utils/api')

const CATEGORY_LABELS = {
  motor: '大运动',
  language: '语言',
  cognitive: '认知',
  social: '社交',
}

Page({
  data: {
    memberId: null,
    milestones: [],
    loading: false,
  },

  onLoad(options) {
    const memberId = options.member_id
    if (!memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.setData({ memberId })
    this.loadMilestones()
  },

  async loadMilestones() {
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/child/milestones?member_id=${this.data.memberId}`)
      const milestones = (res.data || []).map(m => ({
        ...m,
        categoryLabel: CATEGORY_LABELS[m.category] || m.category,
      }))
      this.setData({ milestones, loading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },
})
