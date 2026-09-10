// ============================================================================
// SCOREBOARD PAGE - JAVASCRIPT
// Sprint 41: Sound Breathing - String Performance (self-report, localStorage)
// Sprint 42: Sound Breathing - Constant Resounding Slashes (real per-user
//            persistence + leaderboard, for logged-in visitors)
//
// Dual mode: an anonymous visitor keeps Sprint 41's localStorage-only
// behavior; a logged-in visitor gets server-backed persistence via
// /api/scoreboard/*, with a one-time migration of any local progress into
// their account the first time they're seen logged in on this page.
// ============================================================================

const STORAGE_KEY = 'aura_scoreboard_found';
const MIGRATED_KEY = 'aura_scoreboard_migrated';

function isLoggedIn() {
    return typeof window.CURRENT_USER_ID !== 'undefined' && !!window.CURRENT_USER_ID;
}

function loadFound() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch (e) {
        return new Set();
    }
}

function saveFound(foundSet) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(foundSet)));
}

async function fetchServerProgress(userId) {
    // Returns a Map of vuln_id -> source ('self_report' | 'flag'), so the
    // caller can tell proven (flag-verified) finds apart from claimed
    // (self-reported) ones. Sourced from /progress, VULN-082's own
    // endpoint — safe to reuse here since `source` alone isn't sensitive,
    // unlike the actual flag_value (deliberately never in this response).
    try {
        const res = await fetch(`/api/scoreboard/progress?user_id=${userId}`);
        const data = await res.json();
        const map = new Map();
        if (data.success) data.progress.forEach(p => map.set(p.vuln_id, p.source));
        return map;
    } catch (e) {
        return new Map();
    }
}

async function markServer(userId, vulnId) {
    try {
        await fetch('/api/scoreboard/mark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, vuln_id: vulnId }),
        });
    } catch (e) { /* best-effort */ }
}

async function unmarkServer(userId, vulnId) {
    try {
        await fetch('/api/scoreboard/unmark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, vuln_id: vulnId }),
        });
    } catch (e) { /* best-effort */ }
}

async function migrateLocalIfNeeded(userId) {
    if (localStorage.getItem(MIGRATED_KEY)) return;
    const local = loadFound();
    for (const vulnId of local) {
        await markServer(userId, vulnId);
    }
    localStorage.setItem(MIGRATED_KEY, '1');
}

async function loadLeaderboard() {
    const list = document.getElementById('leaderboardList');
    if (!list) return;

    try {
        const res = await fetch('/api/scoreboard/leaderboard');
        const data = await res.json();

        if (!data.success || data.leaderboard.length === 0) {
            list.innerHTML = '<div class="leaderboard-empty">No one has found anything yet. Be the first.</div>';
            return;
        }

        list.innerHTML = data.leaderboard.map((entry, i) => `
            <div class="leaderboard-row">
                <span class="leaderboard-rank">#${i + 1}</span>
                <span class="leaderboard-name">${entry.username}</span>
                <span class="leaderboard-count">${entry.found_count}</span>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = '<div class="leaderboard-empty">Couldn\'t load the leaderboard.</div>';
    }
}

async function fetchMyFlags() {
    // Returns a Map of vuln_id -> flag_value for whatever this account has
    // actually earned. The "proven" badge alone only ever said the word
    // "proven" — the real flag text was only ever visible once, in the
    // one-time solve popup — so there was no way to look back later and
    // see which flag belonged to which finding. /flags is session-based
    // (safe, login-gated) and already nulls flag_value server-side when
    // the organizer has CTF mode off, so no extra gating needed here.
    try {
        const res = await fetch('/api/scoreboard/flags');
        const data = await res.json();
        const map = new Map();
        if (data.success) {
            data.flags.forEach(f => { if (f.flag_value) map.set(f.vuln_id, f.flag_value); });
        }
        return map;
    } catch (e) {
        return new Map();
    }
}

function updateCounters(foundSet) {
    document.getElementById('foundCount').textContent = foundSet.size;

    document.querySelectorAll('.category-block').forEach(block => {
        const category = block.getAttribute('data-category');
        const checks = block.querySelectorAll('.challenge-check[data-vuln-id]');
        let total = checks.length;
        let found = 0;
        checks.forEach(cb => {
            if (foundSet.has(cb.getAttribute('data-vuln-id'))) found++;
        });
        const countEl = document.querySelector(`[data-category-count="${CSS.escape(category)}"]`);
        if (countEl) countEl.textContent = `${found} / ${total}`;
    });
}

function setupTabs() {
    const tabs = document.querySelectorAll('.scoreboard-tab');
    const blocks = document.querySelectorAll('.category-block');

    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const target = tab.getAttribute('data-tab-target');

            tabs.forEach(t => t.classList.toggle('is-active', t === tab));
            blocks.forEach(b => b.classList.toggle('is-active', b.getAttribute('data-category') === target));
        });
    });
}

function addProvenBadge(row, flagValue) {
    if (!row.querySelector('.proven-badge')) {
        const badge = document.createElement('span');
        badge.className = 'proven-badge';
        badge.textContent = 'proven';
        row.appendChild(badge);
    }
    if (flagValue && !row.querySelector('.proven-flag')) {
        const body = row.querySelector('.challenge-body');
        const flagEl = document.createElement('div');
        flagEl.className = 'proven-flag';
        flagEl.textContent = flagValue;
        body.appendChild(flagEl);
    }
}

function wireCheckboxes(foundSet, serverMode, sourceMap, flagMap) {
    document.querySelectorAll('.challenge-check[data-vuln-id]').forEach(cb => {
        const vulnId = cb.getAttribute('data-vuln-id');
        const row = cb.closest('.challenge-row');

        if (foundSet.has(vulnId)) {
            cb.checked = true;
            row.classList.add('is-found');
            if (sourceMap && sourceMap.get(vulnId) === 'flag') {
                addProvenBadge(row, flagMap ? flagMap.get(vulnId) : null);
            }
        }

        cb.addEventListener('change', async function () {
            if (cb.checked) {
                foundSet.add(vulnId);
                row.classList.add('is-found');
                if (serverMode) await markServer(window.CURRENT_USER_ID, vulnId);
            } else {
                foundSet.delete(vulnId);
                row.classList.remove('is-found');
                if (serverMode) await unmarkServer(window.CURRENT_USER_ID, vulnId);
            }

            if (!serverMode) saveFound(foundSet);
            updateCounters(foundSet);
            if (serverMode) loadLeaderboard();
        });
    });
}

document.addEventListener('DOMContentLoaded', async function () {
    setupTabs();
    loadLeaderboard();

    let foundSet;
    if (isLoggedIn()) {
        await migrateLocalIfNeeded(window.CURRENT_USER_ID);
        const sourceMap = await fetchServerProgress(window.CURRENT_USER_ID);
        const flagMap = await fetchMyFlags();
        foundSet = new Set(sourceMap.keys());
        wireCheckboxes(foundSet, true, sourceMap, flagMap);
    } else {
        foundSet = loadFound();
        wireCheckboxes(foundSet, false, null, null);
    }

    updateCounters(foundSet);
});
