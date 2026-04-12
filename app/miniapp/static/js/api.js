/**
 * NeuroSMM V2 Mini App — API Client
 * Wraps all backend endpoints with proper auth headers.
 */
const API = (() => {
  const BASE = '/api/v1';

  function _headers() {
    const h = { 'Content-Type': 'application/json' };
    // Telegram WebApp init data
    if (window.Telegram?.WebApp?.initData) {
      h['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData;
    }
    // Dev fallback
    const devId = sessionStorage.getItem('dev_user_id');
    if (devId) {
      h['X-Dev-User-Id'] = devId;
    }
    return h;
  }

  async function _request(method, path, body) {
    const opts = { method, headers: _headers() };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${BASE}${path}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    // Bootstrap
    getMe: () => _request('GET', '/me'),

    // Projects
    createProject: (data) => _request('POST', '/projects', data),
    listProjects: () => _request('GET', '/projects'),
    getProject: (pid) => _request('GET', `/projects/${pid}`),
    updateProject: (pid, data) => _request('PATCH', `/projects/${pid}`, data),
    deactivateProject: (pid) => _request('POST', `/projects/${pid}/deactivate`),
    activateProject: (pid) => _request('POST', `/projects/${pid}/activate`),

    // Drafts
    createDraft: (pid, data) => _request('POST', `/projects/${pid}/drafts`, data),
    listDrafts: (pid) => _request('GET', `/projects/${pid}/drafts`),
    getDraft: (pid, did) => _request('GET', `/projects/${pid}/drafts/${did}`),
    updateDraft: (pid, did, data) => _request('PATCH', `/projects/${pid}/drafts/${did}`, data),
    markReady: (pid, did) => _request('POST', `/projects/${pid}/drafts/${did}/ready`),
    backToDraft: (pid, did) => _request('POST', `/projects/${pid}/drafts/${did}/back-to-draft`),
    archiveDraft: (pid, did) => _request('POST', `/projects/${pid}/drafts/${did}/archive`),

    // Generation
    generateText: (pid, did, data) => _request('POST', `/projects/${pid}/drafts/${did}/generate/text`, data),
    generateImage: (pid, did) => _request('POST', `/projects/${pid}/drafts/${did}/generate/image`),

    // Publishing
    previewDraft: (pid, did) => _request('GET', `/projects/${pid}/drafts/${did}/preview`),
    publishDraft: (pid, did) => _request('POST', `/projects/${pid}/drafts/${did}/publish`),

    // Scheduling
    scheduleDraft: (pid, did, data) => _request('POST', `/projects/${pid}/drafts/${did}/schedule`, data),
    listSchedules: (pid) => _request('GET', `/projects/${pid}/schedules`),
    cancelSchedule: (pid, sid) => _request('POST', `/projects/${pid}/schedules/${sid}/cancel`),
    retrySchedule: (pid, sid, data) => _request('POST', `/projects/${pid}/schedules/${sid}/retry`, data),

    // Channel
    bindChannel: (pid, data) => _request('POST', `/projects/${pid}/channel/bind`, data),
    channelStatus: (pid) => _request('GET', `/projects/${pid}/channel/status`),

    // Health
    health: () => _request('GET', '/health'),
  };
})();
