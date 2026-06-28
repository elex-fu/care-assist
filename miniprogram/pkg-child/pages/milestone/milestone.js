const api = require('../../../utils/api')

const CATEGORY_LABELS = {
  motor: '大运动',
  language: '语言',
  cognitive: '认知',
  social: '社交',
}

const STATUS_LABELS = {
  achieved: '已达成',
  warning: '临近',
  delayed: '延迟',
  normal: '待发展',
}

const STATUS_COLORS = {
  achieved: '#10b981',
  warning: '#f59e0b',
  delayed: '#ef4444',
  normal: '#6b7280',
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
        statusLabel: STATUS_LABELS[m.status] || m.status,
        statusColor: STATUS_COLORS[m.status] || STATUS_COLORS.normal,
      }))
      this.setData({ milestones, loading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },
  onAIFabTap(e) {
    const { onAIFabTap } = require('../../../utils/page-base')
    onAIFabTap(e)
  },
})
