Component({
  properties: {
    title: String,
    subtitle: String,
    icon: {
      type: String,
      value: '',
    },
    actionText: {
      type: String,
      value: '',
    },
  },

  methods: {
    onAction() {
      this.triggerEvent('action')
    },
  },
})
