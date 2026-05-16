const { store, clearAll } = require('./utils/store')

App({
  onLaunch() {
    console.log('Care Assist App Launch')

    // Restore store from storage
    const token = wx.getStorageSync('access_token')
    const currentMember = wx.getStorageSync('current_member')
    const family = wx.getStorageSync('family')
    const members = wx.getStorageSync('members')
    const currentMemberId = wx.getStorageSync('current_member_id')

    if (token) store.token = token
    if (currentMember) store.currentMember = currentMember
    if (family) store.family = family
    if (members && members.length) store.members = members
    if (currentMemberId) store.currentMemberId = currentMemberId

    const elderMode = wx.getStorageSync('elder_mode')
    if (elderMode) store.elderMode = true
  },

  onShow() {
    // Login guard: token required for non-login/index pages
    const pages = getCurrentPages()
    const cur = pages[pages.length - 1]
    const publicPages = ['/pages/index/index', '/pages/login/login']
    const route = cur ? `/${cur.route}` : ''

    if (!store.token && !publicPages.includes(route)) {
      wx.reLaunch({ url: '/pages/index/index' })
    }
  },

  globalData: {
    apiBase: 'http://localhost:8000',
  },
})
