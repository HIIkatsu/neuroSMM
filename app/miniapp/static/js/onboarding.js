/**
 * NeuroSMM V2 — Онбординг
 * Пропускаемый, но полезный; собирает начальные настройки.
 */
const Onboarding = (() => {
  let _overlay = null;
  let _step = 0;
  const _totalSteps = 4;
  let _resolve = null;

  const TONE_LABELS = {
    neutral: 'Нейтральный',
    formal: 'Формальный',
    casual: 'Разговорный',
    humorous: 'Юмористический',
    promotional: 'Рекламный',
  };

  const CONTENT_TYPE_LABELS = {
    text: 'Текст',
    image: 'Изображение',
    text_and_image: 'Текст + изображение',
  };

  const _steps = [
    {
      icon: '✨',
      title: 'Добро пожаловать в NeuroSMM',
      desc: 'Создание контента и планирование публикаций для вашего Telegram-канала с помощью ИИ.',
      type: 'welcome',
    },
    {
      icon: '🎯',
      title: 'Ваш проект',
      desc: 'Создайте первый проект для организации контента канала.',
      type: 'project',
      fields: [
        { id: 'ob-project-title', label: 'Название проекта', placeholder: 'Например: Мой Tech-канал', tag: 'input', required: true },
        { id: 'ob-project-desc', label: 'Описание (необязательно)', placeholder: 'О чём этот канал?', tag: 'textarea' },
      ],
    },
    {
      icon: '🎨',
      title: 'Стиль контента',
      desc: 'Настройте тон и тип контента по умолчанию. Можно изменить позже в настройках.',
      type: 'preferences',
      choices: [
        { id: 'ob-tone', label: 'Тон по умолчанию', options: ['neutral', 'formal', 'casual', 'humorous', 'promotional'], labels: TONE_LABELS },
        { id: 'ob-content-type', label: 'Тип контента', options: ['text', 'image', 'text_and_image'], labels: CONTENT_TYPE_LABELS },
      ],
    },
    {
      icon: '📡',
      title: 'Подключить канал',
      desc: 'Привяжите Telegram-канал для прямой публикации. Можно сделать это позже.',
      type: 'channel',
      fields: [
        { id: 'ob-channel-id', label: 'Юзернейм или ID канала', placeholder: '@mychannel', tag: 'input' },
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
        <button class="btn btn-ghost btn-full" id="ob-skip">Пропустить</button>
        ${_step < _totalSteps - 1
          ? `<button class="btn btn-primary btn-full" id="ob-next">${_step === 0 ? 'Начать' : 'Далее'}</button>`
          : `<button class="btn btn-primary btn-full" id="ob-finish">Завершить настройку</button>`
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
            ${c.options.map(o => `<option value="${o}">${c.labels ? c.labels[o] : o}</option>`).join('')}
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
        UI.toast('Введите название проекта', 'error');
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
        UI.toast('Проект создан!', 'success');

        // Bind channel if provided
        const channelId = document.getElementById('ob-channel-id')?.value?.trim();
        if (channelId) {
          try {
            await API.bindChannel(project.id, { channel_identifier: channelId });
            UI.toast('Канал подключён!', 'success');
          } catch (e) {
            UI.toast(`Не удалось привязать канал: ${e.message}`, 'error');
          }
        }
      } catch (e) {
        UI.toast(`Не удалось создать проект: ${e.message}`, 'error');
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
