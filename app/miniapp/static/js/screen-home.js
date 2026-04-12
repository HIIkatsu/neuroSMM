/**
 * NeuroSMM V2 — Главный экран / Нейро
 * Дашборд с обзором и быстрыми действиями.
 */
const ScreenHome = (() => {
  const TONE_LABELS = { neutral: 'Нейтральный', formal: 'Формальный', casual: 'Разговорный', humorous: 'Юмористический', promotional: 'Рекламный' };

  function render() {
    const el = document.getElementById('screen-home');
    const user = Store.get('user');
    const project = Store.getActiveProject();
    const drafts = Store.get('drafts');
    const schedules = Store.get('schedules');
    const features = Store.get('features');

    const recentDrafts = drafts.slice(0, 3);
    const pendingSchedules = schedules.filter(s => s.status === 'pending');
    const firstName = user?.first_name || 'друг';

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div>
            <div class="page-title">Привет, ${UI.esc(firstName)} 👋</div>
            <div class="page-subtitle">Ваше ИИ-пространство для контента</div>
          </div>
          <button class="btn btn-ghost" onclick="App.navigate('settings')" aria-label="Настройки">
            ${Icons.settings}
          </button>
        </div>
      </div>

      ${project ? `
        <div class="hero-card">
          <div style="font-size:var(--font-size-sm);color:var(--text-secondary);margin-bottom:var(--space-sm)">Активный проект</div>
          <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-xs)">${UI.esc(project.title)}</div>
          ${project.platform_channel_id
            ? `<div style="font-size:var(--font-size-sm);color:var(--status-published)">● Канал подключён</div>`
            : `<div style="font-size:var(--font-size-sm);color:var(--status-draft)">○ Канал не привязан</div>`
          }
        </div>
      ` : `
        <div class="hero-card" style="text-align:center">
          <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-sm)">Начните работу</div>
          <div style="color:var(--text-secondary);margin-bottom:var(--space-lg)">Создайте первый проект, чтобы начать</div>
          <button class="btn btn-primary" onclick="ScreenHome.createProject()">Создать проект</button>
        </div>
      `}

      ${project ? `
        <div class="section-title">Быстрые действия</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-md)">
          <button class="card card-interactive" onclick="App.navigate('create')" style="text-align:center;cursor:pointer">
            <div style="color:var(--accent-light);margin-bottom:var(--space-sm)">${Icons.sparkle}</div>
            <div style="font-weight:var(--font-weight-semibold)">Новый черновик</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">С помощью ИИ</div>
          </button>
          <button class="card card-interactive" onclick="App.navigate('plan')" style="text-align:center;cursor:pointer">
            <div style="color:var(--accent-light);margin-bottom:var(--space-sm)">${Icons.plan}</div>
            <div style="font-weight:var(--font-weight-semibold)">Расписание</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">${pendingSchedules.length} ожидает</div>
          </button>
        </div>
      ` : ''}

      ${features ? `
        <div class="section-title">ИИ-функции</div>
        <div class="card">
          <div class="toggle-row">
            <div class="toggle-info">
              <div class="toggle-title">Генерация текста</div>
              <div class="toggle-desc">${features.text_generation ? 'Доступна' : 'Не настроена'}</div>
            </div>
            <span class="badge ${features.text_generation ? 'badge-published' : 'badge-cancelled'}">${features.text_generation ? 'ВКЛ' : 'ВЫКЛ'}</span>
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <div class="toggle-title">Генерация изображений</div>
              <div class="toggle-desc">${features.image_generation ? 'Доступна' : 'Не настроена'}</div>
            </div>
            <span class="badge ${features.image_generation ? 'badge-published' : 'badge-cancelled'}">${features.image_generation ? 'ВКЛ' : 'ВЫКЛ'}</span>
          </div>
        </div>
      ` : ''}

      ${recentDrafts.length > 0 ? `
        <div class="section-title">Последние черновики</div>
        <div class="card" style="padding:var(--space-sm)">
          ${recentDrafts.map(d => `
            <div class="list-item card-interactive" onclick="ScreenCreate.openDraft(${d.id})" style="cursor:pointer">
              <div class="list-item-icon">${Icons.create}</div>
              <div class="list-item-content">
                <div class="list-item-title">${UI.esc(d.title || 'Без названия')}</div>
                <div class="list-item-subtitle">${UI.formatDate(d.updated_at)}</div>
              </div>
              ${UI.statusBadge(d.status)}
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;
  }

  async function createProject() {
    const html = `
      <div class="input-group">
        <label class="input-label" for="new-project-title">Название проекта</label>
        <input class="input" id="new-project-title" placeholder="Например: Мой Tech-канал" required />
      </div>
      <div class="input-group">
        <label class="input-label" for="new-project-desc">Описание (необязательно)</label>
        <textarea class="input" id="new-project-desc" placeholder="О чём этот канал?"></textarea>
      </div>
      <button class="btn btn-primary btn-full" id="create-project-btn">Создать проект</button>
    `;
    const modal = UI.showModal(html, 'Новый проект');
    modal.querySelector('#create-project-btn').addEventListener('click', async function() {
      const title = modal.querySelector('#new-project-title').value.trim();
      if (!title) { UI.toast('Введите название проекта', 'error'); return; }
      await UI.withButtonLoading(this, async () => {
        try {
          const p = await API.createProject({
            title,
            description: modal.querySelector('#new-project-desc').value.trim(),
          });
          Store.update('projects', (ps) => [...ps, p]);
          Store.setActiveProject(p.id);
          UI.closeModal();
          UI.toast('Проект создан!', 'success');
          await App.loadProjectData();
          render();
        } catch (e) {
          UI.toast(e.message, 'error');
        }
      }, 'Создание…');
    });
  }

  return { render, createProject };
})();
