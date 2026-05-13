const API_BASE = 'http://localhost:8000'

function chooseImage(sourceType = ['camera', 'album']) {
  return new Promise((resolve, reject) => {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType,
      success: (res) => resolve(res.tempFilePaths[0]),
      fail: reject,
    })
  })
}

function uploadImage(filePath, fields = {}) {
  const token = wx.getStorageSync('access_token')
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${API_BASE}/api/reports`,
      filePath,
      name: 'images',
      header: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      formData: fields,
      success: (res) => {
        try {
          const data = JSON.parse(res.data)
          if (data.code !== 0) {
            reject(new Error(data.message || '上传失败'))
            return
          }
          resolve(data.data)
        } catch (e) {
          reject(new Error('解析响应失败'))
        }
      },
      fail: (err) => reject(err),
    })
  })
}

module.exports = { chooseImage, uploadImage }
