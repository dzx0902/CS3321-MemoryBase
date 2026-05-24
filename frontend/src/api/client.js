const BASE = '/api';

function formatErrorDetail(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const location = Array.isArray(item.loc) ? item.loc.join('.') : item.loc;
        return [location, item.msg].filter(Boolean).join(': ');
      })
      .filter(Boolean)
      .join('; ') || fallback;
  }
  if (typeof detail === 'object') {
    if (detail.message) return detail.message;
    if (detail.detail) return formatErrorDetail(detail.detail, fallback);
    return JSON.stringify(detail);
  }
  return String(detail);
}

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const err = new Error(formatErrorDetail(detail.detail ?? detail, `HTTP ${res.status}`));
    err.status = res.status;
    err.data = detail;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function qs(params) {
  if (!params) return '';
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, v);
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
}

// ===== Sources =====
export const sourcesApi = {
  list: (params) => request(`/sources${qs(params)}`),
  create: (body) => request('/sources', { method: 'POST', body }),
  detail: (docId, params) => request(`/sources/${docId}${qs(params)}`),
};

// ===== Memories =====
export const memoriesApi = {
  list: (params) => request(`/memories${qs(params)}`),
  create: (body) => request('/memories', { method: 'POST', body }),
  detail: (memoryId, params) => request(`/memories/${memoryId}${qs(params)}`),
  update: (memoryId, body, params = {}, actorHeaders = {}) =>
    request(`/memories/${memoryId}${qs(params)}`, {
      method: 'PATCH',
      body,
      headers: {
        'X-Actor-Type': actorHeaders.actorType || 'user',
        'X-Revision-Reason': actorHeaders.revisionReason || 'Manual update',
        ...(actorHeaders.actorId ? { 'X-Actor-Id': actorHeaders.actorId } : {}),
        ...actorHeaders.extra,
      },
    }),
  remove: (memoryId, params = {}, actorHeaders = {}) =>
    request(`/memories/${memoryId}${qs(params)}`, {
      method: 'DELETE',
      headers: {
        'X-Actor-Type': actorHeaders.actorType || 'user',
        'X-Revision-Reason': actorHeaders.revisionReason || 'Manual deletion',
        ...(actorHeaders.actorId ? { 'X-Actor-Id': actorHeaders.actorId } : {}),
      },
    }),
};

// ===== Recall =====
export const recallApi = {
  search: (body) => request('/recall', { method: 'POST', body }),
};

// ===== Wiki =====
export const wikiApi = {
  export: (body) => request('/wiki/export', { method: 'POST', body }),
};

// ===== Governance =====
export const policiesApi = {
  list: (params) => request(`/policies${qs(params)}`),
  create: (body) => request('/policies', { method: 'POST', body }),
};

export const auditApi = {
  list: (params) => request(`/audit${qs(params)}`),
};

export const conflictsApi = {
  list: (params) => request(`/conflicts${qs(params)}`),
  update: (conflictId, params, body) => request(`/conflicts/${conflictId}${qs(params)}`, { method: 'PATCH', body }),
};

export const forgetRequestsApi = {
  list: (params) => request(`/forget-requests${qs(params)}`),
  create: (body) => request('/forget-requests', { method: 'POST', body }),
  update: (requestId, params, body) => request(`/forget-requests/${requestId}${qs(params)}`, { method: 'PATCH', body }),
};

export const timelineApi = {
  list: (params) => request(`/timeline${qs(params)}`),
  create: (body) => request('/timeline', { method: 'POST', body }),
};
