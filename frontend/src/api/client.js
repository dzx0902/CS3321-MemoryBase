const BASE = '/api';

// Centralize FastAPI error-shape handling so pages can show useful validation,
// 404, and service-error messages without duplicating response parsing.
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
  // The Vite dev proxy and production backend both expose API routes under /api.
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
  // Drop empty filters so list endpoints keep their documented defaults.
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
  contextPack: (body) => request('/recall/context-pack', { method: 'POST', body }),
};

export const qaApi = {
  answer: (body) => request('/qa/answer', { method: 'POST', body }),
};

export const searchApi = {
  search: (body) => request('/search', { method: 'POST', body }),
};

export const sessionsApi = {
  list: (params) => request(`/sessions${qs(params)}`),
  create: (body) => request('/sessions', { method: 'POST', body }),
  detail: (sessionId, params) => request(`/sessions/${sessionId}${qs(params)}`),
  messages: (sessionId, params) => request(`/sessions/${sessionId}/messages${qs(params)}`),
};

export const observeApi = {
  create: (body) => request('/observe', { method: 'POST', body }),
  batch: (body) => request('/observe/batch', { method: 'POST', body }),
};

export const agentsApi = {
  register: (body) => request('/agents/register', { method: 'POST', body }),
  visibleMemories: (agentId, params) => request(`/agents/${agentId}/visible-memories${qs(params)}`),
};

// ===== Wiki =====
export const wikiApi = {
  list: (params) => request(`/wiki${qs(params)}`),
  detail: (pageId, params) => request(`/wiki/${pageId}${qs(params)}`),
  revisions: (pageId, params) => request(`/wiki/${pageId}/revisions${qs(params)}`),
  export: (body) => request('/wiki/export', { method: 'POST', body }),
};

export const statsApi = {
  overview: (params) => request(`/stats/overview${qs(params)}`),
};

export const semanticApi = {
  entities: (params) => request(`/entities${qs(params)}`),
  scenes: (params) => request(`/scenes${qs(params)}`),
};

export const graphApi = {
  health: () => request('/graph/health'),
  workspace: (params) => request(`/graph/workspace${qs(params)}`),
  preview: (params) => request(`/graph/workspace/preview${qs(params)}`),
  sync: (params) => request(`/graph/workspace/sync${qs(params)}`, { method: 'POST' }),
};

// ===== Governance =====
export const policiesApi = {
  list: (params) => request(`/policies${qs(params)}`),
  create: (body) => request('/policies', { method: 'POST', body }),
  update: (policyId, params, body) => request(`/policies/${policyId}${qs(params)}`, { method: 'PATCH', body }),
  remove: (policyId, params) => request(`/policies/${policyId}${qs(params)}`, { method: 'DELETE' }),
};

export const auditApi = {
  list: (params) => request(`/audit${qs(params)}`),
  lifecycle: (params) => request(`/audit/lifecycle${qs(params)}`),
  statistics: (params) => request(`/audit/statistics${qs(params)}`),
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
