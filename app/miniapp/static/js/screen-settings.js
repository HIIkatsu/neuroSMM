/**
 * NeuroSMM V2 — Settings Screen
 * Preserves important user-facing configuration from old product concept.
 */
const ScreenSettings = (() => {
  function render() {
    const el = document.getElementById('screen-settings');
    const user = Store.get('user');
    const prefs = Store.get('preferences');

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;gap:var(--space-md)">
          <button class="btn btn-ghost btn-sm" onclick="App.navigate(App.getPreviousScreen())">← Back</button>
          <div class="page-title" style="font-size:var(--font-size-xl)">Settings</div>
        </div>
      </div>

      ${user ? `
        <div class="card" style="display:flex;align-items:center;gap:var(--space-lg)">
          <div style="width:48px;height:48px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">
            ${Icons.user}
          </div>
          <div>
            <div style="font-weight:var(--font-weight-semibold)">${UI.esc(user.first_name)} ${UI.esc(user.last_name || '')}</div>
            <div style="font-size:var(--font-size-sm);color:var(--text-muted)">${user.username ? '@' + UI.esc(user.username) : 'No username'}</div>
          </div>
        </div>
      ` : ''}

      <div class="section-title">Content defaults</div>
      <div class="card">
        <div class="input-group" style="margin-bottom:var(--space-md)">
          <label class="input-label" for="pref-tone">Default tone</label>
          <select class="input" id="pref-tone" onchange="ScreenSettings.updatePref('defaultTone', this.value)">
            ${['neutral', 'formal', 'casual', 'humorous', 'promotional'].map(t =>
              `<option value="${t}" ${prefs.defaultTone === t ? 'selected' : ''}>${t}</option>`
            ).join('')}
          </select>
        </div>
        <div class="input-group" style="margin-bottom:0">
          <label class="input-label" for="pref-content-type">Default content type</label>
          <select class="input" id="pref-content-type" onchange="ScreenSettings.updatePref('defaultContentType', this.value)">
            ${['text', 'image', 'text_and_image'].map(t =>
              `<option value="${t}" ${prefs.defaultContentType === t ? 'selected' : ''}>${t.replace(/_/g, ' ')}</option>`
            ).join('')}
          </select>
        </div>
      </div>

      <div class="section-title">Formatting</div>
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Auto-format hashtags</div>
            <div class="toggle-desc">Add # prefix to hashtags automatically</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.formatHashtags ? 'checked' : ''} onchange="ScreenSettings.togglePref('formatHashtags', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Include emoji</div>
            <div class="toggle-desc">Allow AI to use emoji in generated text</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.formatEmoji ? 'checked' : ''} onchange="ScreenSettings.togglePref('formatEmoji', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Scheduling</div>
      <div class="card">
        <div class="input-group" style="margin-bottom:var(--space-md)">
          <label class="input-label" for="pref-sched-hour">Default schedule hour (UTC)</label>
          <select class="input" id="pref-sched-hour" onchange="ScreenSettings.updatePref('defaultScheduleHour', parseInt(this.value, 10))">
            ${Array.from({ length: 24 }, (_, i) =>
              `<option value="${i}" ${prefs.defaultScheduleHour === i ? 'selected' : ''}>${String(i).padStart(2, '0')}:00</option>`
            ).join('')}
          </select>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Schedule notifications</div>
            <div class="toggle-desc">Get notified when scheduled posts are published</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.notifyOnSchedule ? 'checked' : ''} onchange="ScreenSettings.togglePref('notifyOnSchedule', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">Editor</div>
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Auto-save drafts</div>
            <div class="toggle-desc">Automatically save changes while editing</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.autoSaveDrafts ? 'checked' : ''} onchange="ScreenSettings.togglePref('autoSaveDrafts', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-title">Compact view</div>
            <div class="toggle-desc">Show more items in draft lists</div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${prefs.compactView ? 'checked' : ''} onchange="ScreenSettings.togglePref('compactView', this.checked)" />
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <div class="section-title">System</div>
      <div class="card">
        <div class="list-item" style="padding:var(--space-sm) 0">
          <div class="list-item-content">
            <div class="list-item-title">Version</div>
            <div class="list-item-subtitle">NeuroSMM 2.0.0</div>
          </div>
        </div>
        <div class="list-item" style="padding:var(--space-sm) 0;border-top:1px solid var(--border-subtle)">
          <div class="list-item-content">
            <div class="list-item-title">Language</div>
            <div class="list-item-subtitle">${UI.esc(user?.language_code || 'en')}</div>
          </div>
        </div>
      </div>

      <div style="margin-top:var(--space-2xl)">
        <button class="btn btn-ghost btn-full btn-sm" onclick="ScreenSettings.resetOnboarding()">
          Restart onboarding
        </button>
      </div>
    `;
  }

  function updatePref(key, value) {
    Store.update('preferences', (p) => ({ ...p, [key]: value }));
    Store.savePreferences();
    UI.toast('Preference saved', 'success');
  }

  function togglePref(key, checked) {
    Store.update('preferences', (p) => ({ ...p, [key]: checked }));
    Store.savePreferences();
  }

  function resetOnboarding() {
    try { localStorage.removeItem('neurosmm_onboarded'); } catch { /* ignore */ }
    UI.toast('Onboarding will show on next launch', 'success');
  }

  return { render, updatePref, togglePref, resetOnboarding };
})();
