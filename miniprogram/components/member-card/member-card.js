const { getMemberTypeLabel } = require('../../utils/format')

Component({
  properties: {
    member: Object,
    hospitalActive: Boolean,
    hospitalDays: Number,
    variant: {
      type: String,
      value: 'grid',
    },
  },

  data: {
    statusClass: '',
    statusText: '',
    statusIcon: '',
    typeLabel: '',
    ageText: '',
    showTopBar: false,
  },

  observers: {
    'member, hospitalActive, hospitalDays, variant': function(member, hospitalActive, hospitalDays, variant) {
      if (!member) return
      const typeLabel = getMemberTypeLabel(member.type)
      const ageText = this.computeAge(member.birth_date)
      this.setData({ typeLabel, ageText })
      if (variant === 'list') {
        return
      }
      if (hospitalActive) {
        this.setData({
          statusClass: 'status-hospital',
          statusText: '住院中',
          statusIcon: 'H',
          showTopBar: true,
        })
        return
      }
      const status = member.latest_status || 'normal'
      const map = {
        normal: { class: 'status-normal', text: '正常', icon: '✓' },
        low: { class: 'status-warning', text: '偏低', icon: '!' },
        high: { class: 'status-warning', text: '偏高', icon: '!' },
        critical: { class: 'status-critical', text: '异常', icon: '!' },
      }
      const s = map[status] || map.normal
      this.setData({
        statusClass: s.class,
        statusText: s.text,
        statusIcon: s.icon,
        showTopBar: status === 'critical' || status === 'high' || status === 'low',
      })
    },
  },

  computeAge(birthDate) {
    if (!birthDate) return ''
    const birth = new Date(birthDate)
    const now = new Date()
    let years = now.getFullYear() - birth.getFullYear()
    const m = now.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) {
      years--
    }
    if (years < 0) return ''
    if (years < 1) {
      const months = Math.max(0, (now.getFullYear() - birth.getFullYear()) * 12 + now.getMonth() - birth.getMonth())
      return months + '个月'
    }
    return years + '岁'
  },
})
