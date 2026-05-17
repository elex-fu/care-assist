const { getMemberTypeLabel } = require('../../utils/format')

Component({
  properties: {
    member: Object,
    hospitalActive: Boolean,
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
  },

  observers: {
    'member, hospitalActive, variant': function(member, hospitalActive, variant) {
      if (!member) return
      const typeLabel = getMemberTypeLabel(member.type)
      this.setData({ typeLabel })
      if (variant === 'list') {
        return
      }
      if (hospitalActive) {
        this.setData({
          statusClass: 'status-hospital',
          statusText: '住院中',
          statusIcon: 'H',
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
      })
    },
  },
})
