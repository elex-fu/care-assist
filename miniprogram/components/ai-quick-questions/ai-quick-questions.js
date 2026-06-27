const { getQuickQuestions } = require('../../utils/api')

Component({
  properties: {
    memberId: String,
    pageContext: { type: String, value: '' },
  },
  data: {
    questions: [],
  },
  observers: {
    'memberId,pageContext': function (memberId, pageContext) {
      if (memberId) this.loadQuestions(memberId, pageContext)
    }
  },
  methods: {
    async loadQuestions(memberId, pageContext) {
      try {
        const res = await getQuickQuestions(memberId, pageContext)
        this.setData({ questions: res.data || [] })
      } catch (err) {
        console.error('load quick questions failed', err)
      }
    },
    onTap(e) {
      const q = e.currentTarget.dataset.q
      this.triggerEvent('select', { question: q })
    }
  }
})
