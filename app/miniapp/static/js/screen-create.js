/**
 * NeuroSMM V2 — Create Screen
 * Draft creation, editing, AI generation, preview & publish.
 */
const ScreenCreate = (() => {
  let _currentDraftId = null;
  let _mode = 'list'; // 'list' | 'edit'

  function render() {
    if (_mode === 'edit' && _currentDraftId) {
      _renderEditor();
    } else {
      _renderList();
    }
  }

  function _renderList() {
    const el = document.getElementById('screen-create');
    const project = Store.getActiveProject();
    const drafts = Store.get('drafts');

    if (!project) {
      el.innerHTML = `
        <div class="page-header"><div class="page-title">Create</div></div>
        <div class="empty-state">
          <div class="empty-state-icon">📝</div>
          <div class="empty-state-title">No project yet</div>
          <div class="empty-state-desc">Create a project on the Home screen first</div>
        </div>`;
      return;
    }

    const activeDrafts = drafts.filter(d => d.status !== 'archived');

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div class="page-title">Create</div>
          <button class="btn btn-primary btn-sm" onclick="ScreenCreate.newDraft()">
            ${Icons.plus} New
          </button>
        </div>
        <div class="page-subtitle">${activeDrafts.length} draft${activeDrafts.length !== 1 ? 's' : ''}</div>
      </div>

      ${activeDrafts.length === 0 ? `
        <div class="empty-state">
          <div class="empty-state-icon">✨</div>
          <div class="empty-state-title">No drafts yet</div>
          <div class="empty-state-desc">Create your first AI-powered draft</div>
          <button class="btn btn-primary" onclick="ScreenCreate.newDraft()">Create draft</button>
        </div>
      ` : `
        <div style="display:flex;flex-direction:column;gap:var(--space-md)">
          ${activeDrafts.map(d => `
            <div class="card card-interactive" onclick="ScreenCreate.openDraft(${d.id})" style="cursor:pointer">
              <div class="card-header">
                <div class="card-title">${UI.esc(d.title || 'Untitled draft')}</div>
                ${UI.statusBadge(d.status)}
              </div>
              <div style="font-size:var(--font-size-sm);color:var(--text-secondary);margin-bottom:var(--space-sm)">
                ${d.text_content ? UI.esc(d.text_content.substring(0, 80)) + (d.text_content.length > 80 ? '…' : '') : 'No content yet'}
              </div>
              <div style="display:flex;gap:var(--space-md);font-size:var(--font-size-xs);color:var(--text-muted)">
                <span>${d.tone}</span>
                <span>${d.content_type.replace(/_/g, ' ')}</span>
                <span>${UI.formatDate(d.updated_at)}</span>
              </div>
            </div>
          `).join('')}
        </div>
      `}
    `;
  }

  async function _renderEditor() {
    const el = document.getElementById('screen-create');
    const project = Store.getActiveProject();
    const drafts = Store.get('drafts');
    const draft = drafts.find(d => d.id === _currentDraftId);
    const features = Store.get('features');

    if (!draft) {
      _mode = 'list';
      _renderList();
      return;
    }

    const isEditable = draft.status === 'draft';
    const isReady = draft.status === 'ready';
    const prefs = Store.get('preferences');

    el.innerHTML = `
      <div class="page-header">
        <div style="display:flex;align-items:center;gap:var(--space-md)">
          <button class="btn btn-ghost btn-sm" onclick="ScreenCreate.backToList()">← Back</button>
          <div style="flex:1">
            <div class="page-title" style="font-size:var(--font-size-xl)">${UI.esc(draft.title || 'Untitled')}</div>
            <div style="display:flex;gap:var(--space-sm);align-items:center;margin-top:var(--space-xs)">
              ${UI.statusBadge(draft.status)}
              <span style="font-size:var(--font-size-xs);color:var(--text-muted)">${UI.formatDateTime(draft.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>

      ${isEditable ? `
        <div class="card">
          <div class="input-group">
            <label class="input-label" for="draft-title">Title</label>
            <input class="input" id="draft-title" value="${UI.esc(draft.title)}" placeholder="Post title" />
          </div>
          <div class="input-group">
            <label class="input-label" for="draft-topic">Topic / hint for AI</label>
            <input class="input" id="draft-topic" value="${UI.esc(draft.topic)}" placeholder="e.g. AI productivity tools" />
          </div>
          <div class="input-group">
            <label class="input-label" for="draft-text">Content</label>
            <textarea class="input" id="draft-text" rows="6" placeholder="Write or generate with AI…">${UI.esc(draft.text_content)}</textarea>
          </div>
          <div style="display:flex;gap:var(--space-md)">
            <button class="btn btn-secondary btn-sm btn-full" id="save-draft-btn">Save</button>
          </div>
        </div>

        <div class="section-title">AI Generation</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-md)">
          <button class="btn btn-primary btn-sm btn-full" id="gen-text-btn" ${!features?.text_generation ? 'disabled title="Not configured"' : ''}>
            ${Icons.sparkle} Text
          </button>
          <button class="btn btn-secondary btn-sm btn-full" id="gen-image-btn" ${!features?.image_generation ? 'disabled title="Not configured"' : ''}>
            ${Icons.image} Image
          </button>
        </div>

        ${draft.image_url ? `
          <div class="section-title">Generated image</div>
          <div class="card" style="padding:var(--space-sm)">
            <img src="${UI.esc(draft.image_url)}" alt="Generated" style="width:100%;border-radius:var(--radius-md)" />
          </div>
        ` : ''}

        <div class="section-title">Actions</div>
        <div style="display:flex;gap:var(--space-md)">
          <button class="btn btn-primary btn-sm btn-full" id="mark-ready-btn">Mark as ready</button>
          <button class="btn btn-danger btn-sm" id="archive-btn" title="Archive">${Icons.trash}</button>
        </div>
      ` : ''}

      ${isReady ? `
        <div class="card card-accent">
          <div style="text-align:center;padding:var(--space-lg) 0">
            <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);margin-bottom:var(--space-sm)">Ready to publish</div>
            <div style="color:var(--text-secondary);margin-bottom:var(--space-lg)">${UI.esc(draft.title || 'Untitled')}</div>
            <div style="display:flex;gap:var(--space-md);justify-content:center">
              <button class="btn btn-primary" id="publish-btn">${Icons.send} Publish now</button>
              <button class="btn btn-secondary" id="schedule-btn">${Icons.clock} Schedule</button>
            </div>
          </div>
        </div>

        <div class="section-title">Preview</div>
        <div class="card" id="preview-card">
          <div style="font-weight:var(--font-weight-semibold);margin-bottom:var(--space-sm)">${UI.esc(draft.title)}</div>
          <div style="font-size:var(--font-size-sm);color:var(--text-secondary);white-space:pre-wrap">${UI.esc(draft.text_content)}</div>
          ${draft.image_url ? `<img src="${UI.esc(draft.image_url)}" alt="" style="width:100%;border-radius:var(--radius-md);margin-top:var(--space-md)" />` : ''}
        </div>

        <div style="margin-top:var(--space-lg);display:flex;gap:var(--space-md)">
          <button class="btn btn-ghost btn-sm btn-full" id="back-to-draft-btn">← Back to draft</button>
          <button class="btn btn-danger btn-sm" id="archive-ready-btn" title="Archive">${Icons.trash}</button>
        </div>
      ` : ''}

      ${draft.status === 'published' ? `
        <div class="card card-accent" style="text-align:center">
          <div style="font-size:40px;margin-bottom:var(--space-md)">🎉</div>
          <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold)">Published</div>
          <div style="color:var(--text-secondary);margin-top:var(--space-sm)">${UI.esc(draft.title)}</div>
        </div>
      ` : ''}
    `;

    // Attach events
    _attachEvents(draft, project);
  }

  function _attachEvents(draft, project) {
    const pid = project.id;

    document.getElementById('save-draft-btn')?.addEventListener('click', async () => {
      try {
        const updated = await API.updateDraft(pid, draft.id, {
          title: document.getElementById('draft-title').value.trim(),
          text_content: document.getElementById('draft-text').value,
          topic: document.getElementById('draft-topic').value.trim(),
        });
        _updateDraftInStore(updated);
        UI.toast('Draft saved', 'success');
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('gen-text-btn')?.addEventListener('click', async () => {
      try {
        UI.toast('Generating text…', 'info');
        const result = await API.generateText(pid, draft.id);
        _updateDraftInStorePartial(draft.id, { text_content: result.draft_text_content });
        _renderEditor();
        UI.toast('Text generated!', 'success');
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('gen-image-btn')?.addEventListener('click', async () => {
      try {
        UI.toast('Generating image…', 'info');
        const result = await API.generateImage(pid, draft.id);
        _updateDraftInStorePartial(draft.id, { image_url: result.draft_image_url });
        _renderEditor();
        UI.toast('Image generated!', 'success');
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('mark-ready-btn')?.addEventListener('click', async () => {
      // Auto-save first
      try {
        const updated = await API.updateDraft(pid, draft.id, {
          title: document.getElementById('draft-title')?.value?.trim(),
          text_content: document.getElementById('draft-text')?.value,
          topic: document.getElementById('draft-topic')?.value?.trim(),
        });
        _updateDraftInStore(updated);
        const ready = await API.markReady(pid, draft.id);
        _updateDraftInStore(ready);
        _renderEditor();
        UI.toast('Draft marked as ready', 'success');
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('back-to-draft-btn')?.addEventListener('click', async () => {
      try {
        const d = await API.backToDraft(pid, draft.id);
        _updateDraftInStore(d);
        _renderEditor();
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('publish-btn')?.addEventListener('click', async () => {
      try {
        UI.toast('Publishing…', 'info');
        const result = await API.publishDraft(pid, draft.id);
        if (result.published) {
          _updateDraftInStorePartial(draft.id, { status: result.status });
          _renderEditor();
          UI.toast('Published successfully!', 'success');
        } else {
          UI.toast('Publish returned without confirmation', 'error');
        }
      } catch (e) { UI.toast(e.message, 'error'); }
    });

    document.getElementById('schedule-btn')?.addEventListener('click', () => {
      _showScheduleModal(pid, draft.id);
    });

    const archiveBtn = document.getElementById('archive-btn') || document.getElementById('archive-ready-btn');
    archiveBtn?.addEventListener('click', async () => {
      try {
        const d = await API.archiveDraft(pid, draft.id);
        _updateDraftInStore(d);
        _mode = 'list';
        _renderList();
        UI.toast('Draft archived', 'success');
      } catch (e) { UI.toast(e.message, 'error'); }
    });
  }

  function _showScheduleModal(pid, did) {
    const now = new Date();
    now.setHours(now.getHours() + 1);
    now.setMinutes(0, 0, 0);
    const defaultTime = now.toISOString().slice(0, 16);

    const html = `
      <div class="input-group">
        <label class="input-label" for="schedule-time">Publish at (UTC)</label>
        <input class="input" type="datetime-local" id="schedule-time" value="${defaultTime}" />
      </div>
      <button class="btn btn-primary btn-full" id="confirm-schedule-btn">${Icons.clock} Schedule</button>
    `;
    const modal = UI.showModal(html, 'Schedule post');
    modal.querySelector('#confirm-schedule-btn').addEventListener('click', async () => {
      const val = modal.querySelector('#schedule-time').value;
      if (!val) { UI.toast('Pick a time', 'error'); return; }
      try {
        const isoTime = new Date(val).toISOString();
        await API.scheduleDraft(pid, did, { publish_at: isoTime });
        UI.closeModal();
        UI.toast('Post scheduled!', 'success');
        await App.loadProjectData();
        _renderEditor();
      } catch (e) { UI.toast(e.message, 'error'); }
    });
  }

  function _updateDraftInStore(draft) {
    Store.update('drafts', (ds) => ds.map(d => d.id === draft.id ? draft : d));
  }

  function _updateDraftInStorePartial(draftId, partial) {
    Store.update('drafts', (ds) => ds.map(d => d.id === draftId ? { ...d, ...partial } : d));
  }

  async function newDraft() {
    const project = Store.getActiveProject();
    if (!project) { UI.toast('No active project', 'error'); return; }
    const prefs = Store.get('preferences');
    try {
      const draft = await API.createDraft(project.id, {
        title: '',
        tone: prefs.defaultTone || 'neutral',
        content_type: prefs.defaultContentType || 'text',
      });
      Store.update('drafts', (ds) => [draft, ...ds]);
      openDraft(draft.id);
    } catch (e) { UI.toast(e.message, 'error'); }
  }

  function openDraft(id) {
    _currentDraftId = id;
    _mode = 'edit';
    App.navigate('create');
  }

  function backToList() {
    _mode = 'list';
    _currentDraftId = null;
    _renderList();
  }

  return { render, newDraft, openDraft, backToList };
})();
