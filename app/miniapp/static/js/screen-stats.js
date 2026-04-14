/**
 * NeuroSMM V2 — Stats Screen
 * Screenshot-faithful: hero metrics card + secondary metric grid + insights.
 */
const ScreenStats = (() => {
  function render() {
    const el = document.getElementById('screen-stats');
    const project = Store.getActiveProject();
    const drafts = Store.get('drafts');
    const schedules = Store.get('schedules');

    if (!project) {
      el.innerHTML = `
        <div class="page-header"><div class="page-title">Статистика</div></div>
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <div class="empty-state-title">Нет проекта</div>
          <div class="empty-state-desc">Создайте проект для просмотра статистики</div>
        </div>`;
      return;
    }

    // Compute real metrics from data
    const totalDrafts = drafts.length;
    const publishedDrafts = drafts.filter(d => d.status === 'published').length;
    const readyDrafts = drafts.filter(d => d.status === 'ready').length;
    const activeDrafts = drafts.filter(d => d.status === 'draft').length;
    const archivedDrafts = drafts.filter(d => d.status === 'archived').length;

    const totalSchedules = schedules.length;
    const pendingSchedules = schedules.filter(s => s.status === 'pending').length;
    const publishedSchedules = schedules.filter(s => s.status === 'published').length;
    const failedSchedules = schedules.filter(s => s.status === 'failed').length;
    const cancelledSchedules = schedules.filter(s => s.status === 'cancelled').length;

    const publishRate = totalDrafts > 0 ? Math.round((publishedDrafts / totalDrafts) * 100) : 0;
    const scheduleSuccessRate = totalSchedules > 0 ? Math.round((publishedSchedules / totalSchedules) * 100) : 0;

    // Upcoming next scheduled
    const nextScheduled = schedules
      .filter(s => s.status === 'pending')
      .sort((a, b) => new Date(a.publish_at) - new Date(b.publish_at))[0];

    el.innerHTML = `
      <div class="page-header">
        <div class="page-title">Статистика</div>
        <div class="page-subtitle">${UI.esc(project.title)}</div>
      </div>

      <div class="hero-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <div style="font-size:var(--font-size-sm);color:var(--text-secondary);margin-bottom:var(--space-xs)">Опубликовано</div>
            <div style="font-size:40px;font-weight:var(--font-weight-bold);line-height:1">${publishedDrafts}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:var(--font-size-sm);color:var(--text-secondary);margin-bottom:var(--space-xs)">Конверсия</div>
            <div style="font-size:var(--font-size-2xl);font-weight:var(--font-weight-bold);color:var(--accent-light)">${publishRate}%</div>
          </div>
        </div>
        <div class="progress-bar" style="margin-top:var(--space-lg)">
          <div class="progress-fill" style="width:${publishRate}%"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:var(--space-sm);font-size:var(--font-size-xs);color:var(--text-muted)">
          <span>${publishedDrafts} опубл.</span>
          <span>${totalDrafts} всего черн.</span>
        </div>
      </div>

      <div class="section-title">Обзор контента</div>
      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-value" style="color:var(--status-draft)">${activeDrafts}</div>
          <div class="metric-label">В работе</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" style="color:var(--status-pending)">${readyDrafts}</div>
          <div class="metric-label">Готовы</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" style="color:var(--status-published)">${publishedDrafts}</div>
          <div class="metric-label">Опубликовано</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" style="color:var(--text-muted)">${archivedDrafts}</div>
          <div class="metric-label">В архиве</div>
        </div>
      </div>

      <div class="section-title">Расписание</div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--space-md)">
          <div>
            <div style="font-size:var(--font-size-2xl);font-weight:var(--font-weight-bold)">${totalSchedules}</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">Всего</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);color:var(--accent-light)">${scheduleSuccessRate}%</div>
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">Успешность</div>
          </div>
        </div>
        <div style="display:flex;gap:var(--space-md);font-size:var(--font-size-sm)">
          <span style="color:var(--status-pending)">⏳ ${pendingSchedules} ожидает</span>
          <span style="color:var(--status-published)">✓ ${publishedSchedules} выполнено</span>
          <span style="color:var(--status-failed)">✗ ${failedSchedules} ошибка</span>
        </div>
      </div>

      ${nextScheduled ? `
        <div class="section-title">Следующая публикация</div>
        <div class="card card-accent">
          <div style="display:flex;align-items:center;gap:var(--space-md)">
            <div style="color:var(--accent-light)">${Icons.clock}</div>
            <div>
              <div style="font-weight:var(--font-weight-semibold)">${UI.formatDateTime(nextScheduled.publish_at)}</div>
              <div style="font-size:var(--font-size-xs);color:var(--text-muted)">Черновик #${nextScheduled.draft_id}</div>
            </div>
          </div>
        </div>
      ` : ''}

      <div class="section-title">Подсказки</div>
      <div class="card">
        ${_buildInsights(drafts, schedules, project)}
      </div>
    `;
  }

  function _buildInsights(drafts, schedules, project) {
    const insights = [];

    if (drafts.length === 0) {
      insights.push({ icon: '💡', text: 'Создайте первый черновик, чтобы начать генерацию контента с ИИ.' });
    }

    const readyCount = drafts.filter(d => d.status === 'ready').length;
    if (readyCount > 0) {
      insights.push({ icon: '📦', text: `У вас ${readyCount} черновик(ов) готовы к публикации.` });
    }

    const failedSchedules = schedules.filter(s => s.status === 'failed');
    if (failedSchedules.length > 0) {
      insights.push({ icon: '⚠️', text: `${failedSchedules.length} неудачных публикаций. Перейдите в План для повтора.` });
    }

    if (!project.platform_channel_id) {
      insights.push({ icon: '📡', text: 'Подключите Telegram-канал для прямой публикации.' });
    }

    if (insights.length === 0) {
      insights.push({ icon: '✨', text: 'Всё отлично! Продолжайте создавать контент.' });
    }

    return insights.map(i => `
      <div style="display:flex;gap:var(--space-md);padding:var(--space-sm) 0;align-items:flex-start">
        <span style="font-size:18px;flex-shrink:0">${i.icon}</span>
        <span style="font-size:var(--font-size-sm);color:var(--text-secondary)">${UI.esc(i.text)}</span>
      </div>
    `).join('');
  }

  return { render };
})();
