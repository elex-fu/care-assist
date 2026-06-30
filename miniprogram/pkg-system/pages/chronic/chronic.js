const api = require('../../../utils/api')
const { store } = require('../../../utils/store')

const PACKAGE_INFO = {
  hypertension: { name: '高血压', icon: '🩸', desc: '监测血压相关指标' },
  diabetes: { name: '糖尿病', icon: '🍬', desc: '监测血糖相关指标' },
  dyslipidemia: { name: '高血脂', icon: '🥑', desc: '监测血脂相关指标' },
}

Page({
  data: {
    memberId: null,
    memberName: '',
    package: '',
    packageName: '',
    packages: [],
    indicators: [],
    summary: '',
    loading: false,
    showTrend: false,
  },

  onLoad(options) {
    const memberId = options.member_id || store.currentMemberId
    const member = (store.members || []).find(m => m.id === memberId)
    const packageKey = options.package || ''
    this.setData({
      memberId,
      memberName: member ? member.name : '',
      package: packageKey,
      packageName: packageKey ? ((PACKAGE_INFO[packageKey] && PACKAGE_INFO[packageKey].name) || '') : '',
    })

    if (packageKey) {
      this.loadPackageDetail(packageKey)
    } else {
      this.loadPackageList()
    }
  },

  async loadPackageList() {
    this.setData({ loading: true })
    try {
      const res = await api.get('/api/indicators/chronic')
      const packages = (res.data || []).map(p => ({
        ...p,
        icon: (PACKAGE_INFO[p.package] && PACKAGE_INFO[p.package].icon) || '📋',
      }))
      this.setData({ packages, loading: false })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadPackageDetail(packageKey) {
    if (!this.data.memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const res = await api.get(`/api/indicators/chronic/${packageKey}?member_id=${this.data.memberId}`)
      const data = res.data || {}
      this.setData({
        packageName: data.name || (PACKAGE_INFO[packageKey] && PACKAGE_INFO[packageKey].name) || packageKey,
        indicators: data.indicators || [],
        summary: data.summary || '',
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  showTrend() {
    this.setData({ showTrend: true })
  },

  closeTrend() {
    this.setData({ showTrend: false })
  },

  goToDetail(e) {
    const packageKey = e.currentTarget.dataset.package
    wx.navigateTo({
      url: `/pkg-system/pages/chronic/chronic?package=${packageKey}&member_id=${this.data.memberId}`,
    })
  },

  goBack() {
    wx.navigateBack()
  },
  onAIFabTap(e) {
    const { onAIFabTap } = require('../../../utils/page-base')
    onAIFabTap(e)
  },
})
