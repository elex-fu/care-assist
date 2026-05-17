const { getStatusColor, getStatusLabel } = require('../../utils/format')

Component({
  properties: {
    indicator: Object,
    showTrend: Boolean,
    compact: Boolean,
  },

  data: {
    statusColor: '',
    statusLabel: '',
  },

  observers: {
    'indicator': function(indicator) {
      if (!indicator) return
      this.setData({
        statusColor: getStatusColor(indicator.status),
        statusLabel: getStatusLabel(indicator.status),
      })
    },
  },
})
