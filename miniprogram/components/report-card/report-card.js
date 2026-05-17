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
      const typeMap = {
        lab: '检验报告',
        diagnosis: '诊断报告',
        prescription: '处方',
        discharge: '出院小结',
      }
      const statusMap = {
        completed: { label: '已识别', class: 'completed' },
        pending: { label: '待处理', class: 'pending' },
        processing: { label: '识别中', class: 'processing' },
        failed: { label: '失败', class: 'failed' },
      }
      this.setData({
        typeLabel: typeMap[report.type] || '报告',
        statusLabel: statusMap[report.ocr_status]?.label || '待处理',
        statusClass: statusMap[report.ocr_status]?.class || 'pending',
      })
    },
  },
})
