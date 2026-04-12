/**
 * NeuroSMM V2 Mini App — Main Application Controller
 * Orchestrates navigation, bootstrap, and screen rendering.
 */
const App = (() => {
  const SCREENS = ['home', 'create', 'plan', 'stats', 'channel'];
  let _currentScreen = 'home';
  let _previousScreen = 'home';

  async function init() {
    // Telegram WebApp SDK
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
      window.Telegram.WebApp.setHeaderColor('#0d0f1a');
      window.Telegram.WebApp.setBackgroundColor('#0d0f1a');
    }

    // Load saved preferences
    Store.loadPreferences();

    // Render nav
    _renderNav();

    // Bootstrap
    try {
      const bootstrap = await API.getMe();
      Store.set('user', bootstrap.user);
      Store.set('features', bootstrap.features);

      // Load projects
      const projectsResult = await API.listProjects();
      Store.set('projects', projectsResult.items || []);

      // Restore active project
      const savedPid = Store.get('activeProjectId');
      if (savedPid && Store.get('projects').find(p => p.id === savedPid)) {
        // already set
      } else if (Store.get('projects').length > 0) {
        Store.setActiveProject(Store.get('projects')[0].id);
      }

      // Load project-specific data
      await loadProjectData();

      // Show onboarding if needed
      if (!Store.get('onboardingComplete')) {
        await Onboarding.show();
        // Reload after onboarding in case project was created
        const projectsAfter = await API.listProjects();
        Store.set('projects', projectsAfter.items || []);
        if (Store.get('projects').length > 0 && !Store.get('activeProjectId')) {
          Store.setActiveProject(Store.get('projects')[0].id);
        }
        await loadProjectData();
      }

      // Render initial screen
      navigate('home');
    } catch (e) {
      console.error('Bootstrap failed:', e);
      _showError(e.message);
    }
  }

  async function loadProjectData() {
    const project = Store.getActiveProject();
    if (!project) {
      Store.set('drafts', []);
      Store.set('schedules', []);
      Store.set('channelStatus', null);
      return;
    }

    try {
      const [draftsResult, schedulesResult] = await Promise.all([
        API.listDrafts(project.id),
        API.listSchedules(project.id),
      ]);
      Store.set('drafts', draftsResult.items || []);
      Store.set('schedules', schedulesResult.items || []);
    } catch (e) {
      console.error('Failed to load project data:', e);
      Store.set('drafts', []);
      Store.set('schedules', []);
    }

    // Channel status (non-blocking)
    try {
      const status = await API.channelStatus(project.id);
      Store.set('channelStatus', status);
    } catch {
      Store.set('channelStatus', { project_id: project.id, is_bound: false, channel_id: null });
    }
  }

  function navigate(screen) {
    if (screen === 'settings') {
      // Settings is not in bottom nav — special handling
      _previousScreen = _currentScreen;
      _currentScreen = 'settings';
      _renderScreen();
      return;
    }

    if (!SCREENS.includes(screen)) return;
    _previousScreen = _currentScreen;
    _currentScreen = screen;
    _renderScreen();
    _updateNav();
  }

  function getPreviousScreen() {
    return _previousScreen || 'home';
  }

  function _renderScreen() {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));

    // Settings screen
    if (_currentScreen === 'settings') {
      const settingsEl = document.getElementById('screen-settings');
      settingsEl.classList.add('active');
      ScreenSettings.render();
      return;
    }

    const el = document.getElementById(`screen-${_currentScreen}`);
    if (el) {
      el.classList.add('active');
    }

    // Render screen content
    const renderers = {
      home: ScreenHome,
      create: ScreenCreate,
      plan: ScreenPlan,
      stats: ScreenStats,
      channel: ScreenChannel,
    };

    const renderer = renderers[_currentScreen];
    if (renderer) renderer.render();
  }

  function _renderNav() {
    const nav = document.getElementById('bottom-nav');
    const items = [
      { id: 'home', label: 'Нейро', icon: Icons.neuro },
      { id: 'create', label: 'Создать', icon: Icons.create },
      { id: 'plan', label: 'План', icon: Icons.plan },
      { id: 'stats', label: 'Статистика', icon: Icons.stats },
      { id: 'channel', label: 'Канал', icon: Icons.channel },
    ];

    nav.innerHTML = items.map(item => `
      <button class="nav-item ${_currentScreen === item.id ? 'active' : ''}"
              onclick="App.navigate('${item.id}')"
              aria-label="${item.label}"
              data-nav="${item.id}">
        <span class="nav-icon">${item.icon}</span>
        <span>${item.label}</span>
      </button>
    `).join('');
  }

  function _updateNav() {
    document.querySelectorAll('.nav-item').forEach(el => {
      const id = el.dataset.nav;
      if (id === _currentScreen) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });
  }

  function _showError(message) {
    const content = document.querySelector('.app-content');
    content.innerHTML = `
      <div class="empty-state" style="padding-top:20vh">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Ошибка подключения</div>
        <div class="empty-state-desc">${UI.esc(message)}</div>
        <button class="btn btn-primary" onclick="location.reload()">Повторить</button>
      </div>
    `;
  }

  return { init, navigate, loadProjectData, getPreviousScreen };
})();

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
