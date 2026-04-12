/**
 * NeuroSMM V2 — Settings Screen
 * Preserves important user-facing configuration from old product concept.
 */
const ScreenSettings = (() => {
  const _toneLabels = { neutral: 'нейтральный', formal: 'формальный', casual: 'разговорный', humorous: 'юмористический', promotional: 'рекламный' };
  const _contentTypeLabels = { text: 'текст', image: 'изображение', text_and_image: 'текст + изображение' };

  function render() {
    const el = document.getElementById('screen-settings');
    const user = Store.get('user');
    const prefs = Store.get('preferences');

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;gap:var(--space-md)">
          <button class="btn btn-ghost btn-sm" onclick="App.navigate(App.getPreviousScreen())">← Назад</button>
          <div class="page-title" style="font-size:var(--font-size-xl)">Настройки</div>
        </div>
      </div>

      ${user ? `
        <div class="card" style="display:flex;align-items:center;gap:var(--space-lg)">
          <div style="width:48px;height:48px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">
            ${Icons.user}
          </div>
          <div>
            <div style="font-weight:var(--font-weight-semibold)">${UI.esc(user.first_name)} ${UI.esc(user.last_name || '')}</div>
            <div style="font-size:var(--font-size-sm);color:var(--text-muted)">${user.username ? '@' + UI.esc(user.username) : 'Нет юзернейма'}</div>
          </div>
        </div>
      ` : ''}

      <div class="section-title">Контент по умолчанию</div>
      <div class="card">
        <div class="input-group" style="margin-bottom:var(--space-md)">
          <label class="input-label" for="pref-tone">Тон по умолчанию</label>
          <select class="input" id="pref-tone" onchange="ScreenSettings.updatePref('defaultTone', this.value)">
            ${['neutral', 'formal', 'casual', 'humorous', 'promotional'].map(t =>
              `<option value="${t}" ${prefs.defaultTone === t ? 'selected' : ''}>${_toneLabels[t]}</option>`
            ).join('')}
          </select>
        </div>
        <div class="input-group" style="margin-bottom:0">
          <label class="input-label" for="pref-content-type">Тип контента</label>
          <select class="input" id="pref-content-type" onchange="ScreenSettings.updatePref('defaultContentType', this.value)">
            ${['text', 'image', 'text_and_image'].map(t =>
              `<option value="${t}" ${prefs.defaultContentType === t ? 'selected' : ''}>${_contentTypeLabels[t]}</option>`
            ).join('')}
          </select>
        </div>
      </div>

      <div class="section-title">Форматирование</div>
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Авто-формат хэштегов</div>
            <div class="toggle-desc">Автоматически добавлять # к хэштегам</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.formatHashtags ? 'checked' : ''} onchange="ScreenSettings.togglePref('formatHashtags', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Использовать эмодзи</div>
            <div class="toggle-desc">Разрешить ИИ использовать эмодзи в тексте</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.formatEmoji ? 'checked' : ''} onchange="ScreenSettings.togglePref('formatEmoji', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Расписание</div>
      <div class="card">
        <div class="input-group" style="margin-bottom:var(--space-md)">
          <label class="input-label" for="pref-sched-hour">Час публикации по умолчанию (UTC)</label>
          <select class="input" id="pref-sched-hour" onchange="ScreenSettings.updatePref('defaultScheduleHour', parseInt(this.value, 10))">
            ${Array.from({ length: 24 }, (_, i) =>
              `<option value="${i}" ${prefs.defaultScheduleHour === i ? 'selected' : ''}>${String(i).padStart(2, '0')}:00</option>`
            ).join('')}
          </select>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Уведомления о расписании</div>
            <div class="toggle-desc">Уведомлять при публикации запланированных постов</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.notifyOnSchedule ? 'checked' : ''} onchange="ScreenSettings.togglePref('notifyOnSchedule', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Редактор</div>
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Авто-сохранение</div>
            <div class="toggle-desc">Автоматически сохранять изменения при редактировании</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.autoSaveDrafts ? 'checked' : ''} onchange="ScreenSettings.togglePref('autoSaveDrafts', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Компактный вид</div>
            <div class="toggle-desc">Показывать больше элементов в списке</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.compactView ? 'checked' : ''} onchange="ScreenSettings.togglePref('compactView', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Система</div>
      <div class="card">
        <div class="list-item" style="padding:var(--space-sm) 0">
          <div class="list-item-content">
            <div class="list-item-title">Версия</div>
            <div class="list-item-subtitle">NeuroSMM 2.0.0</div>
          </div>
        </div>
        <div class="list-item" style="padding:var(--space-sm) 0;border-top:1px solid var(--border-subtle)">
          <div class="list-item-content">
            <div class="list-item-title">Язык</div>
            <div class="list-item-subtitle">${UI.esc(user?.language_code || 'en')}</div>
          </div>
        </div>
      </div>

      <div style="margin-top:var(--space-2xl)">
        <button class="btn btn-ghost btn-full btn-sm" onclick="ScreenSettings.resetOnboarding()">
          Пройти онбординг заново
        </button>
      </div>
    `;
  }

  function updatePref(key, value) {
    Store.update('preferences', (p) => ({ ...p, [key]: value }));
    Store.savePreferences();
    UI.toast('Настройка сохранена', 'success');
  }

  function togglePref(key, checked) {
    Store.update('preferences', (p) => ({ ...p, [key]: checked }));
    Store.savePreferences();
  }

  function resetOnboarding() {
    try { localStorage.removeItem('neurosmm_onboarded'); } catch { /* ignore */ }
    UI.toast('Онбординг появится при следующем запуске', 'success');
  }

  return { render, updatePref, togglePref, resetOnboarding };
})();
