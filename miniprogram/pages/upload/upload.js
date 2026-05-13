const { chooseImage, uploadImage } = require('../../utils/upload')
const { store, setMembers } = require('../../utils/store')
const { formatDateFull } = require('../../utils/format')
const api = require('../../utils/api')

Page({
  data: {
    step: 'select', // select | preview | uploading | processing | result
    members: [],
    currentMemberId: null,
    tempFilePath: '',
    hospital: '',
    reportDate: formatDateFull(new Date()),
    reportType: 'lab',
    reportResult: null,
    extractedIndicators: [],
    errorMsg: '',
    progressText: '',
  },

  onLoad() {
    const cachedMembers = store.members
    if (cachedMembers && cachedMembers.length) {
      this.setData({
        members: cachedMembers,
        currentMemberId: store.currentMemberId || cachedMembers[0].id,
      })
    }
    this.loadMembers()
  },

  async loadMembers() {
    try {
      const res = await api.get('/api/members')
      const members = res.data.members || []
      setMembers(members)
      const currentId = this.data.currentMemberId || (members[0] && members[0].id)
      this.setData({ members, currentMemberId: currentId })
    } catch (err) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    }
  },

  selectMember(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ currentMemberId: id })
  },

  async pickImage(e) {
    const sourceType = e.currentTarget.dataset.source
    try {
      const path = await chooseImage([sourceType])
      this.setData({
        step: 'preview',
        tempFilePath: path,
        errorMsg: '',
      })
    } catch (err) {
      wx.showToast({ title: '选择图片失败', icon: 'none' })
    }
  },

  onHospitalInput(e) {
    this.setData({ hospital: e.detail.value })
  },

  onDateChange(e) {
    this.setData({ reportDate: e.detail.value })
  },

  onTypeChange(e) {
    const types = ['lab', 'diagnosis', 'prescription', 'discharge']
    this.setData({ reportType: types[e.detail.value] })
  },

  async startUpload() {
    const { currentMemberId, tempFilePath, hospital, reportDate, reportType } = this.data
    if (!currentMemberId) {
      wx.showToast({ title: '请先选择成员', icon: 'none' })
      return
    }
    if (!tempFilePath) {
      wx.showToast({ title: '请先选择图片', icon: 'none' })
      return
    }

    this.setData({ step: 'uploading', progressText: '正在上传...' })

    try {
      const res = await uploadImage(tempFilePath, {
        member_id: currentMemberId,
        type: reportType,
        hospital: hospital || '',
        report_date: reportDate,
      })

      const reportId = res.id
      this.setData({ step: 'processing', progressText: '正在识别...' })

      // Trigger OCR
      const ocrRes = await api.post(`/api/reports/${reportId}/ocr`)
      const ocrData = ocrRes.data

      this.setData({
        step: 'result',
        reportResult: res,
        extractedIndicators: ocrData.extracted || [],
        progressText: '',
      })
    } catch (err) {
      this.setData({
        step: 'preview',
        errorMsg: err.message || '上传或识别失败，请重试',
      })
    }
  },

  retry() {
    this.setData({
      step: 'select',
      tempFilePath: '',
      hospital: '',
      reportDate: formatDateFull(new Date()),
      reportResult: null,
      extractedIndicators: [],
      errorMsg: '',
    })
  },

  goToIndicators() {
    wx.switchTab({ url: '/pages/indicators/indicators' })
  },
})
