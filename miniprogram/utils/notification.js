const api = require('./api')

async function getReminderTemplateIds() {
  try {
    const res = await api.get('/api/reminders/template-ids')
    return res.data || {}
  } catch (err) {
    console.warn('[notification] get template ids failed:', err)
    return {}
  }
}

function collectTemplateIds(config) {
  return Object.values(config || {}).filter(Boolean)
}

function filterAcceptedIds(tmplIds, result) {
  return tmplIds.filter(id => result && result[id] === 'accept')
}

async function recordSubscription(acceptedIds) {
  if (!acceptedIds.length) return
  try {
    await api.post('/api/reminders/subscribe', { template_ids: acceptedIds })
  } catch (err) {
    console.warn('[notification] record subscription failed:', err)
  }
}

function requestReminderSubscription() {
  return new Promise(async (resolve) => {
    const config = await getReminderTemplateIds()
    const tmplIds = collectTemplateIds(config)
    if (!tmplIds.length) {
      resolve({ accepted: [], message: 'no template ids configured' })
      return
    }

    wx.requestSubscribeMessage({
      tmplIds,
      success: async (res) => {
        const accepted = filterAcceptedIds(tmplIds, res)
        await recordSubscription(accepted)
        resolve({ accepted, result: res })
      },
      fail: (err) => {
        console.warn('[notification] requestSubscribeMessage failed:', err)
        resolve({ accepted: [], error: err })
      },
    })
  })
}

module.exports = {
  getReminderTemplateIds,
  requestReminderSubscription,
}
