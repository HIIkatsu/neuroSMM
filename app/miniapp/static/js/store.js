/**
 * NeuroSMM V2 Mini App — Global State Store
 * Simple reactive state management.
 */
const Store = (() => {
  const _state = {
    user: null,
    features: null,
    projects: [],
    activeProjectId: null,
    drafts: [],
    schedules: [],
    channelStatus: null,
    onboardingComplete: false,
    preferences: {
      defaultTone: 'neutral',
      defaultContentType: 'text',
      autoSaveDrafts: true,
      notifyOnPublish: true,
      notifyOnSchedule: true,
      compactView: false,
      defaultScheduleHour: 10,
      formatHashtags: true,
      formatEmoji: true,
    },
    loading: {},
  };

  const _listeners = new Map();

  function get(key) {
    return key ? _state[key] : { ..._state };
  }

  function set(key, value) {
    _state[key] = value;
    _notify(key);
  }

  function update(key, fn) {
    _state[key] = fn(_state[key]);
    _notify(key);
  }

  function on(key, cb) {
    if (!_listeners.has(key)) _listeners.set(key, new Set());
    _listeners.get(key).add(cb);
    return () => _listeners.get(key).delete(cb);
  }

  function _notify(key) {
    const listeners = _listeners.get(key);
    if (listeners) listeners.forEach(cb => cb(_state[key]));
  }

  // Persistence
  function loadPreferences() {
    try {
      const saved = localStorage.getItem('neurosmm_prefs');
      if (saved) {
        Object.assign(_state.preferences, JSON.parse(saved));
      }
      _state.onboardingComplete = localStorage.getItem('neurosmm_onboarded') === '1';
      _state.activeProjectId = parseInt(localStorage.getItem('neurosmm_active_project') || '0', 10) || null;
    } catch { /* ignore */ }
  }

  function savePreferences() {
    try {
      localStorage.setItem('neurosmm_prefs', JSON.stringify(_state.preferences));
    } catch { /* ignore */ }
  }

  function setOnboardingComplete() {
    _state.onboardingComplete = true;
    try { localStorage.setItem('neurosmm_onboarded', '1'); } catch { /* ignore */ }
  }

  function setActiveProject(pid) {
    _state.activeProjectId = pid;
    try { localStorage.setItem('neurosmm_active_project', String(pid)); } catch { /* ignore */ }
    _notify('activeProjectId');
  }

  function getActiveProject() {
    if (!_state.activeProjectId) return _state.projects[0] || null;
    return _state.projects.find(p => p.id === _state.activeProjectId) || _state.projects[0] || null;
  }

  return {
    get, set, update, on,
    loadPreferences, savePreferences,
    setOnboardingComplete, setActiveProject, getActiveProject,
  };
})();
