/**
 * Aura — Sidebar Controller
 * Phase 2: theme switcher repurposed as sidebar collapse controller.
 * Persists collapsed state in localStorage.
 */

// ── Glass notifications: custom replacement for SweetAlert2 ────
// window.Swal is redefined here as a small custom implementation instead
// of loading the SweetAlert2 library. Every existing Swal.fire(...) call
// site across the app (~60+ of them) keeps working unchanged — same
// option names (icon, title, text, timer, showConfirmButton,
// showCancelButton, confirmButtonText, cancelButtonText, didOpen,
// allowOutsideClick), same .then(result => result.isConfirmed) shape.
//
// Calls with showCancelButton (delete confirmations — a real yes/no
// decision) render as a centered, blocking glass dialog (reusing the
// existing .glass-modal-backdrop/.glass-modal system). Everything else
// (create/update/delete success, errors, loading states) renders as a
// compact, non-blocking banner at the top of the page. Markup and
// styling: see .glass-toast* / .glass-confirm* in glass.css.
(function() {
  const ICONS = {success: '✓', error: '✕', warning: '!', info: 'i'};

  let toastContainer = null;
  let activeToast = null;
  let activeToastTimer = null;

  function getToastContainer() {
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'glass-toast-container';
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }

  function closeActiveToast() {
    if (activeToastTimer) {
      clearTimeout(activeToastTimer);
      activeToastTimer = null;
    }
    if (activeToast) {
      const el = activeToast;
      activeToast = null;
      el.classList.add('is-leaving');
      setTimeout(() => el.remove(), 200);
    }
  }

  function renderToast(options) {
    closeActiveToast();

    const container = getToastContainer();
    const type = options.icon || 'loading';

    const toast = document.createElement('div');
    toast.className = `glass-toast glass-toast-${type}`;

    const icon = document.createElement('div');
    icon.className = 'glass-toast-icon';
    if (options.icon) icon.textContent = ICONS[options.icon] || '';
    toast.appendChild(icon);

    if (options.title || options.text) {
      const body = document.createElement('div');
      body.className = 'glass-toast-body';
      if (options.title) {
        const title = document.createElement('div');
        title.className = 'glass-toast-title';
        title.textContent = options.title;
        body.appendChild(title);
      }
      if (options.text) {
        const text = document.createElement('div');
        text.className = 'glass-toast-text';
        text.textContent = options.text;
        body.appendChild(text);
      }
      toast.appendChild(body);
    }

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'glass-toast-close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', closeActiveToast);
    toast.appendChild(closeBtn);

    // Loading toasts (no icon — e.g. "Deleting...") stay open until the
    // next Swal.fire() call replaces them; nothing else auto-dismisses them.
    if (options.icon) {
      const duration = options.timer || (options.icon === 'error' ? 4000 : 2800);
      const progress = document.createElement('div');
      progress.className = 'glass-toast-progress';
      progress.style.animationDuration = duration + 'ms';
      toast.appendChild(progress);
      activeToastTimer = setTimeout(closeActiveToast, duration);
    }

    container.appendChild(toast);
    activeToast = toast;

    if (typeof options.didOpen === 'function') {
      options.didOpen();
    }
  }

  function renderConfirm(options) {
    return new Promise((resolve) => {
      const backdrop = document.createElement('div');
      backdrop.className = 'glass-modal-backdrop';

      const modal = document.createElement('div');
      modal.className = 'glass-modal';
      modal.style.cssText = 'max-width:380px;text-align:center;';

      const iconType = options.icon || 'warning';
      const icon = document.createElement('div');
      icon.className = `glass-confirm-icon icon-${iconType}`;
      icon.textContent = ICONS[iconType] || ICONS.warning;
      modal.appendChild(icon);

      if (options.title) {
        const title = document.createElement('div');
        title.className = 'glass-modal-title';
        title.style.justifyContent = 'center';
        title.textContent = options.title;
        modal.appendChild(title);
      }

      if (options.text) {
        const text = document.createElement('p');
        text.style.cssText = 'color:var(--ts);font-size:0.88rem;margin-top:8px;';
        text.textContent = options.text;
        modal.appendChild(text);
      }

      const footer = document.createElement('div');
      footer.className = 'glass-modal-footer';
      footer.style.justifyContent = 'center';

      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button';
      cancelBtn.className = 'btn-glass btn-glass-secondary';
      cancelBtn.textContent = options.cancelButtonText || 'Cancel';
      cancelBtn.addEventListener('click', () => {
        backdrop.remove();
        resolve({isConfirmed: false, isDismissed: true});
      });
      footer.appendChild(cancelBtn);

      const confirmBtn = document.createElement('button');
      confirmBtn.type = 'button';
      confirmBtn.className = 'btn-glass btn-glass-danger';
      confirmBtn.textContent = options.confirmButtonText || 'OK';
      confirmBtn.addEventListener('click', () => {
        backdrop.remove();
        resolve({isConfirmed: true});
      });
      footer.appendChild(confirmBtn);

      modal.appendChild(footer);
      backdrop.appendChild(modal);
      document.body.appendChild(backdrop);
    });
  }

  window.Swal = {
    fire(options) {
      options = options || {};
      if (options.showCancelButton) {
        return renderConfirm(options);
      }
      renderToast(options);
      return Promise.resolve({isConfirmed: false, isDismissed: true});
    },
    showLoading() {
      // No-op: the loading spinner is already rendered via CSS on
      // .glass-toast-loading when renderToast() is called with no icon.
    },
    close() {
      closeActiveToast();
    },
  };
})();

// ── Shared currency formatter (Sprint 17, MC-006) ───────────────
window.formatMoney = function(amount, currencyCode) {
  const code = currencyCode || 'RON';
  try {
    return new Intl.NumberFormat('en-US', {style: 'currency', currency: code}).format(amount || 0);
  } catch (e) {
    return `${(amount || 0).toFixed(2)} ${code}`;
  }
};

const SIDEBAR_KEY = 'aura-sidebar-collapsed';

// ── Apply saved collapse state on load ────────────────────────
function applySidebarState() {
  if (localStorage.getItem(SIDEBAR_KEY) === 'true') {
    document.body.classList.add('sidebar-collapsed');
  }
}

/* DISABLED (Release 7 paused) — Abyss-only per user decision.
   base.html now hardcodes data-theme="abyss" directly on <html>, which
   alone is sufficient (theme.css's `:root` block already equals Abyss),
   so this switcher is fully inert without it. Preserved below for
   reference / future revival: docs/releases/release-07-plan.md

// ── Theme switcher (Sprint 34) ──────────────────────────────────
// Persisted the same way as sidebar-collapse: a localStorage key read on
// every page load. `:root` in theme.css doubles as the "abyss" block, so a
// document with no data-theme attribute at all still renders Abyss — this
// stays correct even if this script fails to run for any reason.
const THEME_KEY = 'aura-theme';
const DEFAULT_THEME = 'abyss';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

function initThemeSwitcher() {
  const saved = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  applyTheme(saved);

  const select = document.getElementById('theme-select');
  if (!select) return;
  select.value = saved;
  select.addEventListener('change', () => {
    applyTheme(select.value);
    localStorage.setItem(THEME_KEY, select.value);
    // Chart.js bakes color options in at chart-creation time — CSS custom
    // properties changing afterward doesn't retroactively repaint an
    // already-rendered canvas. Pages with charts (dashboard.js) listen for
    // this and re-render their charts; pages without charts just ignore it.
    window.dispatchEvent(new CustomEvent('aura:theme-changed', {detail: {theme: select.value}}));
  });
}
*/

// ── Wire sidebar collapse toggle button ───────────────────────
function initSidebarCollapse() {
  const btn = document.getElementById('sidebar-collapse-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_KEY, collapsed);
  });
}

// ── Mark active nav link based on current path ────────────────
function markActiveNavLink() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item[href]').forEach(link => {
    const href = link.getAttribute('href');
    const isActive = href && href !== '/' && path.startsWith(href);
    const isExactHome = href === '/' && path === '/';
    link.classList.toggle('active', isActive || isExactHome);
  });
}

/* DISABLED (Release 7 paused) — Abyss-only per user decision. Floating
   labels (Sprint 36 WI-007) preserved below for reference / future
   revival: docs/releases/release-07-plan.md

// ── Floating labels (Sprint 36, Wisteria — WI-007) ──────────────────
// CSS-driven (see glass.css's [data-theme="wisteria"] .form-group-glass
// rules); this just toggles state classes. Event delegation on `document`
// means every .form-group-glass on every page works automatically, with
// zero changes needed to any of the many existing form templates —
// including ones added to the DOM later (e.g. inside a modal).
function updateFloatingLabelState(input) {
  const group = input.closest('.form-group-glass');
  if (!group) return;
  // A <select> always renders real, visible text for whatever option is
  // current — even a blank-value placeholder option ("Select category…")
  // is real content, unlike a text input's placeholder attribute, which
  // actually disappears once something is typed. So a select's label must
  // always sit in the compact floated position; there's no "empty" visual
  // state for it to safely overlap the way an empty text input has.
  const hasValue = input.tagName === 'SELECT' ? true : !!input.value;
  group.classList.toggle('has-value', hasValue);
}
document.addEventListener('focusin', (e) => {
  if (!e.target.matches || !e.target.matches('.glass-input, .glass-select, .glass-textarea')) return;
  const group = e.target.closest('.form-group-glass');
  if (group) group.classList.add('is-focused');
});
document.addEventListener('focusout', (e) => {
  const group = e.target.closest && e.target.closest('.form-group-glass');
  if (group) group.classList.remove('is-focused');
});
document.addEventListener('input', (e) => {
  if (e.target.matches && e.target.matches('.glass-input, .glass-select, .glass-textarea')) {
    updateFloatingLabelState(e.target);
  }
});
*/

/* DISABLED (Release 7 paused) — Abyss-only per user decision. Interaction
   glow (Sprint 36 WI-009, Sprint 37 TE-003) preserved below for reference
   / future revival: docs/releases/release-07-plan.md

// ── Interaction glow (Sprint 36 WI-009, generalized Sprint 37 TE-003) ──
// "When you touch a Liquid Glass element it illuminates from within...
// starting right under your fingertips" (design-guidance-2.md). Gated
// here too (not just in CSS) so pointerdown elsewhere in the app doesn't
// do pointless work every single click. Allow-list, not a single string
// comparison, since Tempest now shares this mechanism with Wisteria.
const GLOW_THEMES = ['wisteria', 'tempest'];
document.addEventListener('pointerdown', (e) => {
  if (!GLOW_THEMES.includes(document.documentElement.getAttribute('data-theme'))) return;
  const target = e.target.closest('.glass-card, .btn-glass');
  if (!target) return;
  const rect = target.getBoundingClientRect();
  target.style.setProperty('--glow-x', (e.clientX - rect.left) + 'px');
  target.style.setProperty('--glow-y', (e.clientY - rect.top) + 'px');
  target.classList.remove('glow-active');
  void target.offsetWidth; // force reflow so re-adding the class restarts the animation
  target.classList.add('glow-active');
});
document.addEventListener('animationend', (e) => {
  if (e.animationName === 'wisteria-glow-fade') {
    e.target.classList.remove('glow-active');
  }
});
*/

// ── Bootstrap ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applySidebarState();
  initSidebarCollapse();
  markActiveNavLink();
  // initThemeSwitcher() and the floating-label initial-state pass were
  // called here (Release 7); both disabled above along with the features
  // they drove. See docs/releases/release-07-plan.md.
});
