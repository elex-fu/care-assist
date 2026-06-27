const { getMedicationCalendar } = require('../../utils/api')

Component({
  properties: {
    memberId: String,
    yearMonth: String,
  },
  data: {
    weekdays: ['日', '一', '二', '三', '四', '五', '六'],
    days: [],
    currentYearMonth: '',
  },
  observers: {
    'memberId,yearMonth': function (memberId, yearMonth) {
      if (yearMonth && yearMonth !== this.data.currentYearMonth) {
        this.setData({ currentYearMonth: yearMonth })
      }
      const current = this.data.currentYearMonth
      if (memberId && current && (memberId !== this._lastMemberId || current !== this._lastYearMonth)) {
        this._lastMemberId = memberId
        this._lastYearMonth = current
        this.load(memberId, current)
      }
    }
  },
  methods: {
    async load(memberId, yearMonth) {
      this._lastMemberId = memberId
      this._lastYearMonth = yearMonth
      try {
        const res = await getMedicationCalendar(memberId, yearMonth)
        const serverDays = res.data && res.data.days ? res.data.days : []
        const days = serverDays.map(d => ({
          ...d,
          day: parseInt(d.date.split('-')[2], 10),
        }))
        this.setData({ days })
      } catch (err) {
        console.error('load medication calendar failed', err)
      }
    },
    changeMonth(delta) {
      const current = this.data.currentYearMonth || this.properties.yearMonth
      if (!current) return
      const [year, month] = current.split('-').map(Number)
      const date = new Date(year, month - 1 + delta, 1)
      const newYearMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      this.setData({ currentYearMonth: newYearMonth })
      if (this.properties.memberId) this.load(this.properties.memberId, newYearMonth)
      this.triggerEvent('monthchange', { yearMonth: newYearMonth })
    },
    onPrevMonth() {
      this.changeMonth(-1)
    },
    onNextMonth() {
      this.changeMonth(1)
    },
    onDayTap(e) {
      const date = e.currentTarget.dataset.date
      this.triggerEvent('daytap', { date })
    }
  }
})
