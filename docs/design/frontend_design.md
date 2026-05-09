# 家庭智能健康助手 — 前端项目设计

> 版本：v1.0 | 日期：2026-05-08 | 读者：前端开发工程师 | 状态：设计定稿

---

## 目录

1. [项目结构](#一项目结构)
2. [分包策略](#二分包策略)
3. [家庭成员共享前端实现](#三家庭成员共享前端实现)
4. [微信订阅消息管理](#四微信订阅消息管理)
5. [全局状态管理](#五全局状态管理)
6. [HTTP 请求封装](#六http-请求封装)
7. [WebSocket 客户端管理](#七websocket-客户端管理)
8. [趋势图组件](#八趋势图组件)
9. [底部浮层组件](#九底部浮层组件)
10. [离线处理与弱网适配](#十离线处理与弱网适配)

---

## 一、项目结构

```
mini-program/
├── app.js                    # 全局App实例，初始化登录态、WebSocket
├── app.json                  # 页面路由、TabBar配置、分包声明
├── app.wxss                  # 全局样式变量、工具类
├── components/               # 全局公共组件
│   ├── member-card/          # 成员卡片（首页/网格）
│   ├── indicator-card/       # 指标卡片（列表/盯盘）
│   ├── trend-chart/          # 趋势图（ECharts Canvas封装）
│   ├── bottom-sheet/         # 底部浮层容器（趋势图/AI/异常）
│   ├── ai-chat-panel/        # AI对话面板（半屏/全屏）
│   ├── status-badge/         # 状态Badge（正常/偏高/危急）
│   ├── timeline-node/        # 时间轴节点
│   └── skeleton/             # 骨架屏
├── pages/                    # 主包页面（TabBar，必须在主包）
│   ├── index/                # P1 首页
│   ├── indicator/            # P2 指标（关注指标快捷入口+趋势）
│   ├── ai/                   # P3 AI对话（底部Tab AI页面）
│   ├── upload/               # P4 上传（3步极简流程）
│   └── profile/              # P5 我的（设置+成员管理）
├── subpackages/              # 分包加载（按场景分包）
│   ├── member/               # 成员详情包
│   │   ├── pages/detail/     # 成员详情（时间轴/指标/病例/AI）
│   │   ├── pages/indicator/  # 指标中心（完整指标列表+趋势图）
│   │   └── pages/report/     # 报告详情
│   ├── hospital/             # 住院场景包
│   │   ├── pages/overview/   # 住院总览
│   │   ├── pages/watch/      # 指标盯盘
│   │   └── pages/compare/    # 指标对比
│   └── child/                # 儿童场景包
│       ├── pages/dashboard/  # 儿童看板
│       ├── pages/vaccine/    # 疫苗管理
│       └── pages/growth/     # 成长曲线
├── utils/
│   ├── api.js                # HTTP请求封装（含JWT自动续期）
│   ├── ws.js                 # WebSocket管理器（重连/心跳/消息路由）
│   ├── store.js              # 轻量级响应式全局状态
│   ├── auth.js               # 微信登录/JWT管理
│   ├── subscription.js       # 微信订阅消息管理
│   ├── offline.js            # 离线缓存与弱网适配
│   └── format.js             # 数值格式化、日期处理
└── static/
    ├── icons/                # TabBar/导航图标
    └── images/               # 占位图、空态插画
```

---

## 二、分包策略

微信小程序主包体积限制 **2MB**，采用以下分包策略：

| 分包名称 | 包含页面 | 预估体积 | 触发加载 |
|---------|---------|---------|---------|
| `member` | 成员详情、指标中心、报告详情、趋势图 | ~800KB | 点击成员卡片时预加载 |
| `hospital` | 住院总览、盯盘、对比、批次 | ~600KB | 点击住院节点时加载 |
| `child` | 儿童看板、疫苗、成长曲线、里程碑 | ~700KB | 点击儿童卡片时预加载 |

```json
// app.json 主包+分包配置
{
  "pages": [
    "pages/index/index",
    "pages/indicator/index",
    "pages/ai/index",
    "pages/upload/index",
    "pages/profile/index"
  ],
  "tabBar": {
    "list": [
      { "pagePath": "pages/index/index", "text": "首页", "iconPath": "static/icons/home.png", "selectedIconPath": "static/icons/home-active.png" },
      { "pagePath": "pages/indicator/index", "text": "指标", "iconPath": "static/icons/chart.png", "selectedIconPath": "static/icons/chart-active.png" },
      { "pagePath": "pages/ai/index", "text": "AI", "iconPath": "static/icons/ai.png", "selectedIconPath": "static/icons/ai-active.png" },
      { "pagePath": "pages/upload/index", "text": "上传", "iconPath": "static/icons/upload.png", "selectedIconPath": "static/icons/upload-active.png" },
      { "pagePath": "pages/profile/index", "text": "我的", "iconPath": "static/icons/profile.png", "selectedIconPath": "static/icons/profile-active.png" }
    ]
  },
  "subpackages": [
    { "root": "subpackages/member", "pages": ["pages/detail/index", "pages/indicator/index", "pages/report/index"] },
    { "root": "subpackages/hospital", "pages": ["pages/overview/index", "pages/watch/index", "pages/compare/index"] },
    { "root": "subpackages/child", "pages": ["pages/dashboard/index", "pages/vaccine/index", "pages/growth/index"] }
  ],
  "preloadRule": {
    "pages/index/index": { "network": "all", "packages": ["member", "child"] }
  }
}
```

---

## 三、家庭成员共享前端实现

```
创建者流程：
我的页 → 邀请家人 → 调用 wx.shareAppMessage
    ↓
分享卡片：{"title": "邀请你加入张家", "path": "/pages/join/index?token=xxx"}
    ↓
被邀请人点击卡片 → 进入 pages/join/index
    ↓
join页面逻辑：
  1. 解析 token 参数
  2. 调用 wx.login 获取 code
  3. POST /api/members/join {token, code}
  4. 后端返回：{member, family, jwt_token}
  5. 前端自动保存 token 到 storage
  6. 弹出关系选择：["爸爸", "妈妈", "孩子", "其他"]
  7. PUT /api/members/me {relation}
  8. 自动跳转到首页，显示所有家庭成员
```

```javascript
// pages/join/index.js
Page({
  data: { token: null, loading: false, step: 'authorize' },

  onLoad(options) {
    this.setData({ token: options.token });
  },

  async onJoin() {
    this.setData({ loading: true });
    try {
      const { code } = await wx.login();
      const res = await api.post('/api/members/join', { token: this.data.token, code });
      wx.setStorageSync('access_token', res.jwt_token);
      this.setData({ step: 'choose_relation', member: res.member });
    } catch (e) {
      wx.showToast({ title: '邀请已过期或无效', icon: 'none' });
    }
  },

  async onChooseRelation(e) {
    const relation = e.currentTarget.dataset.relation;
    await api.put('/api/members/me', { relation });
    wx.switchTab({ url: '/pages/index/index' });
  }
});
```

---

## 四、微信订阅消息管理

```javascript
// utils/subscription.js
const SUBSCRIPTION_TEMPLATES = {
  daily_digest: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  urgent_alert: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
  review_reminder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
};

export const SubscriptionManager = {
  // 申请订阅授权（引导用户勾选模板）
  async request(templates = ['daily_digest', 'urgent_alert']) {
    const tmplIds = templates.map(t => SUBSCRIPTION_TEMPLATES[t]);
    const res = await wx.requestSubscribeMessage({ tmplIds });

    // 解析授权结果并同步到后端
    const status = {};
    templates.forEach(key => {
      const tmplId = SUBSCRIPTION_TEMPLATES[key];
      status[key] = res[tmplId] === 'accept';
    });

    await api.put('/api/members/me/subscription', status);
    return status;
  },

  // 检查某项是否已订阅
  async isSubscribed(templateKey) {
    // 本地缓存 + 后端查询
    const local = wx.getStorageSync('subscription_status') || {};
    if (templateKey in local) return local[templateKey];

    const { subscription_status } = await api.get('/api/members/me');
    wx.setStorageSync('subscription_status', subscription_status);
    return subscription_status[templateKey] || false;
  }
};
```

---

## 五、全局状态管理

不使用 Redux/MobX，采用基于 `Proxy` 的轻量级响应式 Store（~200行），原因：
- 小程序运行环境限制，第三方库增加包体积
- 状态逻辑不复杂，不需要完整 Redux 范式

```javascript
// utils/store.js — 核心实现思路
const createStore = (initialState) => {
  const callbacks = new Map();
  const state = new Proxy(initialState, {
    set(target, key, value) {
      const old = target[key];
      target[key] = value;
      if (old !== value && callbacks.has(key)) {
        callbacks.get(key).forEach(cb => cb(value, old));
      }
      return true;
    }
  });
  return {
    state,
    subscribe(key, cb) {
      if (!callbacks.has(key)) callbacks.set(key, new Set());
      callbacks.get(key).add(cb);
      return () => callbacks.get(key).delete(cb);
    }
  };
};

// 全局状态定义
const globalStore = createStore({
  familyId: null,           // 当前家庭ID
  members: [],              // 成员列表（缓存）
  currentMemberId: null,    // 当前选中成员
  currentHospitalId: null,  // 当前住院事件
  wsConnected: false,       // WebSocket连接状态
  unreadAI: false,          // AI未读消息红点
  isElderMode: false,       // 长辈模式
  networkStatus: 'online'   // 网络状态
});
```

---

## 六、HTTP 请求封装

```javascript
// utils/api.js — 封装思路
const API_BASE = 'https://api.health-helper.example.com';

const request = (method) => async (url, data = {}, options = {}) => {
  const token = wx.getStorageSync('access_token');
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}${url}`,
      method,
      data,
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 401) {
          // Token过期，静默刷新后重试
          refreshToken().then(() => request(method)(url, data, options));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(res.data.message || '请求失败'));
        }
      },
      fail: reject
    });
  });
};

export const api = {
  get: request('GET'),
  post: request('POST'),
  put: request('PUT'),
  del: request('DELETE')
};
```

---

## 七、WebSocket 客户端管理

```javascript
// utils/ws.js — WebSocket管理器核心逻辑
class WSManager {
  constructor() {
    this.socket = null;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.messageHandlers = new Map(); // 消息类型 -> 回调数组
    this.reconnectCount = 0;
    this.maxReconnect = 5;
  }

  connect(token) {
    this.socket = wx.connectSocket({
      url: `wss://api.health-helper.example.com/ws?token=${token}`
    });
    this.socket.onOpen(() => {
      this.reconnectCount = 0;
      this.startHeartbeat();
      globalStore.state.wsConnected = true;
    });
    this.socket.onMessage((res) => {
      const msg = JSON.parse(res.data);
      const handlers = this.messageHandlers.get(msg.type) || [];
      handlers.forEach(cb => cb(msg.payload));
    });
    this.socket.onClose(() => {
      globalStore.state.wsConnected = false;
      this.scheduleReconnect(token);
    });
    this.socket.onError(() => {
      this.scheduleReconnect(token);
    });
  }

  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000);
  }

  scheduleReconnect(token) {
    if (this.reconnectCount >= this.maxReconnect) return;
    const delay = Math.min(1000 * 2 ** this.reconnectCount, 30000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectCount++;
      this.connect(token);
    }, delay);
  }

  send(data) {
    if (this.socket && globalStore.state.wsConnected) {
      this.socket.send({ data: JSON.stringify(data) });
    }
  }

  on(type, handler) {
    if (!this.messageHandlers.has(type)) this.messageHandlers.set(type, []);
    this.messageHandlers.get(type).push(handler);
  }
}

export const wsManager = new WSManager();
```

---

## 八、趋势图组件

基于 ECharts-for-Weixin 封装。

```javascript
// components/trend-chart/index.js — 封装思路
Component({
  properties: {
    indicatorName: String,
    dataPoints: Array,      // [{ date, value, status }]
    lowerLimit: Number,
    upperLimit: Number,
    unit: String
  },
  data: {
    ec: { lazyLoad: true }
  },
  methods: {
    initChart() {
      this.selectComponent('#chart').init((canvas, width, height, dpr) => {
        const chart = echarts.init(canvas, null, { width, height, devicePixelRatio: dpr });
        const option = this.buildOption();
        chart.setOption(option);
        return chart;
      });
    },
    buildOption() {
      const { dataPoints, lowerLimit, upperLimit } = this.properties;
      return {
        grid: { top: 30, right: 20, bottom: 30, left: 50 },
        xAxis: { type: 'category', data: dataPoints.map(d => d.date) },
        yAxis: { type: 'value', name: this.properties.unit },
        series: [{
          data: dataPoints.map(d => d.value),
          type: 'line',
          smooth: true,
          markArea: {
            // 正常范围背景带（绿色）
            data: [[{
              yAxis: lowerLimit,
              itemStyle: { color: 'rgba(16, 185, 129, 0.1)' }
            }, { yAxis: upperLimit }]]
          },
          markLine: {
            // 参考线
            data: [
              { yAxis: lowerLimit, lineStyle: { color: '#10B981', type: 'dashed' } },
              { yAxis: upperLimit, lineStyle: { color: '#EF4444', type: 'dashed' } }
            ]
          }
        }]
      };
    }
  }
});
```

---

## 九、底部浮层组件

统一三种浮层的交互：趋势图 / AI对话 / 异常引导。

```javascript
// components/bottom-sheet/index.js — 核心手势逻辑
Component({
  properties: {
    visible: Boolean,
    height: { type: String, value: '60%' }  // 半屏60% / 全屏100%
  },
  data: { translateY: '100%', transition: false },
  observers: {
    'visible': function(v) {
      this.setData({ translateY: v ? '0%' : '100%', transition: true });
    }
  },
  methods: {
    onTouchStart(e) {
      this.startY = e.touches[0].clientY;
      this.startTranslate = 0;
    },
    onTouchMove(e) {
      const delta = e.touches[0].clientY - this.startY;
      if (delta > 0) { // 只允许下滑关闭
        this.setData({ translateY: `${delta}px`, transition: false });
      }
    },
    onTouchEnd(e) {
      const delta = e.changedTouches[0].clientY - this.startY;
      if (delta > 100) {
        this.triggerEvent('close');
      } else {
        this.setData({ translateY: '0%', transition: true });
      }
    }
  }
});
```

---

## 十、离线处理与弱网适配

微信小程序运行环境常处于弱网（医院电梯、地下室、WiFi限速）。前端需要具备基础离线能力。

**本地缓存策略**：

```javascript
// utils/offline.js
const CACHE_KEYS = {
  members: 'cache:members',
  indicators: 'cache:indicators',
  timeline: 'cache:timeline',
  pendingUploads: 'pending:uploads'  // 离线拍照队列
};

export const OfflineManager = {
  // 拍照后若网络不可用，存入本地待上传队列
  async queueUpload(imagePath, memberId = null) {
    const pending = wx.getStorageSync(CACHE_KEYS.pendingUploads) || [];
    pending.push({ imagePath, memberId, createdAt: Date.now() });
    wx.setStorageSync(CACHE_KEYS.pendingUploads, pending);
    wx.showToast({ title: '已保存，联网后自动上传', icon: 'none' });
  },

  // 网络恢复时自动重试上传
  async flushPendingUploads() {
    const pending = wx.getStorageSync(CACHE_KEYS.pendingUploads) || [];
    if (pending.length === 0) return;

    for (const item of pending) {
      try {
        await api.upload('/api/reports/upload', item.imagePath);
        // 成功则从队列移除
      } catch (e) {
        console.error('离线上传重试失败', e);
        break; // 保留剩余项，下次再试
      }
    }
  },

  // 首页成员列表缓存（有效期30分钟）
  cacheMembers(data) {
    wx.setStorageSync(CACHE_KEYS.members, {
      data,
      timestamp: Date.now()
    });
  },

  getCachedMembers() {
    const cached = wx.getStorageSync(CACHE_KEYS.members);
    if (!cached) return null;
    const age = Date.now() - cached.timestamp;
    if (age > 30 * 60 * 1000) return null; // 30分钟过期
    return cached.data;
  }
};

// app.js 全局网络状态监听
App({
  onLaunch() {
    wx.onNetworkStatusChange((res) => {
      if (res.isConnected) {
        OfflineManager.flushPendingUploads();
      }
      globalStore.state.networkStatus = res.isConnected ? 'online' : 'offline';
    });
  }
});
```

**弱网UI适配**：
- 首页：网络断开时显示缓存的成员卡片，状态文字变为灰色"上次更新于X分钟前"
- 上传流程：网络断开时提示"网络不稳定，已保存到草稿，恢复后自动上传"
- 时间轴/指标页：支持下拉刷新，失败时显示缓存数据+顶部黄色横幅
