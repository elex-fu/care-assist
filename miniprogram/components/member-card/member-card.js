Component({
  properties: {
    member: Object,
  },

  data: {
    statusClass: '',
    statusText: '',
    statusIcon: '',
  },

  observers: {
    'member': function(member) {
      if (!member) return
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
