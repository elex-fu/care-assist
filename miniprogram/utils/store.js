const raw = {
  token: wx.getStorageSync('access_token') || null,
  currentMember: wx.getStorageSync('current_member') || null,
  family: wx.getStorageSync('family') || null,
  members: wx.getStorageSync('members') || [],
  currentMemberId: wx.getStorageSync('current_member_id') || null,
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
    if (key === 'family') {
      wx.setStorageSync('family', value)
    }
    if (key === 'members') {
      wx.setStorageSync('members', value)
    }
    if (key === 'currentMemberId') {
      wx.setStorageSync('current_member_id', value)
    }
    return true
  },
})

function setMembers(members) {
  store.members = members
}

function setCurrentMemberId(id) {
  store.currentMemberId = id
}

function getMemberById(id) {
  return store.members.find(m => m.id === id) || null
}

function getCurrentMember() {
  return store.currentMember
}

function isCreator() {
  const m = store.currentMember
  return m && m.role === 'creator'
}

function clearAll() {
  store.token = null
  store.currentMember = null
  store.family = null
  store.members = []
  store.currentMemberId = null
  wx.removeStorageSync('access_token')
  wx.removeStorageSync('refresh_token')
  wx.removeStorageSync('current_member')
  wx.removeStorageSync('family')
  wx.removeStorageSync('members')
  wx.removeStorageSync('current_member_id')
}

module.exports = { store, setMembers, setCurrentMemberId, getMemberById, getCurrentMember, isCreator, clearAll }
