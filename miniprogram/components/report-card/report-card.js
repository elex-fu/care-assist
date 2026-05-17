const { getReportTypeLabel, getOcrStatusLabel } = require('../../utils/format')

Component({
  properties: {
    report: Object,
    variant: {
      type: String,
      value: 'list',
    },
  },

  data: {
    typeLabel: '',
    statusLabel: '',
    statusClass: '',
  },

  observers: {
    'report': function(report) {
      if (!report) return
      this.setData({
        typeLabel: getReportTypeLabel(report.type),
        statusLabel: getOcrStatusLabel(report.ocr_status),
        statusClass: report.ocr_status || 'pending',
      })
    },
  },
})
