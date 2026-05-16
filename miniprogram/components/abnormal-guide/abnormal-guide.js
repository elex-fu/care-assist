Component({
  properties: {
    visible: {
      type: Boolean,
      value: false,
    },
    indicator: {
      type: Object,
      value: null,
    },
  },

  data: {
    actions: [],
    title: '',
    subtitle: '',
  },

  observers: {
    'indicator': function(indicator) {
      if (!indicator) return
      const status = indicator.status
      const name = indicator.indicator_name
      const value = indicator.value
      const unit = indicator.unit || ''

      const statusMap = {
        high: { title: `${name} 偏高`, subtitle: `当前值 ${value}${unit}，高于正常范围`, color: '#F59E0B' },
        low: { title: `${name} 偏低`, subtitle: `当前值 ${value}${unit}，低于正常范围`, color: '#3B82F6' },
        critical: { title: `${name} 严重异常`, subtitle: `当前值 ${value}${unit}，请尽快就医`, color: '#EF4444' },
      }
      const info = statusMap[status] || statusMap.high

      const actions = this.buildActions(status, name)
      this.setData({
        title: info.title,
        subtitle: info.subtitle,
        actions,
      })
    },
  },

  methods: {
    buildActions(status, name) {
      const base = [
        { icon: '📅', text: '预约复查', desc: '建议一周内复查', action: 'book_checkup' },
        { icon: '🥗', text: '饮食建议', desc: '查看相关饮食注意事项', action: 'diet' },
      ]
      if (status === 'critical') {
        return [
          { icon: '🏥', text: '立即就医', desc: '该指标严重异常，建议尽快就诊', action: 'hospital', highlight: true },
          { icon: '📞', text: '咨询医生', desc: '通过 AI 咨询健康问题', action: 'ai_chat' },
          ...base,
        ]
      }
      if (name.includes('血压') || name.includes('血糖')) {
        return [
          ...base,
          { icon: '🏃', text: '运动建议', desc: '适量运动有助于控制指标', action: 'exercise' },
          { icon: '💊', text: '用药记录', desc: '检查是否按时服药', action: 'medication' },
        ]
      }
      return base
    },

    onClose() {
      this.triggerEvent('close')
    },

    onAction(e) {
      const action = e.currentTarget.dataset.action
      this.triggerEvent('action', { action, indicator: this.data.indicator })
    },

    onOverlayTap() {
      this.onClose()
    },
  },
})
