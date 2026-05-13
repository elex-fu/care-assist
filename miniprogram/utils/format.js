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
}
