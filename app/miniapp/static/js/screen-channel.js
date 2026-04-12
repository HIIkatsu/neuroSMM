/**
 * NeuroSMM V2 — Channel Screen
 * Screenshot-faithful: channel status hero card + settings + operational controls.
 */
const ScreenChannel = (() => {
  function render() {
    const el = document.getElementById('screen-channel');
    const project = Store.getActiveProject();

    if (!project) {
      el.innerHTML = `
        <div class="page-header"><div class="page-title">Канал</div></div>
        <div class="empty-state">
          <div class="empty-state-icon">📡</div>
          <div class="empty-state-title">Нет проекта</div>
          <div class="empty-state-desc">Сначала создайте проект для управления каналом</div>
        </div>`;
      return;
    }

    const channelStatus = Store.get('channelStatus');
    const isBound = channelStatus?.is_bound || false;

    el.innerHTML = `
      <div class="page-header">
        <div class="page-title">Канал</div>
        <div class="page-subtitle">${UI.esc(project.title)}</div>
      </div>

      ${isBound ? _renderConnectedChannel(channelStatus, project) : _renderUnconnectedChannel(project)}

      <div class="section-title">Настройки канала</div>
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Авто-публикация</div>
            <div class="toggle-desc">Автоматически публиковать запланированные посты</div>
          </div>
          <label class="toggle">
            <input type="checkbox" checked disabled />
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Уведомления</div>
            <div class="toggle-desc">Получать уведомления об успехе/ошибке публикации</div>
          </div>
          <label class="toggle">
            <input type="checkbox" id="ch-notify" ${Store.get('preferences').notifyOnPublish ? 'checked' : ''} onchange="ScreenChannel.toggleNotify(this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Информация о проекте</div>
      <div class="card">
        <div class="list-item" style="padding:var(--space-sm) 0">
          <div class="list-item-content">
            <div class="list-item-title">Название проекта</div>
            <div class="list-item-subtitle">${UI.esc(project.title)}</div>
          </div>
          <button class="btn btn-ghost btn-sm" onclick="ScreenChannel.editProject()">Edit</button>
        </div>
        <div class="list-item" style="padding:var(--space-sm) 0;border-top:1px solid var(--border-subtle)">
          <div class="list-item-content">
            <div class="list-item-title">Платформа</div>
            <div class="list-item-subtitle">${UI.esc(project.platform)}</div>
          </div>
        </div>
        <div class="list-item" style="padding:var(--space-sm) 0;border-top:1px solid var(--border-subtle)">
          <div class="list-item-content">
            <div class="list-item-title">Создан</div>
            <div class="list-item-subtitle">${UI.formatDate(project.created_at)}</div>
          </div>
        </div>
        <div class="list-item" style="padding:var(--space-sm) 0;border-top:1px solid var(--border-subtle)">
          <div class="list-item-content">
            <div class="list-item-title">Статус</div>
            <div class="list-item-subtitle">${project.is_active ? 'Активен' : 'Деактивирован'}</div>
          </div>
        </div>
      </div>

      ${Store.get('projects').length > 1 ? `
        <div class="section-title">Сменить проект</div>
        <div class="card" style="padding:var(--space-sm)">
          ${Store.get('projects').filter(p => p.is_active).map(p => `
            <div class="list-item card-interactive" onclick="ScreenChannel.switchProject(${p.id})" style="cursor:pointer">
              <div class="list-item-icon" style="${p.id === project.id ? 'background:var(--accent);color:white' : ''}">${Icons.channel}</div>
              <div class="list-item-content">
                <div class="list-item-title">${UI.esc(p.title)}</div>
                <div class="list-item-subtitle">${p.platform_channel_id ? 'Подключён' : 'Нет канала'}</div>
              </div>
              ${p.id === project.id ? `<span style="color:var(--accent-light)">${Icons.check}</span>` : ''}
            </div>
          `).join('')}
        </div>
      ` : ''}

      <div style="margin-top:var(--space-2xl)">
        ${project.is_active
          ? `<button class="btn btn-danger btn-full btn-sm" onclick="ScreenChannel.deactivateProject()">Деактивировать проект</button>`
          : `<button class="btn btn-primary btn-full btn-sm" onclick="ScreenChannel.activateProject()">Активировать проект</button>`
        }
      </div>
    `;
  }

  function _renderConnectedChannel(channelStatus, project) {
    return `
      <div class="hero-card">
        <div style="display:flex;align-items:center;gap:var(--space-lg);margin-bottom:var(--space-lg)">
          <div style="width:48px;height:48px;border-radius:var(--radius-lg);background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">📡</div>
          <div>
            <div style="font-size:var(--font-size-lg);font-weight:var(--font-weight-bold)">Канал подключён</div>
            <div style="font-size:var(--font-size-sm);color:var(--text-secondary)">ID: ${UI.esc(channelStatus.channel_id || project.platform_channel_id || '—')}</div>
          </div>
        </div>
        <div style="display:flex;gap:var(--space-md)">
          <button class="btn btn-secondary btn-sm btn-full" onclick="ScreenChannel.refreshStatus()">
            ${Icons.refresh} Обновить
          </button>
          <button class="btn btn-ghost btn-sm btn-full" onclick="ScreenChannel.rebindChannel()">
            ${Icons.link} Перепривязать
          </button>
        </div>
      </div>
    `;
  }

  function _renderUnconnectedChannel(project) {
    return `
      <div class="hero-card" style="text-align:center">
        <div style="font-size:48px;margin-bottom:var(--space-lg)">📡</div>
        <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-sm)">Подключите канал</div>
        <div style="color:var(--text-secondary);margin-bottom:var(--space-xl)">Привяжите Telegram-канал для публикации контента</div>
        <button class="btn btn-primary btn-full" onclick="ScreenChannel.bindChannel()">
          ${Icons.link} Подключить канал
        </button>
      </div>
    `;
  }

  function bindChannel() {
    const project = Store.getActiveProject();
    if (!project) return;

    const html = `
      <div class="input-group">
        <label class="input-label" for="bind-channel-id">Юзернейм или ID канала</label>
        <input class="input" id="bind-channel-id" placeholder="@mychannel или -100123456" />
      </div>
      <div style="font-size:var(--font-size-xs);color:var(--text-muted);margin-bottom:var(--space-lg)">
        Убедитесь, что бот добавлен как администратор канала с правом публикации.
      </div>
      <button class="btn btn-primary btn-full" id="confirm-bind-btn">Подключить</button>
    `;
    const modal = UI.showModal(html, 'Подключить канал');
    modal.querySelector('#confirm-bind-btn').addEventListener('click', async function() {
      const id = modal.querySelector('#bind-channel-id').value.trim();
      if (!id) { UI.toast('Введите идентификатор канала', 'error'); return; }
      await UI.withButtonLoading(this, async () => {
        try {
          await API.bindChannel(project.id, { channel_identifier: id });
          UI.closeModal();
          UI.toast('Канал подключён!', 'success');
          await _refreshChannelStatus();
          render();
        } catch (e) { UI.toast(e.message, 'error'); }
      }, 'Подключение…');
    });
  }

  function rebindChannel() {
    bindChannel();
  }

  async function refreshStatus() {
    const btn = document.querySelector('[onclick="ScreenChannel.refreshStatus()"]');
    if (btn) {
      await UI.withButtonLoading(btn, async () => {
        await _refreshChannelStatus();
        render();
        UI.toast('Статус обновлён', 'success');
      }, `${Icons.refresh} Обновление…`);
    } else {
      await _refreshChannelStatus();
      render();
      UI.toast('Статус обновлён', 'success');
    }
  }

  async function _refreshChannelStatus() {
    const project = Store.getActiveProject();
    if (!project) return;
    try {
      const status = await API.channelStatus(project.id);
      Store.set('channelStatus', status);
    } catch {
      Store.set('channelStatus', { project_id: project.id, is_bound: false, channel_id: null });
    }
  }

  function editProject() {
    const project = Store.getActiveProject();
    if (!project) return;

    const html = `
      <div class="input-group">
        <label class="input-label" for="edit-proj-title">Название проекта</label>
        <input class="input" id="edit-proj-title" value="${UI.esc(project.title)}" />
      </div>
      <div class="input-group">
        <label class="input-label" for="edit-proj-desc">Описание</label>
        <textarea class="input" id="edit-proj-desc">${UI.esc(project.description)}</textarea>
      </div>
      <button class="btn btn-primary btn-full" id="save-proj-btn">Сохранить</button>
    `;
    const modal = UI.showModal(html, 'Редактировать проект');
    modal.querySelector('#save-proj-btn').addEventListener('click', async function() {
      const title = modal.querySelector('#edit-proj-title').value.trim();
      const desc = modal.querySelector('#edit-proj-desc').value.trim();
      if (!title) { UI.toast('Название обязательно', 'error'); return; }
      await UI.withButtonLoading(this, async () => {
        try {
          const updated = await API.updateProject(project.id, { title, description: desc });
          Store.update('projects', (ps) => ps.map(p => p.id === updated.id ? updated : p));
          UI.closeModal();
          UI.toast('Проект обновлён', 'success');
          render();
        } catch (e) { UI.toast(e.message, 'error'); }
      }, 'Сохранение…');
    });
  }

  async function switchProject(pid) {
    Store.setActiveProject(pid);
    await App.loadProjectData();
    render();
    UI.toast('Проект переключён', 'success');
  }

  async function deactivateProject() {
    const project = Store.getActiveProject();
    if (!project) return;
    const confirmed = await UI.confirm(
      `Деактивировать "${project.title}"? Можно будет активировать позже.`,
      'Деактивировать'
    );
    if (!confirmed) return;
    try {
      const updated = await API.deactivateProject(project.id);
      Store.update('projects', (ps) => ps.map(p => p.id === updated.id ? updated : p));
      // Switch to another active project if available
      const activeProjects = Store.get('projects').filter(p => p.is_active && p.id !== updated.id);
      if (activeProjects.length > 0) {
        Store.setActiveProject(activeProjects[0].id);
        await App.loadProjectData();
      }
      render();
      UI.toast('Проект деактивирован', 'success');
    } catch (e) { UI.toast(e.message, 'error'); }
  }

  async function activateProject() {
    const project = Store.getActiveProject();
    if (!project) return;
    try {
      const updated = await API.activateProject(project.id);
      Store.update('projects', (ps) => ps.map(p => p.id === updated.id ? updated : p));
      render();
      UI.toast('Проект активирован', 'success');
    } catch (e) { UI.toast(e.message, 'error'); }
  }

  function toggleNotify(checked) {
    Store.update('preferences', (p) => ({ ...p, notifyOnPublish: checked }));
    Store.savePreferences();
  }

  return {
    render, bindChannel, rebindChannel, refreshStatus,
    editProject, switchProject, deactivateProject, activateProject,
    toggleNotify,
  };
})();
