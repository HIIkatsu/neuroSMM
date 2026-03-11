const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  document.body.classList.add('telegram');
}

const state = {
  ownerId: 0,
  owners: [],
  data: null,
  activeTab: 'dashboard',
  loading: false,
};

function escapeHtml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function nl2br(str = '') {
  return escapeHtml(str).replace(/\n/g, '<br>');
}

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const res = await fetch(path, { ...options, headers });

  const contentType = res.headers.get('content-type') || '';
  let payload = null;
  try {
    payload = contentType.includes('application/json') ? await res.json() : await res.text();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    const detail = (payload && (payload.detail || payload.error || payload.message)) || `Ошибка ${res.status}`;
    throw new Error(detail);
  }

  return payload;
}

function toast(message) {
  const wrap = document.querySelector('.toast-wrap') || document.body.appendChild(Object.assign(document.createElement('div'), { className: 'toast-wrap' }));
  wrap.innerHTML = '';
  const node = Object.assign(document.createElement('div'), { className: 'toast', textContent: message });
  wrap.appendChild(node);
  setTimeout(() => node.remove(), 2600);
}

function closeModal() {
  document.getElementById('modal-root')?.classList.remove('open');
}

function modal(title, bodyHtml, actionsHtml = '') {
  let root = document.getElementById('modal-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'modal-root';
    root.className = 'modal-backdrop';
    document.body.appendChild(root);
  }
  root.innerHTML = `
    <div class="modal">
      <div class="modal-head">
        <div>
          <div class="section-title">${escapeHtml(title)}</div>
        </div>
        <button class="btn small ghost" id="modal-close">Закрыть</button>
      </div>
      <div class="stack">${bodyHtml}</div>
      ${actionsHtml ? `<div class="item-actions" style="margin-top:16px">${actionsHtml}</div>` : ''}
    </div>
  `;
  root.classList.add('open');
  document.getElementById('modal-close').onclick = closeModal;
  root.onclick = (e) => { if (e.target === root) closeModal(); };
}

function formatDateTime(dt) {
  const raw = String(dt || '');
  if (!raw) return '—';
  const normalized = raw.replace(' ', 'T');
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function activeChannel() {
  return state.data?.active_channel || null;
}

async function loadBootstrap(ownerId = state.ownerId || 0) {
  state.loading = true;
  render();
  try {
    const data = await api(`/api/bootstrap?owner_id=${ownerId}`);
    state.data = data;
    state.ownerId = data.owner_id;
    state.owners = data.owners || [];
  } catch (e) {
    toast(e.message);
  } finally {
    state.loading = false;
    render();
  }
}

function navBtn(id, title, icon) {
  return `<button class="nav-btn ${state.activeTab === id ? 'active' : ''}" onclick="state.activeTab='${id}';render()"><div>${icon}</div><div>${title}</div></button>`;
}

function dashboardView() {
  const stats = state.data?.stats || {};
  const active = activeChannel();
  const nextPlan = (state.data?.plan || []).filter(x => !x.posted).sort((a, b) => (a.dt > b.dt ? 1 : -1))[0];
  const settings = state.data?.settings || {};
  return `
    <div class="hero">
      <div class="card hero-main"><div class="card-inner">
        <div class="eyebrow">Telegram Mini App</div>
        <div class="title">NeuroSMM</div>
        <div class="subtitle">Упрощённая и более рабочая панель: каналы, черновики, контент-план, слоты и настройки без каши из кнопок.</div>
        <div class="badges">
          <div class="badge">Канал: ${escapeHtml(active?.title || 'не выбран')}</div>
          <div class="badge">Тема: ${escapeHtml(settings.topic || 'не задана')}</div>
          <div class="badge">${settings.posts_enabled === '1' ? 'Постинг включён' : 'Постинг выключен'}</div>
        </div>
      </div></div>
      <div class="stat-grid">
        <div class="stat"><div class="stat-label">Опубликовано</div><div class="stat-value">${stats.total_posts || 0}</div></div>
        <div class="stat"><div class="stat-label">Черновики</div><div class="stat-value">${(state.data?.drafts || []).length}</div></div>
        <div class="stat"><div class="stat-label">План</div><div class="stat-value">${stats.plan_total || 0}</div></div>
        <div class="stat"><div class="stat-label">Слоты</div><div class="stat-value">${stats.schedules_total || 0}</div></div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card"><div class="card-inner">
        <div class="section-head">
          <div>
            <div class="section-title">Быстрые действия</div>
            <div class="section-desc">Самые частые действия без лишних окон.</div>
          </div>
        </div>
        <div class="grid-2">
          <button class="btn primary" onclick="openDraftEditor()">Новый пост</button>
          <button class="btn secondary" onclick="openGenerateDraftModal()">✨ Сгенерировать</button>
          <button class="btn" onclick="state.activeTab='plan';render()">Контент-план</button>
          <button class="btn" onclick="state.activeTab='channels';render()">Каналы</button>
        </div>
      </div></div>
      <div class="card"><div class="card-inner">
        <div class="section-head">
          <div>
            <div class="section-title">Ближайшая публикация</div>
            <div class="section-desc">Следующий элемент из контент-плана.</div>
          </div>
        </div>
        ${nextPlan ? `
          <div class="item">
            <div class="item-title">${escapeHtml(nextPlan.prompt || nextPlan.topic || 'Без текста')}</div>
            <div class="item-sub">${formatDateTime(nextPlan.dt)}</div>
          </div>
        ` : `<div class="empty">План пока пустой. Сгенерируй его или добавь элемент вручную.</div>`}
      </div></div>
    </div>
  `;
}

function channelsView() {
  const channels = state.data?.channels || [];
  const activeId = state.data?.active_channel?.id;
  return `
    <div class="section-head">
      <div>
        <div class="section-title">Каналы</div>
        <div class="section-desc">Быстро переключай активный канал и редактируй тему без чата.</div>
      </div>
      <button class="btn primary" onclick="openChannelModal()">Добавить канал</button>
    </div>
    <div class="list">
      ${channels.length ? channels.map(ch => `
        <div class="item">
          <div class="item-row">
            <div>
              <div class="item-title">${escapeHtml(ch.title)}</div>
              <div class="item-sub">${escapeHtml(ch.channel_target)}\n${escapeHtml(ch.topic || 'Тема не указана')}</div>
            </div>
            ${activeId === ch.id ? '<div class="badge">Активный</div>' : ''}
          </div>
          <div class="item-actions">
            ${activeId === ch.id ? '<button class="btn small ghost" disabled>Используется сейчас</button>' : `<button class="btn small primary" onclick="activateChannel(${ch.id})">Сделать активным</button>`}
          </div>
        </div>`).join('') : '<div class="empty">Список каналов пока пустой.</div>'}
    </div>
  `;
}

function draftCard(d) {
  const hasChannel = !!String(d.channel_target || '').trim();
  const text = (d.text || d.prompt || 'Без текста').trim();
  const subtitleBits = [
    `Канал: ${d.channel_target || 'не выбран'}`,
    `Тип: ${d.media_type || 'none'}`,
    `Статус: ${d.status || 'draft'}`,
  ];
  return `
    <div class="item">
      <div class="item-row">
        <div>
          <div class="item-title">${escapeHtml(text.slice(0, 120) || 'Без текста')}</div>
          <div class="item-sub">${escapeHtml(subtitleBits.join(' · '))}</div>
        </div>
        ${hasChannel ? '<div class="badge">Готов к публикации</div>' : '<div class="badge">Нужно выбрать канал</div>'}
      </div>
      <div class="item-actions">
        <button class="btn small" onclick="openDraftEditor(${d.id})">Редактировать</button>
        <button class="btn small ghost" onclick="previewDraft(${d.id})">Предпросмотр</button>
        ${hasChannel
          ? `<button class="btn small secondary" onclick="publishDraft(${d.id})">Опубликовать</button>`
          : `<button class="btn small ghost" onclick="openDraftEditor(${d.id})">Выбрать канал</button>`}
        <button class="btn small danger" onclick="deleteDraft(${d.id})">Удалить</button>
      </div>
    </div>
  `;
}

function draftsView() {
  const drafts = state.data?.drafts || [];
  return `
    <div class="section-head">
      <div>
        <div class="section-title">Черновики</div>
        <div class="section-desc">Редактирование без перегруза: сначала главное, всё остальное — в дополнительных настройках.</div>
      </div>
      <div class="item-actions">
        <button class="btn secondary" onclick="openGenerateDraftModal()">✨ Сгенерировать</button>
        <button class="btn primary" onclick="openDraftEditor()">Новый черновик</button>
      </div>
    </div>
    <div class="list">
      ${drafts.length ? drafts.map(draftCard).join('') : '<div class="empty">Черновиков пока нет.</div>'}
    </div>
  `;
}

function planView() {
  const items = (state.data?.plan || []).slice().sort((a, b) => (a.dt > b.dt ? 1 : -1));
  return `
    <div class="section-head">
      <div>
        <div class="section-title">Контент-план</div>
        <div class="section-desc">Генерируй на период или добавляй отдельные элементы вручную.</div>
      </div>
      <div class="item-actions">
        <button class="btn secondary" onclick="openPlanGenerator()">Сгенерировать</button>
        <button class="btn primary" onclick="openPlanEditor()">Добавить вручную</button>
      </div>
    </div>
    <div class="calendar">
      ${items.length ? items.map(item => `
        <div class="calendar-day">
          <div class="calendar-date">${formatDateTime(item.dt)}</div>
          <div class="calendar-title">${escapeHtml(item.prompt || item.topic || 'Пустой элемент')}</div>
          <div class="item-actions">
            <button class="btn small" onclick="openPlanEditor(${item.id})">Редактировать</button>
            <button class="btn small danger" onclick="deletePlanItem(${item.id})">Удалить</button>
          </div>
        </div>`).join('') : '<div class="empty">План пока пустой.</div>'}
    </div>
  `;
}

function schedulesView() {
  const rows = state.data?.schedules || [];
  return `
    <div class="section-head">
      <div>
        <div class="section-title">Слоты</div>
        <div class="section-desc">Временные окна, по которым бот публикует автоматически.</div>
      </div>
      <button class="btn primary" onclick="openScheduleModal()">Добавить слот</button>
    </div>
    <div class="list">
      ${rows.length ? rows.map(row => `
        <div class="item">
          <div class="item-row">
            <div>
              <div class="item-title">${escapeHtml(row.time_hhmm)}</div>
              <div class="item-sub">${escapeHtml(row.days_label || row.days || '*')}</div>
            </div>
          </div>
          <div class="item-actions">
            <button class="btn small danger" onclick="deleteSchedule(${row.id})">Удалить</button>
          </div>
        </div>`).join('') : '<div class="empty">Слоты пока не добавлены.</div>'}
    </div>
  `;
}

function settingsView() {
  const s = state.data?.settings || {};
  return `
    <div class="section-head">
      <div>
        <div class="section-title">Настройки</div>
        <div class="section-desc">Основные параметры канала и автопостинга.</div>
      </div>
      <button class="btn primary" onclick="saveSettings()">Сохранить</button>
    </div>
    <div class="grid-2">
      <div class="card"><div class="card-inner stack">
        <label class="switch"><input type="checkbox" id="set-posts-enabled" ${s.posts_enabled === '1' ? 'checked' : ''}/> <span>Постинг включён</span></label>
        <label class="switch"><input type="checkbox" id="set-news-enabled" ${s.news_enabled === '1' ? 'checked' : ''}/> <span>Авто-новости включены</span></label>
        <div class="field">
          <div class="label">Режим публикации</div>
          <select class="select" id="set-posting-mode">${['both','news','posts'].map(m => `<option value="${m}" ${s.posting_mode === m ? 'selected' : ''}>${m}</option>`).join('')}</select>
        </div>
        <div class="field">
          <div class="label">Интервал новостей, часы</div>
          <input class="input" id="set-news-interval" value="${escapeHtml(s.news_interval_hours || '6')}" />
        </div>
      </div></div>
      <div class="card"><div class="card-inner stack">
        <div class="field">
          <div class="label">Тема канала</div>
          <textarea class="textarea" id="set-topic">${escapeHtml(s.topic || '')}</textarea>
        </div>
        <div class="field">
          <div class="label">Источники новостей</div>
          <textarea class="textarea" id="set-news-sources">${escapeHtml(s.news_sources || '')}</textarea>
        </div>
      </div></div>
    </div>
  `;
}

function renderBody() {
  switch (state.activeTab) {
    case 'channels': return channelsView();
    case 'drafts': return draftsView();
    case 'plan': return planView();
    case 'schedules': return schedulesView();
    case 'settings': return settingsView();
    default: return dashboardView();
  }
}

function render() {
  const root = document.getElementById('app');
  if (!state.data && state.loading) {
    root.innerHTML = `<div class="shell loading"><div class="loading-card"><div class="spinner"></div><div class="section-title">Загружаю панель…</div></div></div>`;
    return;
  }
  root.innerHTML = `
    <div class="shell">
      <div class="topbar">
        <div class="brand">
          <div class="eyebrow">Telegram Mini App</div>
          <div class="title">NeuroSMM</div>
          <div class="subtitle">Красивый интерфейс — хорошо. Рабочий интерфейс — лучше. Эта версия проще, чище и безопаснее в публикации.</div>
        </div>
        <select class="owner-switch" id="owner-switch">
          ${(state.owners || []).length ? state.owners.map(id => `<option value="${id}" ${Number(id) === Number(state.ownerId) ? 'selected' : ''}>ID ${id}</option>`).join('') : '<option value="0">ID 0</option>'}
        </select>
      </div>
      <div class="panel">${renderBody()}</div>
      <div class="bottom-nav">
        ${navBtn('dashboard','Главная','⌂')}
        ${navBtn('channels','Каналы','◎')}
        ${navBtn('drafts','Черновики','✎')}
        ${navBtn('plan','План','▣')}
        ${navBtn('schedules','Слоты','◷')}
        ${navBtn('settings','Настройки','⚙')}
      </div>
    </div>
  `;
  document.getElementById('owner-switch').onchange = (e) => loadBootstrap(Number(e.target.value));
}

async function activateChannel(profileId) {
  try {
    await api('/api/channels/activate', {
      method: 'POST',
      body: JSON.stringify({ owner_id: state.ownerId, profile_id: profileId })
    });
    toast('Активный канал обновлён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

function openChannelModal() {
  modal('Новый канал', `
    <div class="field"><div class="label">Название</div><input class="input" id="ch-title" placeholder="Например, Чиповые новости"></div>
    <div class="field"><div class="label">Канал / chat_id / @username</div><input class="input" id="ch-target" placeholder="@my_channel"></div>
    <div class="field"><div class="label">Тема канала</div><textarea class="textarea" id="ch-topic" placeholder="О чём канал"></textarea></div>
    <label class="switch"><input type="checkbox" id="ch-active" checked> <span>Сделать активным сразу</span></label>
  `, `<button class="btn primary" onclick="saveChannel()">Сохранить</button>`);
}

async function saveChannel() {
  try {
    await api('/api/channels', {
      method: 'POST',
      body: JSON.stringify({
        owner_id: state.ownerId,
        title: document.getElementById('ch-title').value,
        channel_target: document.getElementById('ch-target').value,
        topic: document.getElementById('ch-topic').value,
        make_active: document.getElementById('ch-active').checked,
      })
    });
    closeModal();
    toast('Канал сохранён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

function draftEditorHtml(draft) {
  const currentChannel = draft?.channel_target || activeChannel()?.channel_target || state.data?.settings?.channel_target || '';
  const currentTopic = draft?.topic || state.data?.settings?.topic || '';
  return `
    <div class="field">
      <div class="label">Текст поста</div>
      <textarea class="textarea" id="dr-text" placeholder="Текст поста">${escapeHtml(draft?.text || '')}</textarea>
    </div>
    <div class="grid-2">
      <div class="field">
        <div class="label">Канал</div>
        <input class="input" id="dr-channel" value="${escapeHtml(currentChannel)}" placeholder="@channel или chat_id">
      </div>
      <div class="field">
        <div class="label">Тема</div>
        <input class="input" id="dr-topic" value="${escapeHtml(currentTopic)}" placeholder="Тема поста">
      </div>
    </div>
    <div class="field">
      <div class="label">Картинка (URL или file_id)</div>
      <input class="input" id="dr-media-ref" value="${escapeHtml(draft?.media_ref || '')}" placeholder="https://... или Telegram file_id">
    </div>
    <div class="note">Главное — текст, канал, тема и картинка. Остальные настройки спрятаны ниже, чтобы окно не выглядело перегруженным.</div>
    <label class="adv-toggle"><input type="checkbox" id="adv-toggle" onchange="toggleAdvanced()"> <span>Показать дополнительные настройки</span></label>
    <div class="advanced" id="advanced-box">
      <div class="stack">
        <div class="field">
          <div class="label">Промпт</div>
          <textarea class="textarea" id="dr-prompt" placeholder="Промпт для генерации или служебная заметка">${escapeHtml(draft?.prompt || '')}</textarea>
        </div>
        <div class="grid-2">
          <div class="field">
            <div class="label">Тип медиа</div>
            <select class="select" id="dr-media-type">${['none','photo'].map(v => `<option value="${v}" ${draft?.media_type === v ? 'selected' : ''}>${v}</option>`).join('')}</select>
          </div>
          <div class="field">
            <div class="label">Кнопки JSON</div>
            <input class="input" id="dr-buttons" value="${escapeHtml(draft?.buttons_json || '[]')}" placeholder='[{"text":"Сайт","url":"https://..."}]'>
          </div>
        </div>
        <div class="grid-3">
          <label class="switch"><input type="checkbox" id="dr-pin" ${draft?.pin_post ? 'checked' : ''}> <span>Закрепить</span></label>
          <label class="switch"><input type="checkbox" id="dr-comments" ${draft?.comments_enabled !== 0 ? 'checked' : ''}> <span>Комментарии</span></label>
          <label class="switch"><input type="checkbox" id="dr-ad" ${draft?.ad_mark ? 'checked' : ''}> <span>Реклама</span></label>
        </div>
      </div>
    </div>
  `;
}

function openDraftEditor(draftId = null) {
  const draft = draftId ? (state.data?.drafts || []).find(d => Number(d.id) === Number(draftId)) : null;
  modal(
    draft ? 'Редактор черновика' : 'Новый черновик',
    draftEditorHtml(draft),
    draft
      ? `<button class="btn" onclick="previewDraft(${draft.id})">Предпросмотр</button><button class="btn primary" onclick="saveDraft(${draft.id})">Сохранить</button>`
      : `<button class="btn primary" onclick="createDraft()">Создать</button>`
  );
}

function toggleAdvanced() {
  const box = document.getElementById('advanced-box');
  if (box) box.classList.toggle('open', document.getElementById('adv-toggle').checked);
}

function readDraftForm() {
  const buttonsInput = document.getElementById('dr-buttons');
  return {
    owner_id: state.ownerId,
    text: document.getElementById('dr-text').value,
    prompt: document.getElementById('dr-prompt')?.value || '',
    channel_target: document.getElementById('dr-channel').value,
    topic: document.getElementById('dr-topic').value,
    media_type: document.getElementById('dr-media-type')?.value || (document.getElementById('dr-media-ref').value ? 'photo' : 'none'),
    media_ref: document.getElementById('dr-media-ref').value,
    buttons_json: buttonsInput ? buttonsInput.value : '[]',
    pin_post: document.getElementById('dr-pin')?.checked ? 1 : 0,
    comments_enabled: document.getElementById('dr-comments')?.checked ? 1 : 0,
    ad_mark: document.getElementById('dr-ad')?.checked ? 1 : 0,
  };
}

async function createDraft() {
  try {
    const body = readDraftForm();
    if (!body.text.trim() && !body.prompt.trim()) {
      toast('Добавь текст поста или промпт');
      return;
    }
    await api('/api/drafts', { method: 'POST', body: JSON.stringify(body) });
    closeModal();
    toast('Черновик создан');
    await loadBootstrap(state.ownerId);
    state.activeTab = 'drafts';
    render();
  } catch (e) {
    toast(e.message);
  }
}

async function saveDraft(id) {
  try {
    const body = readDraftForm();
    await api(`/api/drafts/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
    closeModal();
    toast('Черновик обновлён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

async function deleteDraft(id) {
  if (!confirm('Удалить черновик?')) return;
  try {
    await api(`/api/drafts/${id}?owner_id=${state.ownerId}`, { method: 'DELETE' });
    toast('Черновик удалён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

function previewDraft(id) {
  const draft = (state.data?.drafts || []).find(d => Number(d.id) === Number(id));
  if (!draft) {
    toast('Черновик не найден');
    return;
  }
  modal('Предпросмотр поста', `
    <div class="item">
      <div class="item-title">${nl2br((draft.text || draft.prompt || 'Без текста').trim())}</div>
      <div class="chips">
        <div class="chip">Канал: ${escapeHtml(draft.channel_target || 'не выбран')}</div>
        <div class="chip">Тип: ${escapeHtml(draft.media_type || 'none')}</div>
        ${draft.media_ref ? `<div class="chip">Есть картинка</div>` : ''}
      </div>
    </div>
  `, `<button class="btn primary" onclick="closeModal()">Понятно</button>`);
}

async function publishDraft(id) {
  try {
    const draft = (state.data?.drafts || []).find(d => Number(d.id) === Number(id));
    if (!draft) {
      toast('Черновик не найден');
      return;
    }
    if (!draft.channel_target || !String(draft.channel_target).trim()) {
      toast('Сначала выбери канал в редакторе');
      openDraftEditor(id);
      return;
    }
    await api('/api/drafts/publish', {
      method: 'POST',
      body: JSON.stringify({ owner_id: state.ownerId, draft_id: id })
    });
    toast('Пост опубликован');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message || 'Ошибка отправки в Telegram');
  }
}

function openGenerateDraftModal() {
  modal('Сгенерировать черновик', `
    <div class="field">
      <div class="label">Что нужно сгенерировать</div>
      <textarea class="textarea" id="gd-prompt" placeholder="Напиши, что именно сгенерировать. Можно коротко: пост про тренды в полупроводниках для Telegram-канала."></textarea>
    </div>
    <div class="note">Используется текущий AI-слой твоего бота. Если ключ и роутер уже настроены, готовый черновик появится в базе сразу.</div>
  `, `<button class="btn primary" onclick="generateDraft()">Создать черновик</button>`);
}

async function generateDraft() {
  try {
    await api('/api/drafts/generate', {
      method: 'POST',
      body: JSON.stringify({ owner_id: state.ownerId, prompt: document.getElementById('gd-prompt').value })
    });
    closeModal();
    toast('ИИ-черновик создан');
    await loadBootstrap(state.ownerId);
    state.activeTab = 'drafts';
    render();
  } catch (e) {
    toast(e.message);
  }
}

function openPlanGenerator() {
  modal('Генерация контент-плана', `
    <div class="grid-2">
      <div class="field"><div class="label">Стартовая дата</div><input class="input" id="pg-date" type="date"></div>
      <div class="field"><div class="label">Время первого поста</div><input class="input" id="pg-time" type="time" value="10:00"></div>
    </div>
    <div class="grid-2">
      <div class="field"><div class="label">Сколько дней</div><select class="select" id="pg-days">${[7,14,30,60].map(v => `<option value="${v}">${v}</option>`).join('')}</select></div>
      <div class="field"><div class="label">Постов в день</div><select class="select" id="pg-ppd">${[1,2,3].map(v => `<option value="${v}">${v}</option>`).join('')}</select></div>
    </div>
    <div class="field"><div class="label">Тема</div><textarea class="textarea" id="pg-topic">${escapeHtml(state.data?.settings?.topic || '')}</textarea></div>
    <label class="switch"><input type="checkbox" id="pg-clear"> <span>Очистить старый непубликованный план</span></label>
  `, `<button class="btn primary" onclick="generatePlan()">Создать план</button>`);
}

async function generatePlan() {
  try {
    await api('/api/plan/generate', {
      method: 'POST',
      body: JSON.stringify({
        owner_id: state.ownerId,
        start_date: document.getElementById('pg-date').value,
        post_time: document.getElementById('pg-time').value,
        days: Number(document.getElementById('pg-days').value),
        posts_per_day: Number(document.getElementById('pg-ppd').value),
        topic: document.getElementById('pg-topic').value,
        clear_existing: document.getElementById('pg-clear').checked,
      })
    });
    closeModal();
    toast('Контент-план создан');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

function openPlanEditor(itemId = null) {
  const item = itemId ? (state.data?.plan || []).find(p => Number(p.id) === Number(itemId)) : null;
  modal(item ? 'Редактировать элемент плана' : 'Новый элемент плана', `
    <div class="field"><div class="label">Дата и время</div><input class="input" id="pl-dt" type="datetime-local" value="${escapeHtml(item?.dt ? String(item.dt).replace(' ', 'T').slice(0,16) : '')}"></div>
    <div class="field"><div class="label">Промпт</div><textarea class="textarea" id="pl-prompt">${escapeHtml(item?.prompt || '')}</textarea></div>
    <div class="field"><div class="label">Тема</div><input class="input" id="pl-topic" value="${escapeHtml(item?.topic || '')}"></div>
  `, item ? `<button class="btn primary" onclick="savePlanItem(${item.id})">Сохранить</button>` : `<button class="btn primary" onclick="createPlanItem()">Создать</button>`);
}

async function createPlanItem() {
  try {
    await api('/api/plan', {
      method: 'POST',
      body: JSON.stringify({
        owner_id: state.ownerId,
        dt: document.getElementById('pl-dt').value,
        prompt: document.getElementById('pl-prompt').value,
        topic: document.getElementById('pl-topic').value,
      })
    });
    closeModal();
    toast('Элемент добавлен');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

async function savePlanItem(id) {
  try {
    await api(`/api/plan/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        owner_id: state.ownerId,
        dt: document.getElementById('pl-dt').value,
        prompt: document.getElementById('pl-prompt').value,
        topic: document.getElementById('pl-topic').value,
      })
    });
    closeModal();
    toast('Элемент обновлён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

async function deletePlanItem(id) {
  if (!confirm('Удалить элемент плана?')) return;
  try {
    await api(`/api/plan/${id}?owner_id=${state.ownerId}`, { method: 'DELETE' });
    toast('Элемент удалён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

function openScheduleModal() {
  modal('Новый слот расписания', `
    <div class="field"><div class="label">Время</div><input class="input" id="sc-time" type="time"></div>
    <div class="field"><div class="label">Дни</div><input class="input" id="sc-days" value="*" placeholder="* или пн,ср,пт"></div>
    <div class="note">Поддерживается формат <b>*</b> или строка вроде <b>пн,ср,пт</b>. Это не ломает текущий планировщик и хранится в той же БД.</div>
  `, `<button class="btn primary" onclick="createSchedule()">Сохранить</button>`);
}

async function createSchedule() {
  try {
    await api('/api/schedules', {
      method: 'POST',
      body: JSON.stringify({
        owner_id: state.ownerId,
        time_hhmm: document.getElementById('sc-time').value,
        days: document.getElementById('sc-days').value,
      })
    });
    closeModal();
    toast('Слот добавлен');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

async function deleteSchedule(id) {
  if (!confirm('Удалить слот?')) return;
  try {
    await api(`/api/schedules/${id}?owner_id=${state.ownerId}`, { method: 'DELETE' });
    toast('Слот удалён');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

async function saveSettings() {
  try {
    await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        owner_id: state.ownerId,
        posts_enabled: document.getElementById('set-posts-enabled').checked ? '1' : '0',
        news_enabled: document.getElementById('set-news-enabled').checked ? '1' : '0',
        posting_mode: document.getElementById('set-posting-mode').value,
        news_interval_hours: document.getElementById('set-news-interval').value,
        news_sources: document.getElementById('set-news-sources').value,
        topic: document.getElementById('set-topic').value,
      })
    });
    toast('Настройки сохранены');
    await loadBootstrap(state.ownerId);
  } catch (e) {
    toast(e.message);
  }
}

window.state = state;
window.openDraftEditor = openDraftEditor;
window.openGenerateDraftModal = openGenerateDraftModal;
window.openPlanGenerator = openPlanGenerator;
window.openPlanEditor = openPlanEditor;
window.openScheduleModal = openScheduleModal;
window.openChannelModal = openChannelModal;
window.createDraft = createDraft;
window.saveDraft = saveDraft;
window.generateDraft = generateDraft;
window.publishDraft = publishDraft;
window.deleteDraft = deleteDraft;
window.previewDraft = previewDraft;
window.activateChannel = activateChannel;
window.saveChannel = saveChannel;
window.generatePlan = generatePlan;
window.createPlanItem = createPlanItem;
window.savePlanItem = savePlanItem;
window.deletePlanItem = deletePlanItem;
window.createSchedule = createSchedule;
window.deleteSchedule = deleteSchedule;
window.saveSettings = saveSettings;
window.toggleAdvanced = toggleAdvanced;

loadBootstrap();
