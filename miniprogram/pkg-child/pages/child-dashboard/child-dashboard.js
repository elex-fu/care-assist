const api = require('../../../utils/api')
const { formatDateFull } = require('../../../utils/format')

const AGE_LAYOUTS = {
  infant: { label: '0-3 个月', focus: '黄疸观察、母乳喂养、体重增长', todos: ['乙肝疫苗第2针（1月龄）', '卡介苗接种'] },
  baby: { label: '3-6 个月', focus: '翻身、辅食准备、睡眠规律', todos: ['五联疫苗第1针', '口服轮状疫苗'] },
  toddler: { label: '6-12 个月', focus: '爬行、辅食添加、语言启蒙', todos: ['麻疹疫苗', '乙脑疫苗', '手足口疫苗'] },
  preschool: { label: '1-3 岁', focus: '行走、语言发展、社交启蒙', todos: ['甲肝疫苗', '百白破加强针', '水痘疫苗'] },
  kinder: { label: '3-6 岁', focus: '入园准备、视力保护、饮食习惯', todos: ['流脑疫苗加强', '腮腺炎疫苗', '入园体检'] },
}

function getAgeSegment(months) {
  if (months < 3) return 'infant'
  if (months < 6) return 'baby'
  if (months < 12) return 'toddler'
  if (months < 36) return 'preschool'
  return 'kinder'
}

function calcMonths(birthDate) {
  if (!birthDate) return 0
  const birth = new Date(birthDate)
  const now = new Date()
  return (now.getFullYear() - birth.getFullYear()) * 12 + (now.getMonth() - birth.getMonth())
}

Page({
  data: {
    member: null,
    months: 0,
    segment: null,
    segmentInfo: null,
    vaccines: [],
    indicators: [],
    loading: true,
  },

  onLoad(options) {
    const memberId = options.member_id
    if (!memberId) {
      wx.showToast({ title: '缺少成员信息', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.loadData(memberId)
  },

  async loadData(memberId) {
    this.setData({ loading: true })
    try {
      const [memberRes, vaccineRes, indRes] = await Promise.all([
        api.get('/api/members').then(r => {
          const members = r.data.members || []
          return members.find(m => m.id === memberId)
        }),
        api.get(`/api/vaccines?member_id=${memberId}`),
        api.get(`/api/indicators?member_id=${memberId}`),
      ])

      const member = memberRes || null
      const months = calcMonths(member && member.birth_date)
      const segment = getAgeSegment(months)

      this.setData({
        member,
        months,
        segment,
        segmentInfo: AGE_LAYOUTS[segment],
        vaccines: vaccineRes.data || [],
        indicators: indRes.data || [],
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  goToVaccines() {
    const id = this.data.member && this.data.member.id
    if (!id) return
    wx.navigateTo({ url: `/pkg-child/pages/vaccine/vaccine?member_id=${id}` })
  },

  goToIndicators() {
    const id = this.data.member && this.data.member.id
    if (!id) return
    wx.switchTab({ url: '/pages/indicators/indicators' })
    // Note: indicators page will show current member
  },

  goToUpload() {
    wx.switchTab({ url: '/pages/upload/upload' })
  },

  goToMemberDetail() {
    const id = this.data.member && this.data.member.id
    if (!id) return
    wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },
})
