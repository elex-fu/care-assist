function onAIFabTap(e) {
  const ctx = e.detail.pageContext || ''
  wx.setStorageSync('ai_page_context', ctx)
  wx.switchTab({
    url: '/pages/ai/ai'
  })
}

module.exports = { onAIFabTap }
