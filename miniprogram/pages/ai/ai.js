const api = require('../../utils/api')
const { store, setMembers, setCurrentMemberId } = require('../../utils/store')
const { getClient } = require('../../utils/websocket')

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
    elderMode: false,
  },

  ws: null,

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

  onUnload() {
    if (this.ws) {
      this.ws.disconnect()
      this.ws = null
    }
  },

  onShow() {
    this.setData({ elderMode: store.elderMode || false })
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
      this.connectWebSocket()
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  connectWebSocket() {
    const token = wx.getStorageSync('access_token')
    if (!token) return

    this.ws = getClient()
    this.ws.disconnect() // Ensure clean state

    this.ws.on('chat_chunk', (data) => {
      const messages = this.data.messages
      const lastIdx = messages.length - 1
      if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
        messages[lastIdx].content += data.content || ''
        this.setData({ messages: [...messages] })
      }
    })

    this.ws.on('chat_done', () => {
      const messages = this.data.messages
      const lastIdx = messages.length - 1
      if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
        messages[lastIdx]._blocks = this.parseStructuredContent(messages[lastIdx].content)
      }
      this.setData({ messages: [...messages], loading: false })
    })

    this.ws.on('chat_error', (data) => {
      wx.showToast({ title: data.message || 'AI 回复失败', icon: 'none' })
      const messages = this.data.messages
      const lastIdx = messages.length - 1
      if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
        messages[lastIdx].content = '[回复失败，请重试]'
      }
      this.setData({ messages: [...messages], loading: false })
    })

    this.ws.connect(token)
  },

  async loadOrCreateConversation(memberId) {
    this.setData({ loading: true })
    try {
      const listRes = await api.get(`/api/ai-conversations?member_id=${memberId}`)
      const conversations = listRes.data || []

      if (conversations.length > 0) {
        const conv = conversations[0]
        const messages = (conv.messages || []).map(m => ({
          ...m,
          _blocks: m.role === 'assistant' ? this.parseStructuredContent(m.content) : null,
        }))
        this.setData({
          conversationId: conv.id,
          messages,
          conversations,
          loading: false,
        })
      } else {
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

  sendMessage(content) {
    const text = typeof content === 'string' ? content : this.data.inputValue
    const { conversationId, messages } = this.data

    if (!text.trim()) return
    if (!conversationId) {
      wx.showToast({ title: '对话未初始化', icon: 'none' })
      return
    }

    // Add user message and placeholder assistant message
    const newMessages = [
      ...messages,
      { role: 'user', content: text },
      { role: 'assistant', content: '' },
    ]
    this.setData({
      messages: newMessages,
      inputValue: '',
      loading: true,
    })

    if (this.ws && this.ws.connected) {
      this.ws.send({
        type: 'chat',
        conversation_id: conversationId,
        user_message: text,
      })
    } else {
      // Fallback to REST if WS not connected
      this._sendRestMessage(text)
    }
  },

  async _sendRestMessage(text) {
    const { conversationId, messages } = this.data
    try {
      const res = await api.post(`/api/ai-conversations/${conversationId}/messages`, {
        user_message: text,
      })
      const messages = (res.data.messages || []).map(m => ({
        ...m,
        _blocks: m.role === 'assistant' ? this.parseStructuredContent(m.content) : null,
      }))
      this.setData({
        messages,
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

  onAiAction(e) {
    const action = e.currentTarget.dataset.action
    if (action === 'view_summary') {
      wx.showToast({ title: '查看摘要功能开发中', icon: 'none' })
    } else if (action === 'add_reminder') {
      wx.navigateTo({ url: '/pkg-system/pages/reminder-add/reminder-add' })
    } else if (action === 'view_trend') {
      wx.switchTab({ url: '/pages/indicators/indicators' })
    }
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
        this.setData({
          conversationId: id,
          messages: [],
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

  // Parse assistant message into structured blocks for rich rendering
  parseStructuredContent(content) {
    if (!content || content.length < 20) return null

    const blocks = []
    const lines = content.split('\n')

    // Detect indicator rows: 名称 + 数值 + 单位 + optional arrow/status
    const indicatorRegex = /^([一-龥a-zA-Z]+)\s+([\d.]+)\s*(g\/L|mmol\/L|U\/L|μmol\/L|umol\/L|10\^\d+\/L|10\*\*\d+\/L|mmHg|bpm|kg|cm|mg\/dL|%|°C|个\/μL|×10\^\d+\/L|×10\*\*\d+\/L|\/L|μL|ml|mL|L)?\s*([↑↓→]|正常|偏高|偏低|异常|高|低)?/
    const questionRegex = /^(\d+)\.\s*(.+)/

    let currentText = ''
    let indicatorRows = []
    let questionList = []
    let actions = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

      const indMatch = line.match(indicatorRegex)
      const qMatch = line.match(questionRegex)

      if (indMatch && indMatch[2]) {
        // Flush pending text before table
        if (currentText) {
          blocks.push({ type: 'text', content: currentText.trim() })
          currentText = ''
        }
        indicatorRows.push({
          name: indMatch[1],
          value: indMatch[2],
          unit: indMatch[3] || '',
          status: indMatch[4] || '',
        })
      } else if (qMatch) {
        if (currentText) {
          blocks.push({ type: 'text', content: currentText.trim() })
          currentText = ''
        }
        questionList.push({ num: qMatch[1], text: qMatch[2] })
      } else {
        if (indicatorRows.length > 0) {
          blocks.push({ type: 'indicator_table', rows: indicatorRows })
          indicatorRows = []
        }
        if (questionList.length > 0) {
          blocks.push({ type: 'question_list', items: questionList })
          questionList = []
        }
        currentText += line + '\n'
      }
    }

    // Flush remaining
    if (currentText) {
      blocks.push({ type: 'text', content: currentText.trim() })
    }
    if (indicatorRows.length > 0) {
      blocks.push({ type: 'indicator_table', rows: indicatorRows })
    }
    if (questionList.length > 0) {
      blocks.push({ type: 'question_list', items: questionList })
    }

    // Detect action suggestions from keywords
    if (content.includes('就诊摘要') || content.includes('摘要') || content.includes('报告')) {
      actions.push({ label: '查看就诊摘要', action: 'view_summary' })
    }
    if (content.includes('提醒') || content.includes('添加')) {
      actions.push({ label: '添加到提醒', action: 'add_reminder' })
    }
    if (content.includes('指标') || content.includes('趋势')) {
      actions.push({ label: '查看指标趋势', action: 'view_trend' })
    }

    if (actions.length > 0) {
      blocks.push({ type: 'actions', items: actions })
    }

    // Only return structured data if we found more than plain text
    const hasStructure = blocks.some(b => b.type !== 'text')
    return hasStructure ? blocks : null
  },
})
