const raw = {
  token: wx.getStorageSync('access_token') || null,
  currentMember: wx.getStorageSync('current_member') || null,
  family: null,
  members: [],
}

const store = new Proxy(raw, {
  set(target, key, value) {
    target[key] = value
    // Persist critical fields
    if (key === 'token') {
      wx.setStorageSync('access_token', value)
    }
    if (key === 'currentMember') {
      wx.setStorageSync('current_member', value)
    }
    return true
  },
})

module.exports = { store }
