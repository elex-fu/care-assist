Component({
  properties: {
    event: {
      type: Object,
      value: null,
    },
  },

  data: {
    typeMeta: {},
  },

  observers: {
    'event': function(event) {
      if (!event) return
      const meta = this.resolveTypeMeta(event.type)
      this.setData({ typeMeta: meta })
    },
  },

  methods: {
    resolveTypeMeta(type) {
      const map = {
        visit: { label: '就诊', icon: '🏥', color: '#EF4444', bg: '#FEF2F2' },
        lab: { label: '检验', icon: '🧪', color: '#3B82F6', bg: '#EFF6FF' },
        medication: { label: '用药', icon: '💊', color: '#F59E0B', bg: '#FFFBEB' },
        symptom: { label: '症状', icon: '🤒', color: '#EC4899', bg: '#FDF2F8' },
        hospital: { label: '住院', icon: '🛏️', color: '#8B5CF6', bg: '#F5F3FF' },
        vaccine: { label: '疫苗', icon: '💉', color: '#10B981', bg: '#ECFDF5' },
        checkup: { label: '体检', icon: '🩺', color: '#06B6D4', bg: '#ECFEFF' },
        milestone: { label: '里程碑', icon: '🏆', color: '#F97316', bg: '#FFF7ED' },
      }
      return map[type] || { label: '事件', icon: '📌', color: '#64748B', bg: '#F8FAFC' }
    },

    onTap() {
      this.triggerEvent('tap', { event: this.data.event })
    },
  },
})
