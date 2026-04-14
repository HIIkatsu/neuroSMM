/**
 * NeuroSMM V2 — Plan / Schedule Screen
 * Screenshot-faithful: week day selector + timeline cards.
 */
const ScreenPlan = (() => {
  let _selectedDate = new Date();

  const _statusLabels = { pending: 'ЗАПЛАНИРОВАН', failed: 'ОШИБКА', published: 'ОПУБЛИКОВАН', cancelled: 'ОТМЕНЁН' };

  function render() {
    const el = document.getElementById('screen-plan');
    const project = Store.getActiveProject();
    const schedules = Store.get('schedules');
    const drafts = Store.get('drafts');

    if (!project) {
      el.innerHTML = `
        <div class="page-header"><div class="page-title">План</div></div>
        <div class="empty-state">
          <div class="empty-state-icon">📅</div>
          <div class="empty-state-title">Нет проекта</div>
          <div class="empty-state-desc">Сначала создайте проект, чтобы увидеть расписание</div>
        </div>`;
      return;
    }

    const weekDays = _getWeekDays(_selectedDate);
    const daySchedules = _getSchedulesForDay(schedules, drafts, _selectedDate);
    const timeSlots = _buildTimeSlots(daySchedules);

    el.innerHTML = `
      <div class="page-header">
        <div class="page-title">План</div>
      </div>

      <div class="week-selector">
        ${weekDays.map(d => {
          const isActive = _isSameDay(d.date, _selectedDate);
          const hasItems = _hasSchedulesOnDay(schedules, d.date);
          return `
            <div class="day-chip ${isActive ? 'active' : ''} ${hasItems ? 'has-items' : ''}"
                 onclick="ScreenPlan.selectDay('${d.date.toISOString()}')"
                 role="button" tabindex="0">
              <span class="day-name">${d.dayName}</span>
              <span class="day-number">${d.dayNumber}</span>
            </div>`;
        }).join('')}
      </div>

      <div style="margin-top:var(--space-2xl)">
        ${timeSlots.length === 0 ? `
          <div class="empty-state" style="padding:var(--space-2xl) 0">
            <div class="empty-state-icon">📅</div>
            <div class="empty-state-title">Ничего не запланировано</div>
            <div class="empty-state-desc">Нет постов на этот день</div>
          </div>
        ` : ''}

        ${timeSlots.map(slot => {
          if (slot.type === 'scheduled') {
            const statusClass = `status-${slot.schedule.status === 'pending' ? 'scheduled' : slot.schedule.status}`;
            const statusLabel = _statusLabels[slot.schedule.status] || slot.schedule.status.toUpperCase();
            return `
              <div class="timeline-slot">
                <div class="timeline-time">${slot.time}</div>
                <div class="timeline-card ${statusClass}" onclick="ScreenPlan.openSchedule(${slot.schedule.id})" style="cursor:pointer">
                  <span class="badge badge-${slot.schedule.status === 'pending' ? 'scheduled' : slot.schedule.status}" style="margin-bottom:var(--space-sm);display:inline-block">${statusLabel}</span>
                  <div style="font-weight:var(--font-weight-semibold)">${UI.esc(slot.draftTitle)}</div>
                  ${slot.schedule.failure_reason ? `<div style="font-size:var(--font-size-xs);color:var(--status-failed);margin-top:var(--space-xs)">${UI.esc(slot.schedule.failure_reason)}</div>` : ''}
                </div>
              </div>`;
          } else {
            return `
              <div class="timeline-slot">
                <div class="timeline-time">${slot.time}</div>
                <div class="timeline-card-empty" onclick="ScreenPlan.addAtTime('${slot.time}')">
                  + Запланировать
                </div>
              </div>`;
          }
        }).join('')}
      </div>

      <button class="fab" onclick="ScreenPlan.addAtTime(null)" aria-label="Добавить запланированный пост">
        ${Icons.plus}
      </button>
    `;
  }

  function selectDay(isoStr) {
    _selectedDate = new Date(isoStr);
    render();
  }

  function _getWeekDays(centerDate) {
    const days = [];
    const d = new Date(centerDate);
    const dayOfWeek = d.getDay();
  // Days-since-Monday offset: JS getDay() returns 0=Sun,1=Mon,...,6=Sat.
    // (dayOfWeek + 6) % 7 converts to 0=Mon,...,6=Sun.
    const monday = new Date(d);
    monday.setDate(d.getDate() - ((dayOfWeek + 6) % 7));

    const names = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'];
    for (let i = 0; i < 7; i++) {
      const day = new Date(monday);
      day.setDate(monday.getDate() + i);
      days.push({
        date: day,
        dayName: names[i],
        dayNumber: day.getDate(),
      });
    }
    return days;
  }

  function _isSameDay(a, b) {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth() === b.getMonth() &&
           a.getDate() === b.getDate();
  }

  function _hasSchedulesOnDay(schedules, date) {
    return schedules.some(s => {
      const sd = new Date(s.publish_at);
      return _isSameDay(sd, date);
    });
  }

  function _getSchedulesForDay(schedules, drafts, date) {
    return schedules
      .filter(s => _isSameDay(new Date(s.publish_at), date))
      .map(s => ({
        schedule: s,
        draft: drafts.find(d => d.id === s.draft_id),
      }))
      .sort((a, b) => new Date(a.schedule.publish_at) - new Date(b.schedule.publish_at));
  }

  function _buildTimeSlots(daySchedules) {
    const slots = [];

    // Add actual scheduled items
    for (const item of daySchedules) {
      const time = UI.formatTime(item.schedule.publish_at);
      slots.push({
        type: 'scheduled',
        time,
        schedule: item.schedule,
        draftTitle: item.draft?.title || 'Без названия',
      });
    }

    // Add empty slots between scheduled items
    const usedHours = new Set(daySchedules.map(d => new Date(d.schedule.publish_at).getHours()));
    const defaultHours = [9, 12, 15, 18];
    for (const h of defaultHours) {
      if (!usedHours.has(h)) {
        const timeStr = `${String(h).padStart(2, '0')}:00`;
        slots.push({ type: 'empty', time: timeStr });
      }
    }

    // Sort by time string
    slots.sort((a, b) => a.time.localeCompare(b.time));
    return slots;
  }

  function openSchedule(scheduleId) {
    const project = Store.getActiveProject();
    const schedules = Store.get('schedules');
    const schedule = schedules.find(s => s.id === scheduleId);
    if (!schedule || !project) return;

    const drafts = Store.get('drafts');
    const draft = drafts.find(d => d.id === schedule.draft_id);

    let actions = '';
    if (schedule.status === 'pending') {
      actions = `<button class="btn btn-danger btn-full" id="cancel-schedule-btn">Отменить расписание</button>`;
    } else if (schedule.status === 'failed') {
      const retryDefault = new Date();
      retryDefault.setHours(retryDefault.getHours() + 1);
      retryDefault.setMinutes(0, 0, 0);
      const retryTimeValue = retryDefault.toISOString().slice(0, 16);
      actions = `
        <div class="input-group">
          <label class="input-label" for="retry-time">Новое время (UTC)</label>
          <input class="input" type="datetime-local" id="retry-time" value="${retryTimeValue}" />
        </div>
        <button class="btn btn-primary btn-full" id="retry-schedule-btn">${Icons.refresh} Повторить</button>
      `;
    }

    const html = `
      <div class="card" style="margin-bottom:var(--space-lg)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--space-md)">
          <span style="font-weight:var(--font-weight-semibold)">${UI.esc(draft?.title || 'Без названия')}</span>
          ${UI.statusBadge(schedule.status)}
        </div>
        <div style="font-size:var(--font-size-sm);color:var(--text-secondary)">
          Запланировано на ${UI.formatDateTime(schedule.publish_at)}
        </div>
        ${schedule.failure_reason ? `
          <div style="margin-top:var(--space-sm);font-size:var(--font-size-sm);color:var(--status-failed)">
            ${UI.esc(schedule.failure_reason)}
          </div>` : ''}
        ${schedule.published_at ? `
          <div style="margin-top:var(--space-sm);font-size:var(--font-size-sm);color:var(--status-published)">
            Опубликовано ${UI.formatDateTime(schedule.published_at)}
          </div>` : ''}
      </div>
      ${actions}
    `;

    const modal = UI.showModal(html, 'Запланированный пост');

    modal.querySelector('#cancel-schedule-btn')?.addEventListener('click', async function() {
      const confirmed = await UI.confirm('Отменить запланированный пост?', 'Отменить расписание');
      if (!confirmed) return;
      await UI.withButtonLoading(this, async () => {
        try {
          await API.cancelSchedule(project.id, scheduleId);
          UI.closeModal();
          UI.toast('Расписание отменено', 'success');
          await App.loadProjectData();
          render();
        } catch (e) { UI.toast(e.message, 'error'); }
      }, 'Отмена…');
    });

    modal.querySelector('#retry-schedule-btn')?.addEventListener('click', async function() {
      const val = modal.querySelector('#retry-time').value;
      if (!val) { UI.toast('Выберите время', 'error'); return; }
      const selectedTime = new Date(val);
      if (selectedTime <= new Date()) { UI.toast('Время должно быть в будущем', 'error'); return; }
      await UI.withButtonLoading(this, async () => {
        try {
          await API.retrySchedule(project.id, scheduleId, {
            new_publish_at: selectedTime.toISOString(),
          });
          UI.closeModal();
          UI.toast('Расписание обновлено', 'success');
          await App.loadProjectData();
          render();
        } catch (e) { UI.toast(e.message, 'error'); }
      }, 'Повтор…');
    });
  }

  function addAtTime(timeStr) {
    // Navigate to Create screen to make a new draft, then come back to schedule
    const drafts = Store.get('drafts');
    const readyDrafts = drafts.filter(d => d.status === 'ready');

    if (readyDrafts.length === 0) {
      UI.toast('Нет готовых черновиков. Сначала создайте и отметьте черновик.', 'info');
      App.navigate('create');
      return;
    }

    const project = Store.getActiveProject();
    const now = new Date();
    let defaultTime;

    if (timeStr) {
      const [h, m] = timeStr.split(':').map(Number);
      defaultTime = new Date(_selectedDate);
      defaultTime.setHours(h, m, 0, 0);
      // If the selected date+time is in the past, use the next available slot from now
      if (defaultTime < now) {
        defaultTime = new Date(now);
        defaultTime.setHours(h, m, 0, 0);
        if (defaultTime < now) {
          defaultTime.setDate(defaultTime.getDate() + 1);
        }
      }
    } else {
      defaultTime = new Date(now);
      defaultTime.setHours(defaultTime.getHours() + 1);
      defaultTime.setMinutes(0, 0, 0);
    }

    const html = `
      <div class="input-group">
        <label class="input-label" for="sched-draft">Выберите черновик</label>
        <select class="input" id="sched-draft">
          ${readyDrafts.map(d => `<option value="${d.id}">${UI.esc(d.title || 'Без названия')}</option>`).join('')}
        </select>
      </div>
      <div class="input-group">
        <label class="input-label" for="sched-time">Дата публикации (UTC)</label>
        <input class="input" type="datetime-local" id="sched-time" value="${defaultTime.toISOString().slice(0, 16)}" />
      </div>
      <button class="btn btn-primary btn-full" id="confirm-add-schedule">Запланировать</button>
    `;

    const modal = UI.showModal(html, 'Запланировать пост');
    modal.querySelector('#confirm-add-schedule').addEventListener('click', async function() {
      const draftId = parseInt(modal.querySelector('#sched-draft').value, 10);
      const val = modal.querySelector('#sched-time').value;
      if (!val) { UI.toast('Выберите время', 'error'); return; }
      const selectedTime = new Date(val);
      if (selectedTime <= new Date()) { UI.toast('Время должно быть в будущем', 'error'); return; }
      await UI.withButtonLoading(this, async () => {
        try {
          await API.scheduleDraft(project.id, draftId, { publish_at: selectedTime.toISOString() });
          UI.closeModal();
          UI.toast('Пост запланирован!', 'success');
          await App.loadProjectData();
          render();
        } catch (e) { UI.toast(e.message, 'error'); }
      }, 'Планирование…');
    });
  }

  return { render, selectDay, openSchedule, addAtTime };
})();
