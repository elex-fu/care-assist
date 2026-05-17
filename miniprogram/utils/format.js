function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return `${month}月${day}日`
}

function formatDateFull(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatValue(value, unit) {
  if (value === null || value === undefined) return '-'
  return `${value} ${unit || ''}`
}

const STATUS_CONFIG = {
  normal: { color: '#10B981', label: '正常', icon: '✓' },
  low: { color: '#F59E0B', label: '偏低', icon: '!' },
  high: { color: '#F59E0B', label: '偏高', icon: '!' },
  critical: { color: '#EF4444', label: '建议复查', icon: '✕' },
}

function getStatusColor(status) {
  return (STATUS_CONFIG[status] || STATUS_CONFIG.normal).color
}

function getStatusLabel(status) {
  return (STATUS_CONFIG[status] || STATUS_CONFIG.normal).label
}

function getStatusIcon(status) {
  return (STATUS_CONFIG[status] || STATUS_CONFIG.normal).icon
}

function getTrendArrow(direction) {
  const arrows = { up: '↑', down: '↓', stable: '→' }
  return arrows[direction] || ''
}

function getTrendLabel(evaluation) {
  const labels = {
    improving: '改善',
    worsening: '恶化',
    stable: '平稳',
  }
  return labels[evaluation] || ''
}

function formatNumber(n, decimals = 1) {
  if (n === null || n === undefined) return '-'
  return Number(n).toFixed(decimals)
}

function getEventTypeLabel(type) {
  const map = {
    visit: '就诊',
    lab: '检验',
    medication: '用药',
    symptom: '症状',
    hospital: '住院',
    vaccine: '疫苗',
    checkup: '体检',
    milestone: '里程碑',
    ai: 'AI解读',
  }
  return map[type] || '事件'
}

function getReportTypeLabel(type) {
  const map = {
    lab: '检验报告',
    diagnosis: '诊断报告',
    prescription: '处方',
    discharge: '出院小结',
  }
  return map[type] || '报告'
}

function getOcrStatusLabel(status) {
  const map = {
    completed: '已识别',
    pending: '待处理',
    processing: '识别中',
    failed: '失败',
  }
  return map[status] || '待处理'
}

function getReminderTypeLabel(type) {
  const map = {
    vaccine: '疫苗',
    checkup: '体检',
    review: '复查',
    medication: '用药',
  }
  return map[type] || '提醒'
}

function getReminderPriorityLabel(priority) {
  const map = {
    critical: '紧急',
    high: '高',
    normal: '普通',
    low: '低',
  }
  return map[priority] || '普通'
}

function getVaccineStatusLabel(status) {
  const map = {
    completed: '已完成',
    pending: '待接种',
    upcoming: '即将接种',
    overdue: '已逾期',
  }
  return map[status] || '待接种'
}

module.exports = {
  formatDate,
  formatDateFull,
  formatValue,
  getStatusColor,
  getStatusLabel,
  getStatusIcon,
  getTrendArrow,
  getTrendLabel,
  formatNumber,
  getEventTypeLabel,
  getReportTypeLabel,
  getOcrStatusLabel,
  getReminderTypeLabel,
  getReminderPriorityLabel,
  getVaccineStatusLabel,
}
