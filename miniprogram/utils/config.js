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
    wsBase: 'ws://localhost:8000',
    name: '开发环境',
  },
  trial: {
    apiBase: 'https://api-staging.care-assist.example.com',
    wsBase: 'wss://api-staging.care-assist.example.com',
    name: '体验版环境',
  },
  release: {
    apiBase: 'https://api.care-assist.example.com',
    wsBase: 'wss://api.care-assist.example.com',
    name: '生产环境',
  },
}

function getEnvConfig() {
  const env = getEnvVersion()
  return ENV_CONFIG[env] || ENV_CONFIG.release
}

function getApiBase() {
  return getEnvConfig().apiBase
}

function getWsBase() {
  return getEnvConfig().wsBase
}

function getCurrentEnv() {
  return {
    version: getEnvVersion(),
    ...getEnvConfig(),
  }
}

module.exports = {
  getEnvVersion,
  getApiBase,
  getWsBase,
  getCurrentEnv,
}
