/**
 * NeuroSMM V2 Mini App — UI Helpers & Toast System
 */
const UI = (() => {
  // ── Toast ─────────────────────────────────────────────────
  let _toastContainer;

  function _ensureToastContainer() {
    if (!_toastContainer) {
      _toastContainer = document.createElement('div');
      _toastContainer.className = 'toast-container';
      document.body.appendChild(_toastContainer);
    }
    return _toastContainer;
  }

  const TOAST_AUTO_DISMISS_MS = 3000;

  function toast(message, type = 'info') {
    const container = _ensureToastContainer();
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(-16px)';
      el.style.transition = 'all 300ms ease';
      setTimeout(() => el.remove(), 300);
    }, TOAST_AUTO_DISMISS_MS);
  }

  // ── Modal ─────────────────────────────────────────────────
  let _currentModal = null;

  function showModal(contentHTML, title) {
    closeModal();
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-sheet">
        <div class="modal-handle"></div>
        ${title ? `<div class="modal-title">${_esc(title)}</div>` : ''}
        <div class="modal-body">${contentHTML}</div>
      </div>
    `;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
    document.body.appendChild(overlay);
    _currentModal = overlay;
    return overlay;
  }

  function closeModal() {
    if (_currentModal) {
      _currentModal.remove();
      _currentModal = null;
    }
  }

  // ── Helpers ───────────────────────────────────────────────
  function _esc(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
  }

  function formatDate(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    const now = new Date();
    // Include year if different from current year
    const opts = { month: 'short', day: 'numeric' };
    if (d.getFullYear() !== now.getFullYear()) {
      opts.year = 'numeric';
    }
    return d.toLocaleDateString(undefined, opts);
  }

  function formatTime(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
  }

  function formatDateTime(isoStr) {
    if (!isoStr) return '—';
    return `${formatDate(isoStr)} ${formatTime(isoStr)}`;
  }

  function statusBadge(status) {
    const cls = {
      draft: 'badge-draft',
      ready: 'badge-ready',
      published: 'badge-published',
      archived: 'badge-cancelled',
      pending: 'badge-pending',
      scheduled: 'badge-scheduled',
      failed: 'badge-failed',
      cancelled: 'badge-cancelled',
    }[status] || 'badge-draft';
    return `<span class="badge ${cls}">${_esc(status)}</span>`;
  }

  function setLoading(key, isLoading) {
    Store.update('loading', (l) => ({ ...l, [key]: isLoading }));
  }

  function isLoading(key) {
    return Store.get('loading')[key] || false;
  }

  function esc(str) { return _esc(str); }

  /**
   * Show a confirmation dialog via modal and return a promise that resolves to true/false.
   */
  function confirm(message, confirmLabel = 'Confirm', cancelLabel = 'Cancel') {
    return new Promise((resolve) => {
      const html = `
        <div style="margin-bottom:var(--space-lg);font-size:var(--font-size-base);color:var(--text-secondary)">${_esc(message)}</div>
        <div style="display:flex;gap:var(--space-md)">
          <button class="btn btn-ghost btn-full" id="confirm-cancel">${_esc(cancelLabel)}</button>
          <button class="btn btn-danger btn-full" id="confirm-ok">${_esc(confirmLabel)}</button>
        </div>
      `;
      const modal = showModal(html, 'Confirm');
      modal.querySelector('#confirm-ok').addEventListener('click', () => {
        closeModal();
        resolve(true);
      });
      modal.querySelector('#confirm-cancel').addEventListener('click', () => {
        closeModal();
        resolve(false);
      });
    });
  }

  /**
   * Wrap an async action with button loading state (disabled + spinner text).
   * Returns the result of the action.
   */
  async function withButtonLoading(btn, action, loadingText) {
    if (!btn || btn.disabled) return;
    const originalHTML = btn.innerHTML;
    const originalDisabled = btn.disabled;
    btn.disabled = true;
    btn.innerHTML = loadingText || 'Loading…';
    try {
      return await action();
    } finally {
      btn.disabled = originalDisabled;
      btn.innerHTML = originalHTML;
    }
  }

  return {
    toast, showModal, closeModal, confirm, withButtonLoading,
    formatDate, formatTime, formatDateTime,
    statusBadge, setLoading, isLoading, esc,
  };
})();
