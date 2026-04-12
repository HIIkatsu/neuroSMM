/**
 * NeuroSMM V2 — Home / Neuro Screen
 * Dashboard overview with quick actions.
 */
const ScreenHome = (() => {
  function render() {
    const el = document.getElementById('screen-home');
    const user = Store.get('user');
    const project = Store.getActiveProject();
    const drafts = Store.get('drafts');
    const schedules = Store.get('schedules');
    const features = Store.get('features');

    const recentDrafts = drafts.slice(0, 3);
    const pendingSchedules = schedules.filter(s => s.status === 'pending');
    const firstName = user?.first_name || 'there';

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div>
            <div class="page-title">Hi, ${UI.esc(firstName)} 👋</div>
            <div class="page-subtitle">Your AI content workspace</div>
          </div>
          <button class="btn btn-ghost" onclick="App.navigate('settings')" aria-label="Settings">
            ${Icons.settings}
          </button>
        </div>
      </div>

      ${project ? `
        <div class="hero-card">
          <div style="font-size:var(--font-size-sm);color:var(--text-secondary);margin-bottom:var(--space-sm)">Active project</div>
          <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-xs)">${UI.esc(project.title)}</div>
          ${project.platform_channel_id
            ? `<div style="font-size:var(--font-size-sm);color:var(--status-published)">● Channel connected</div>`
            : `<div style="font-size:var(--font-size-sm);color:var(--status-draft)">○ No channel linked</div>`
          }
        </div>
      ` : `
        <div class="hero-card" style="text-align:center">
          <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-sm)">Get started</div>
          <div style="color:var(--text-secondary);margin-bottom:var(--space-lg)">Create your first project to begin</div>
          <button class="btn btn-primary" onclick="ScreenHome.createProject()">Create project</button>
        </div>
      `}

      ${project ? `
        <div class="section-title">Quick actions</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-md)">
          <button class="card card-interactive" onclick="App.navigate('create')" style="text-align:center;cursor:pointer">
            <div style="color:var(--accent-light);margin-bottom:var(--space-sm)">${Icons.sparkle}</div>
            <div style="font-weight:var(--font-weight-semibold)">New draft</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">AI-powered</div>
          </button>
          <button class="card card-interactive" onclick="App.navigate('plan')" style="text-align:center;cursor:pointer">
            <div style="color:var(--accent-light);margin-bottom:var(--space-sm)">${Icons.plan}</div>
            <div style="font-weight:var(--font-weight-semibold)">Schedule</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">${pendingSchedules.length} pending</div>
          </button>
        </div>
      ` : ''}

      ${features ? `
        <div class="section-title">AI Features</div>
        <div class="card">
          <div class="toggle-row">
            <div class="toggle-info">
              <div class="toggle-title">Text generation</div>
              <div class="toggle-desc">${features.text_generation ? 'Available' : 'Not configured'}</div>
            </div>
            <span class="badge ${features.text_generation ? 'badge-published' : 'badge-cancelled'}">${features.text_generation ? 'ON' : 'OFF'}</span>
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <div class="toggle-title">Image generation</div>
              <div class="toggle-desc">${features.image_generation ? 'Available' : 'Not configured'}</div>
            </div>
            <span class="badge ${features.image_generation ? 'badge-published' : 'badge-cancelled'}">${features.image_generation ? 'ON' : 'OFF'}</span>
          </div>
        </div>
      ` : ''}

      ${recentDrafts.length > 0 ? `
        <div class="section-title">Recent drafts</div>
        <div class="card" style="padding:var(--space-sm)">
          ${recentDrafts.map(d => `
            <div class="list-item card-interactive" onclick="ScreenCreate.openDraft(${d.id})" style="cursor:pointer">
              <div class="list-item-icon">${Icons.create}</div>
              <div class="list-item-content">
                <div class="list-item-title">${UI.esc(d.title || 'Untitled draft')}</div>
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
        <label class="input-label" for="new-project-title">Project name</label>
        <input class="input" id="new-project-title" placeholder="e.g. My Tech Channel" required />
      </div>
      <div class="input-group">
        <label class="input-label" for="new-project-desc">Description (optional)</label>
        <textarea class="input" id="new-project-desc" placeholder="What is this channel about?"></textarea>
      </div>
      <button class="btn btn-primary btn-full" id="create-project-btn">Create project</button>
    `;
    const modal = UI.showModal(html, 'New project');
    modal.querySelector('#create-project-btn').addEventListener('click', async () => {
      const title = modal.querySelector('#new-project-title').value.trim();
      if (!title) { UI.toast('Enter a project name', 'error'); return; }
      try {
        const p = await API.createProject({
          title,
          description: modal.querySelector('#new-project-desc').value.trim(),
        });
        Store.update('projects', (ps) => [...ps, p]);
        Store.setActiveProject(p.id);
        UI.closeModal();
        UI.toast('Project created!', 'success');
        await App.loadProjectData();
        render();
      } catch (e) {
        UI.toast(e.message, 'error');
      }
    });
  }

  return { render, createProject };
})();
