/**
 * NeuroSMM V2 — Onboarding Flow
 * Skippable but useful; collects meaningful setup information.
 */
const Onboarding = (() => {
  let _overlay = null;
  let _step = 0;
  const _totalSteps = 4;
  let _resolve = null;

  const _steps = [
    {
      icon: '✨',
      title: 'Welcome to NeuroSMM',
      desc: 'AI-powered content creation and scheduling for your Telegram channel.',
      type: 'welcome',
    },
    {
      icon: '🎯',
      title: 'Your project',
      desc: 'Create your first project to organize content for a channel.',
      type: 'project',
      fields: [
        { id: 'ob-project-title', label: 'Project name', placeholder: 'e.g. My Tech Channel', tag: 'input', required: true },
        { id: 'ob-project-desc', label: 'Description (optional)', placeholder: 'What is this channel about?', tag: 'textarea' },
      ],
    },
    {
      icon: '🎨',
      title: 'Content style',
      desc: 'Set your default tone and content preferences. You can change these later in Settings.',
      type: 'preferences',
      choices: [
        { id: 'ob-tone', label: 'Default tone', options: ['neutral', 'formal', 'casual', 'humorous', 'promotional'] },
        { id: 'ob-content-type', label: 'Default content type', options: ['text', 'image', 'text_and_image'] },
      ],
    },
    {
      icon: '📡',
      title: 'Connect channel',
      desc: 'Link your Telegram channel to publish content directly. You can skip this and do it later.',
      type: 'channel',
      fields: [
        { id: 'ob-channel-id', label: 'Channel username or ID', placeholder: '@mychannel', tag: 'input' },
      ],
    },
  ];

  function show() {
    return new Promise((resolve) => {
      _resolve = resolve;
      _step = 0;
      _render();
    });
  }

  function _render() {
    if (_overlay) _overlay.remove();

    _overlay = document.createElement('div');
    _overlay.className = 'onboarding-overlay';
    _overlay.innerHTML = `
      <div class="onboarding-progress">
        ${Array.from({ length: _totalSteps }, (_, i) =>
          `<div class="onboarding-dot ${i < _step ? 'completed' : ''} ${i === _step ? 'active' : ''}"></div>`
        ).join('')}
      </div>
      <div class="onboarding-content">
        ${_steps.map((s, i) => _renderStep(s, i)).join('')}
      </div>
      <div class="onboarding-actions">
        <button class="btn btn-ghost btn-full" id="ob-skip">Skip</button>
        ${_step < _totalSteps - 1
          ? `<button class="btn btn-primary btn-full" id="ob-next">${_step === 0 ? 'Get started' : 'Continue'}</button>`
          : `<button class="btn btn-primary btn-full" id="ob-finish">Finish setup</button>`
        }
      </div>
    `;

    document.body.appendChild(_overlay);

    // Events
    _overlay.querySelector('#ob-skip')?.addEventListener('click', _finish);
    _overlay.querySelector('#ob-next')?.addEventListener('click', _next);
    _overlay.querySelector('#ob-finish')?.addEventListener('click', _finishWithData);
  }

  function _renderStep(step, idx) {
    let content = '';

    if (step.type === 'welcome') {
      content = '';
    } else if (step.fields) {
      content = step.fields.map(f => `
        <div class="input-group">
          <label class="input-label" for="${f.id}">${UI.esc(f.label)}</label>
          ${f.tag === 'textarea'
            ? `<textarea class="input" id="${f.id}" placeholder="${UI.esc(f.placeholder || '')}"></textarea>`
            : `<input class="input" id="${f.id}" placeholder="${UI.esc(f.placeholder || '')}" ${f.required ? 'required' : ''} />`
          }
        </div>
      `).join('');
    } else if (step.choices) {
      content = step.choices.map(c => `
        <div class="input-group">
          <label class="input-label" for="${c.id}">${UI.esc(c.label)}</label>
          <select class="input" id="${c.id}">
            ${c.options.map(o => `<option value="${o}">${o.replace(/_/g, ' ')}</option>`).join('')}
          </select>
        </div>
      `).join('');
    }

    return `
      <div class="onboarding-step ${idx === _step ? 'active' : ''}" data-step="${idx}">
        <div class="onboarding-icon">${step.icon}</div>
        <div class="onboarding-title">${UI.esc(step.title)}</div>
        <div class="onboarding-desc">${UI.esc(step.desc)}</div>
        ${content}
      </div>
    `;
  }

  async function _next() {
    // Validate current step
    if (_step === 1) {
      const title = document.getElementById('ob-project-title')?.value?.trim();
      if (!title) {
        UI.toast('Please enter a project name', 'error');
        return;
      }
    }
    _step++;
    _render();
  }

  async function _finishWithData() {
    await _collectAndSave();
    _finish();
  }

  async function _collectAndSave() {
    // Collect project
    const projectTitle = document.getElementById('ob-project-title')?.value?.trim();
    const projectDesc = document.getElementById('ob-project-desc')?.value?.trim() || '';

    // Collect preferences
    const tone = document.getElementById('ob-tone')?.value || 'neutral';
    const contentType = document.getElementById('ob-content-type')?.value || 'text';

    // Save preferences
    Store.update('preferences', (p) => ({
      ...p,
      defaultTone: tone,
      defaultContentType: contentType,
    }));
    Store.savePreferences();

    // Create project if title provided
    if (projectTitle) {
      try {
        const project = await API.createProject({ title: projectTitle, description: projectDesc });
        Store.update('projects', (ps) => [...ps, project]);
        Store.setActiveProject(project.id);

        // Bind channel if provided
        const channelId = document.getElementById('ob-channel-id')?.value?.trim();
        if (channelId) {
          try {
            await API.bindChannel(project.id, { channel_identifier: channelId });
            UI.toast('Channel connected!', 'success');
          } catch (e) {
            UI.toast(`Channel binding failed: ${e.message}`, 'error');
          }
        }

    // Success toast for project (channel binding failure already shown separately above)
        UI.toast('Project created!', 'success');
      } catch (e) {
        UI.toast(`Failed to create project: ${e.message}`, 'error');
      }
    }
  }

  function _finish() {
    Store.setOnboardingComplete();
    if (_overlay) {
      _overlay.remove();
      _overlay = null;
    }
    if (_resolve) {
      _resolve();
      _resolve = null;
    }
  }

  return { show };
})();
