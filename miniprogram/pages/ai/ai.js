const api = require('../../utils/api')
const { store, setMembers, setCurrentMemberId } = require('../../utils/store')

const QUICK_QUESTIONS = [
  '血压正常吗？',
  '帮我分析最新报告',
  '最近指标有什么变化？',
  '需要注意什么？',
]

Page({
  data: {
    members: [],
    currentMemberId: null,
    conversationId: null,
    messages: [],
    inputValue: '',
    loading: false,
    showHistory: false,
    conversations: [],
    quickQuestions: QUICK_QUESTIONS,
  },

  onLoad() {
    const cachedMembers = store.members
    const currentId = store.currentMemberId
    if (cachedMembers && cachedMembers.length) {
      this.setData({
        members: cachedMembers,
        currentMemberId: currentId || cachedMembers[0].id,
      })
    }
    this.init()
  },

  async init() {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      const currentId = this.data.currentMemberId || (members[0] && members[0].id)
      this.setData({ members, currentMemberId: currentId })
      if (currentId) {
        await this.loadOrCreateConversation(currentId)
      }
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  async loadOrCreateConversation(memberId) {
    this.setData({ loading: true })
    try {
      // Try to find an existing conversation
      const listRes = await api.get(`/api/ai-conversations?member_id=${memberId}`)
      const conversations = listRes.data || []

      if (conversations.length > 0) {
        const conv = conversations[0]
        this.setData({
          conversationId: conv.id,
          messages: conv.messages || [],
          conversations,
          loading: false,
        })
      } else {
        // Create new conversation
        const createRes = await api.post('/api/ai-conversations', {
          member_id: memberId,
          page_context: 'ai_tab',
        })
        this.setData({
          conversationId: createRes.data.id,
          messages: [],
          conversations: [],
          loading: false,
        })
      }
    } catch (err) {
      this.setData({ loading: false })
      wx.showToast({ title: err.message || '初始化对话失败', icon: 'none' })
    }
  },

  async selectMember(e) {
    const id = e.currentTarget.dataset.id
    setCurrentMemberId(id)
    this.setData({ currentMemberId: id })
    await this.loadOrCreateConversation(id)
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  async sendMessage(content) {
    const text = typeof content === 'string' ? content : this.data.inputValue
    const { conversationId, messages } = this.data

    if (!text.trim()) return
    if (!conversationId) {
      wx.showToast({ title: '对话未初始化', icon: 'none' })
      return
    }

    const newMessages = [...messages, { role: 'user', content: text }]
    this.setData({
      messages: newMessages,
      inputValue: '',
      loading: true,
    })

    try {
      const res = await api.post(`/api/ai-conversations/${conversationId}/messages`, {
        user_message: text,
      })
      this.setData({
        messages: res.data.messages || [],
        loading: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  onSendTap() {
    this.sendMessage()
  },

  onQuickQuestion(e) {
    const q = e.currentTarget.dataset.q
    this.sendMessage(q)
  },

  toggleHistory() {
    this.setData({ showHistory: !this.data.showHistory })
  },

  closeHistory() {
    this.setData({ showHistory: false })
  },

  async loadConversation(e) {
    const id = e.currentTarget.dataset.id
    try {
      const listRes = await api.get(`/api/ai-conversations?member_id=${this.data.currentMemberId}`)
      const conversations = listRes.data || []
      const conv = conversations.find(c => c.id === id)
      if (conv) {
        // Need to fetch full conversation to get messages
        // For now, assume messages aren't in list; we need to fetch from send endpoint or add GET /{id}
        // As a workaround, create a new conversation flow
        this.setData({
          conversationId: id,
          messages: [], // messages not available in list endpoint
          showHistory: false,
        })
      }
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  async startNewConversation() {
    const { currentMemberId } = this.data
    if (!currentMemberId) return
    try {
      const createRes = await api.post('/api/ai-conversations', {
        member_id: currentMemberId,
        page_context: 'ai_tab',
      })
      this.setData({
        conversationId: createRes.data.id,
        messages: [],
        showHistory: false,
      })
    } catch (err) {
      wx.showToast({ title: err.message || '创建失败', icon: 'none' })
    }
  },

  preventClose() {
    // catch tap on sheet to prevent overlay close
  },
})
