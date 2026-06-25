function getEnvVersion() {
  try {
    const accountInfo = wx.getAccountInfoSync()
    return accountInfo.miniProgram.envVersion || 'release'
  } catch (err) {
    return 'release'
  }
}

const ENV_CONFIG = {
  develop: {
    apiBase: 'http://localhost:8000',
    name: '开发环境',
  },
  trial: {
    apiBase: 'https://api-staging.care-assist.example.com',
    name: '体验版环境',
  },
  release: {
    apiBase: 'https://api.care-assist.example.com',
    name: '生产环境',
  },
}

function getApiBase() {
  const env = getEnvVersion()
  return ENV_CONFIG[env]?.apiBase || ENV_CONFIG.release.apiBase
}

function getCurrentEnv() {
  const env = getEnvVersion()
  return {
    version: env,
    ...ENV_CONFIG[env],
  }
}

module.exports = {
  getEnvVersion,
  getApiBase,
  getCurrentEnv,
}
