// ═══════════════════════════════════════════════════════════════════════════
// SOCIAL VISIBILITY
// ═══════════════════════════════════════════════════════════════════════════

let svCurrentPieceId = null;
let svCurrentTopicId = null;
let svSchedulingPieceId = null;
let svPostPieceId = null;

// Platform definitions (all supported platforms)
const SV_PLATFORMS = [
    { key: 'linkedin',  label: 'LinkedIn',         icon: 'fab fa-linkedin',  color: '#0077b5', automatable: true,  desc: 'Professional network — articles & posts' },
    { key: 'twitter',   label: 'Twitter / X',      icon: 'fab fa-twitter',   color: '#1da1f2', automatable: false, desc: 'Short-form content & thought leadership' },
    { key: 'medium',    label: 'Medium',            icon: 'fab fa-medium',    color: '#00ab6c', automatable: false, desc: 'Long-form articles & blog posts' },
    { key: 'github',    label: 'GitHub',            icon: 'fab fa-github',    color: '#333333', automatable: false, desc: 'Profile README & project showcasing' },
    { key: 'portfolio', label: 'Portfolio / Blog',  icon: 'fas fa-globe',     color: '#6f42c1', automatable: false, desc: 'Personal website or portfolio' },
    { key: 'instagram', label: 'Instagram',         icon: 'fab fa-instagram', color: '#e1306c', automatable: false, desc: 'Visual content & personal brand' },
    { key: 'youtube',   label: 'YouTube',           icon: 'fab fa-youtube',   color: '#ff0000', automatable: false, desc: 'Video content & tutorials' },
    { key: 'facebook',  label: 'Facebook',          icon: 'fab fa-facebook',  color: '#1877f2', automatable: false, desc: 'Community & group engagement' },
];

// ── Panel navigation ──────────────────────────────────────────────────────

function showSocialPanel(panelId, btn) {
    document.querySelectorAll('.social-panel').forEach(p => p.classList.add('d-none'));
    document.querySelectorAll('.social-nav-btn').forEach(b => {
        b.classList.remove('active', 'btn-primary');
        b.classList.add('btn-light');
    });
    const panel = document.getElementById(panelId);
    if (panel) panel.classList.remove('d-none');
    if (btn) { btn.classList.add('active', 'btn-primary'); btn.classList.remove('btn-light'); }
    if (panelId === 'sv-platforms') loadPlatformSetup();
    if (panelId === 'sv-score')     loadVisibilityScore();
    if (panelId === 'sv-library')   loadContentLibrary();
    if (panelId === 'sv-calendar')  loadContentCalendar();
}

function loadSocialVisibility() {
    const firstBtn = document.querySelector('.social-nav-btn');
    if (firstBtn) showSocialPanel('sv-platforms', firstBtn);
}

// ── Platform Setup ────────────────────────────────────────────────────────

async function loadPlatformSetup() {
    const container = document.getElementById('svPlatformCards');
    if (!container || !authToken) return;
    try {
        const r = await fetch(`${API_BASE_URL}/social/platforms`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const saved = r.ok ? (await r.json()).platforms : [];
        svEnabledPlatforms = saved;   // cache for publish targets
        renderPlatformCards(saved);
    } catch (_) {
        renderPlatformCards([]);
    }
}

function renderPlatformCards(savedConfigs) {
    const container = document.getElementById('svPlatformCards');
    if (!container) return;
    const configMap = {};
    savedConfigs.forEach(c => { configMap[c.platform] = c; });

    container.innerHTML = SV_PLATFORMS.map(p => {
        const saved = configMap[p.key] || {};
        const enabled = saved.enabled || false;
        const autoType = saved.automation_type || 'none';
        const handle = saved.platform_handle || '';
        const automationBadge = autoType === 'api'
            ? `<span class="badge bg-success"><i class="fas fa-bolt me-1"></i>API Connected</span>`
            : autoType === 'browser'
            ? `<span class="badge bg-primary"><i class="fas fa-robot me-1"></i>Browser Automation</span>`
            : p.automatable
            ? `<span class="badge bg-warning text-dark"><i class="fas fa-hand-pointer me-1"></i>Manual (Automation available)</span>`
            : `<span class="badge bg-light text-muted border">Manual only</span>`;

        return `
        <div class="col-md-6 col-lg-3">
          <div class="card border-0 shadow-sm h-100 sv-platform-card ${enabled ? 'border-start border-3' : ''}"
               style="${enabled ? `border-color:${p.color}!important;` : 'opacity:0.75;'}" data-platform="${p.key}">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <div class="d-flex align-items-center gap-2">
                  <i class="${p.icon} fa-lg" style="color:${p.color};width:20px;"></i>
                  <span class="fw-semibold small">${p.label}</span>
                </div>
                <div class="form-check form-switch mb-0">
                  <input class="form-check-input sv-platform-toggle" type="checkbox"
                         id="svPlatform_${p.key}" data-platform="${p.key}"
                         ${enabled ? 'checked' : ''}
                         onchange="togglePlatformCard(this)">
                </div>
              </div>
              <div class="text-muted mb-2" style="font-size:0.72rem;">${p.desc}</div>
              <div class="mb-2">${automationBadge}</div>
              <div class="sv-platform-details ${enabled ? '' : 'd-none'}" id="svPlatformDetails_${p.key}">
                <input type="text" class="form-control form-control-sm mt-2 sv-platform-handle"
                       data-platform="${p.key}"
                       placeholder="@handle or profile URL"
                       value="${handle}">
                ${p.automatable ? `
                <div class="mt-2">
                  <select class="form-select form-select-sm sv-platform-auto" data-platform="${p.key}">
                    <option value="none" ${autoType === 'none' ? 'selected' : ''}>Manual posting</option>
                    <option value="browser" ${autoType === 'browser' ? 'selected' : ''}>Browser automation</option>
                    <option value="api" ${autoType === 'api' ? 'selected' : ''}>API (coming soon)</option>
                  </select>
                </div>` : ''}
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
}

function togglePlatformCard(checkbox) {
    const key = checkbox.dataset.platform;
    const details = document.getElementById(`svPlatformDetails_${key}`);
    const card = checkbox.closest('.sv-platform-card');
    const platform = SV_PLATFORMS.find(p => p.key === key);
    if (checkbox.checked) {
        details?.classList.remove('d-none');
        if (platform) {
            card.style.opacity = '1';
            card.classList.add('border-start', 'border-3');
            card.style.borderColor = platform.color + '!important';
        }
    } else {
        details?.classList.add('d-none');
        card.style.opacity = '0.75';
        card.classList.remove('border-start', 'border-3');
    }
}

async function savePlatformConfig() {
    if (!authToken) return;
    const platforms = SV_PLATFORMS.map(p => {
        const enabled = document.getElementById(`svPlatform_${p.key}`)?.checked || false;
        const handle = document.querySelector(`.sv-platform-handle[data-platform="${p.key}"]`)?.value?.trim() || null;
        const autoEl = document.querySelector(`.sv-platform-auto[data-platform="${p.key}"]`);
        const automation_type = autoEl ? autoEl.value : 'none';
        return { platform: p.key, enabled, platform_handle: handle, automation_type };
    });
    try {
        const r = await fetch(`${API_BASE_URL}/social/platforms`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ platforms })
        });
        if (r.ok) showToast('Platform settings saved!', 'success');
        else showToast('Save failed', 'danger');
    } catch (_) { showToast('Save failed', 'danger'); }
}

// ── Platform publishing helpers ───────────────────────────────────────────

// Cached after loadPlatformSetup() runs
let svEnabledPlatforms = [];

// Platform URLs for new-post actions
function getPlatformPublishUrl(platform, contentType) {
    const urls = {
        linkedin:  contentType === 'article' ? 'https://www.linkedin.com/article/new/' : 'https://www.linkedin.com/feed/',
        twitter:   'https://x.com/compose/post',
        medium:    'https://medium.com/new-story',
        instagram: 'https://www.instagram.com/',
        facebook:  'https://www.facebook.com/',
        youtube:   'https://studio.youtube.com/',
    };
    return urls[platform] || null;
}

// Which platforms are relevant for a content type
function getRelevantPlatforms(contentType) {
    const map = {
        post:    ['linkedin', 'twitter', 'instagram', 'facebook'],
        article: ['linkedin', 'medium', 'portfolio'],
        thread:  ['twitter'],
        about_section: ['linkedin', 'github', 'portfolio'],
    };
    return map[contentType] || ['linkedin', 'twitter'];
}

async function renderPublishTargets(containerId, sectionId, contentType) {
    const container = document.getElementById(containerId);
    const section = document.getElementById(sectionId);
    if (!container || !section) return;

    // Use cached platforms, or fetch
    let platforms = svEnabledPlatforms;
    if (!platforms.length && authToken) {
        try {
            const r = await fetch(`${API_BASE_URL}/social/platforms`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (r.ok) {
                const data = await r.json();
                svEnabledPlatforms = data.platforms || [];
                platforms = svEnabledPlatforms;
            }
        } catch (_) {}
    }

    const relevant = getRelevantPlatforms(contentType);
    const enabledRelevant = platforms.filter(p => p.enabled && relevant.includes(p.platform));

    if (!enabledRelevant.length) {
        container.innerHTML = `
            <div class="col-12">
              <div class="alert alert-light border py-2 small mb-0">
                <i class="fas fa-info-circle me-1 text-muted"></i>
                No platforms enabled for this content type.
                <a href="#" class="ms-1" onclick="showSocialPanel('sv-platforms', document.querySelector('[data-panel=sv-platforms]'));return false;">
                  Set up platforms →
                </a>
              </div>
            </div>`;
        section.classList.remove('d-none');
        return;
    }

    const platformMeta = {};
    SV_PLATFORMS.forEach(p => { platformMeta[p.key] = p; });

    container.innerHTML = enabledRelevant.map(cfg => {
        const meta = platformMeta[cfg.platform] || { icon: 'fas fa-globe', color: '#6c757d', label: cfg.platform };
        const publishUrl = cfg.platform_url || getPlatformPublishUrl(cfg.platform, contentType);
        const isAutomatable = cfg.automation_type === 'browser' || cfg.automation_type === 'api';
        const handleLabel = cfg.platform_handle ? `<span class="text-muted" style="font-size:.7rem;">${cfg.platform_handle}</span>` : '';

        return `
        <div class="col-md-6 col-lg-4">
          <div class="card border-0 shadow-sm h-100" style="border-left:3px solid ${meta.color}!important;">
            <div class="card-body p-3">
              <div class="d-flex align-items-center gap-2 mb-2">
                <i class="${meta.icon}" style="color:${meta.color};font-size:1.1rem;width:18px;"></i>
                <span class="fw-semibold small">${meta.label}</span>
                ${handleLabel}
              </div>
              <div class="d-flex gap-2 flex-wrap">
                <button class="btn btn-sm fw-semibold" style="background:${meta.color};color:#fff;font-size:.78rem;"
                  onclick="copyAndOpenPlatform('${cfg.platform}', '${publishUrl || ''}')">
                  <i class="fas fa-external-link-alt me-1"></i>Copy &amp; Open
                </button>
                ${isAutomatable && cfg.platform === 'linkedin'
                    ? `<button class="btn btn-sm btn-outline-primary" style="font-size:.78rem;"
                         onclick="autoPostToPlatform('${cfg.platform}')">
                         <i class="fas fa-robot me-1"></i>Auto-Post
                       </button>`
                    : `<span class="badge bg-light text-muted border align-self-center" style="font-size:.7rem;">
                         <i class="fas fa-robot me-1"></i>Auto-Post: Coming soon
                       </span>`
                }
              </div>
            </div>
          </div>
        </div>`;
    }).join('');

    section.classList.remove('d-none');
}

async function copyAndOpenPlatform(platform, url) {
    // Collect content from whichever editor is active
    const postBody  = document.getElementById('svPostBody')?.value?.trim();
    const artTitle  = document.getElementById('svEditorTitle')?.value?.trim();
    const artBody   = document.getElementById('svEditorBody')?.value?.trim();

    const body  = postBody || artBody || '';
    const title = artTitle || '';

    // Collect hashtags from both possible containers
    const hashtagEls = document.querySelectorAll('#svPostHashtags .badge, #svHashtagsContainer .badge');
    const hashtags = Array.from(hashtagEls)
        .map(b => b.childNodes[0]?.textContent?.trim() || b.textContent.replace('×','').trim())
        .filter(Boolean)
        .map(t => t.startsWith('#') ? t : '#' + t)
        .join(' ');

    const fullContent = [title, body, hashtags].filter(Boolean).join('\n\n').trim();

    try {
        await navigator.clipboard.writeText(fullContent);
        showToast(`✓ Copied! Opening ${platform}… paste your content and post.`, 'success');
    } catch (_) {
        showToast('Could not auto-copy — select and copy the text manually, then open the platform.', 'warning');
    }

    if (url) {
        setTimeout(() => window.open(url, '_blank'), 400);
    }
}

function autoPostToPlatform(platform) {
    if (platform === 'linkedin') {
        showToast('LinkedIn Auto-Post: browser automation will be set up in the next release. Use Copy & Open for now.', 'info');
    } else {
        showToast(`Auto-Post for ${platform} is coming soon.`, 'info');
    }
}

// ── Visibility Score ──────────────────────────────────────────────────────

async function loadVisibilityScore() {
    const el = document.getElementById('svScoreContent');
    if (!el || !authToken) return;
    try {
        const r = await fetch(`${API_BASE_URL}/social/dashboard`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!r.ok) throw new Error('Could not load visibility data');
        const d = await r.json();
        const score = d.visibility_score || 0;
        const color = score >= 70 ? '#198754' : score >= 40 ? '#fd7e14' : '#dc3545';
        const circ = 2 * Math.PI * 54;
        const offset = circ - (score / 100) * circ;

        const platformBars = Object.entries(d.by_platform || {}).map(([p, n]) => `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small text-capitalize">${p}</span>
                <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="width:80px;height:6px;">
                        <div class="progress-bar" style="width:${Math.min(n * 20, 100)}%;background:${color};"></div>
                    </div>
                    <span class="small fw-bold">${n}</span>
                </div>
            </div>`).join('');

        el.innerHTML = `
        <div class="row g-4">
          <div class="col-md-4">
            <div class="card border-0 shadow-sm text-center p-4 h-100">
              <svg viewBox="0 0 120 120" width="140" class="mx-auto mb-3">
                <circle cx="60" cy="60" r="54" fill="none" stroke="#e9ecef" stroke-width="10"/>
                <circle cx="60" cy="60" r="54" fill="none" stroke="${color}" stroke-width="10"
                  stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
                  stroke-linecap="round" transform="rotate(-90 60 60)"/>
                <text x="60" y="65" text-anchor="middle" font-size="26" font-weight="700" fill="${color}">${score}</text>
                <text x="60" y="82" text-anchor="middle" font-size="10" fill="#6c757d">/100</text>
              </svg>
              <div class="fw-bold fs-5">Visibility Score</div>
              <div class="text-muted small mt-1">${score >= 70 ? 'Strong presence' : score >= 40 ? 'Growing — keep publishing' : 'Publish content to build visibility'}</div>
              <div class="text-muted mt-2 px-2" style="font-size:0.7rem;">Score reflects <strong>published</strong> content only — drafts &amp; scheduled do not count</div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card border-0 shadow-sm p-4 h-100">
              <div class="fw-bold mb-3">Content Stats</div>
              ${[['Published', d.published, 'success'], ['Scheduled', d.scheduled, 'primary'],
                 ['Drafts', d.drafts, 'secondary'], ['Topics ready', d.topics_available, 'info']]
                .map(([l, v, c]) => `<div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="small">${l}</span><span class="badge bg-${c} rounded-pill">${v}</span></div>`).join('')}
              ${d.avg_ai_quality_score ? `<div class="small text-muted mt-2">Avg AI quality: <strong>${d.avg_ai_quality_score}/10</strong></div>` : ''}
              ${d.next_scheduled ? `<div class="small text-muted mt-1">Next: <strong>${new Date(d.next_scheduled).toLocaleDateString()}</strong></div>` : ''}
            </div>
          </div>
          <div class="col-md-4">
            <div class="card border-0 shadow-sm p-4 h-100">
              <div class="fw-bold mb-3">By Platform</div>
              ${platformBars || '<div class="text-muted small">No content yet</div>'}
              <div class="mt-3 pt-3 border-top">
                <button class="btn btn-primary btn-sm w-100"
                  onclick="showSocialPanel('sv-article', document.querySelector('[data-panel=sv-article]'))">
                  <i class="fas fa-pen-nib me-1"></i>Write an Article
                </button>
              </div>
            </div>
          </div>
        </div>`;
    } catch (e) {
        el.innerHTML = `<div class="alert alert-warning">${e.message}</div>`;
    }
}

// ── Topics ────────────────────────────────────────────────────────────────

async function suggestTopics() {
    const grid = document.getElementById('svTopicsGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="col-12 text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>AI is generating topics from your profile…</div>';
    try {
        const r = await fetch(`${API_BASE_URL}/social/topics/suggest`, {
            method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!r.ok) throw new Error('Topic generation failed');
        const { topics } = await r.json();
        renderTopicsGrid(topics);
    } catch (e) {
        grid.innerHTML = `<div class="col-12"><div class="alert alert-danger">${e.message}</div></div>`;
    }
}

const CATEGORY_COLORS = {
    thought_leadership: 'primary', how_to: 'success',
    case_study: 'warning', career_story: 'info', industry_insight: 'secondary'
};

function renderTopicsGrid(topics) {
    const grid = document.getElementById('svTopicsGrid');
    if (!grid) return;
    grid.innerHTML = topics.map(t => `
        <div class="col-md-6 col-lg-4">
          <div class="card border-0 shadow-sm topic-card h-100" style="cursor:pointer;transition:all .15s;"
               onclick="selectTopic(${t.id}, '${(t.title || '').replace(/'/g, "\\'")}', this)"
               data-topic-id="${t.id}">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <span class="badge bg-${CATEGORY_COLORS[t.category] || 'secondary'} text-capitalize small">
                  ${(t.category || '').replace(/_/g, ' ')}
                </span>
                <span class="badge bg-light text-dark border small">${t.relevance_score}/10</span>
              </div>
              <div class="fw-semibold small mb-1" style="line-height:1.4;">${t.title}</div>
              <div class="text-muted" style="font-size:0.75rem;line-height:1.4;">${(t.summary || '').substring(0, 110)}…</div>
              <div class="mt-2">
                <span class="badge ${t.source === 'user_provided' ? 'bg-success' : 'bg-light text-dark border'} small">
                  ${t.source === 'user_provided' ? '✓ Your topic' : 'AI suggested'}
                </span>
                ${t.used ? '<span class="badge bg-light text-success border small ms-1">Used</span>' : ''}
              </div>
            </div>
          </div>
        </div>`).join('');
}

function selectTopic(topicId, topicTitle, cardEl) {
    document.querySelectorAll('.topic-card').forEach(c => {
        c.style.borderColor = ''; c.style.boxShadow = ''; c.style.background = '';
    });
    if (cardEl) {
        cardEl.style.borderColor = '#0d6efd';
        cardEl.style.boxShadow = '0 0 0 2px rgba(13,110,253,.25)';
        cardEl.style.background = '#f0f5ff';
    }
    svCurrentTopicId = topicId;
    const badge = document.getElementById('svSelectedTopicBadge');
    if (badge) badge.textContent = topicTitle;
    const fp = document.getElementById('svFormatPanel');
    if (fp) fp.style.removeProperty('display');
    const ct = document.getElementById('svCustomTopic');
    if (ct) ct.value = '';
}

function useCustomTopic() {
    const val = document.getElementById('svCustomTopic')?.value?.trim();
    if (!val) { showToast('Enter a topic first', 'warning'); return; }
    svCurrentTopicId = null;
    document.querySelectorAll('.topic-card').forEach(c => {
        c.style.borderColor = ''; c.style.boxShadow = ''; c.style.background = '';
    });
    const badge = document.getElementById('svSelectedTopicBadge');
    if (badge) badge.textContent = val;
    const fp = document.getElementById('svFormatPanel');
    if (fp) fp.style.removeProperty('display');
}

// ── Article generation ────────────────────────────────────────────────────

async function generateSocialContent() {
    const btn = document.getElementById('svGenerateBtn');
    const customTopic = document.getElementById('svCustomTopic')?.value?.trim();
    if (!svCurrentTopicId && !customTopic) {
        showToast('Select or enter a topic first', 'warning'); return;
    }
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Writing…';
    const platform = document.getElementById('svPlatform')?.value || 'linkedin';
    const contentType = document.getElementById('svContentType')?.value || 'article';
    const tone = document.getElementById('svTone')?.value || 'thought_leader';
    try {
        const r = await fetch(`${API_BASE_URL}/social/content/generate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic_id: svCurrentTopicId || null, custom_topic: customTopic || null, content_type: contentType, platform, tone })
        });
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Generation failed'); }
        const piece = await r.json();
        populateSocialEditor(piece);
        showToast('Content generated!', 'success');
    } catch (e) { showToast(e.message, 'danger'); }
    finally { btn.disabled = false; btn.innerHTML = '<i class="fas fa-brain me-2"></i>Generate with AI'; }
}

function populateSocialEditor(piece) {
    svCurrentPieceId = piece.id;
    document.getElementById('svEditorTitle').value = piece.title || '';
    document.getElementById('svEditorBody').value = piece.body || '';
    document.getElementById('svHookAText').textContent = piece.hook_a || '(no hook A)';
    document.getElementById('svHookBText').textContent = piece.hook_b || '(no hook B)';
    const sb = document.getElementById('svAiScoreBadge');
    if (piece.ai_score) { sb.textContent = `AI Score: ${piece.ai_score}/10`; sb.style.display = 'inline'; }
    const wb = document.getElementById('svWordCountBadge');
    if (piece.word_count) wb.textContent = `${piece.word_count} words`;
    const rb = document.getElementById('svReadTimeBadge');
    if (piece.estimated_read_minutes) rb.textContent = `~${piece.estimated_read_minutes} min read`;
    const hc = document.getElementById('svHashtagsContainer');
    hc.innerHTML = '';
    (piece.hashtags || []).forEach(tag => addHashtagChip(tag));
    const fb = document.getElementById('svAiFeedback');
    if (piece.ai_feedback) { fb.textContent = '💡 ' + piece.ai_feedback; fb.style.display = 'block'; }
    document.getElementById('svHookA').classList.remove('border-primary', 'bg-primary');
    document.getElementById('svHookB').classList.remove('border-primary', 'bg-primary');
    // Hide publish section until re-rendered for this piece
    const artPub = document.getElementById('svArticlePublishSection');
    if (artPub) artPub.classList.add('d-none');
    renderPublishTargets('svArticlePublishTargets', 'svArticlePublishSection', piece.content_type || 'article');
    const ep = document.getElementById('svEditorPanel');
    if (ep) { ep.style.removeProperty('display'); ep.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}

function selectHook(variant) {
    document.getElementById('svHookA').classList.remove('border-primary', 'bg-primary');
    document.getElementById('svHookB').classList.remove('border-primary', 'bg-primary');
    const chosen = variant === 'a'
        ? document.getElementById('svHookAText').textContent
        : document.getElementById('svHookBText').textContent;
    document.getElementById(variant === 'a' ? 'svHookA' : 'svHookB').classList.add('border-primary', 'bg-primary');
    const body = document.getElementById('svEditorBody');
    body.value = chosen + '\n\n' + body.value;
    showToast('Hook applied', 'success');
}

// ── Hashtags ──────────────────────────────────────────────────────────────

function addHashtagChip(tag) {
    const container = document.getElementById('svHashtagsContainer');
    const clean = tag.replace(/^#/, '');
    const chip = document.createElement('span');
    chip.className = 'badge bg-primary rounded-pill d-flex align-items-center gap-1';
    chip.innerHTML = `#${clean} <i class="fas fa-times" style="cursor:pointer;font-size:0.65rem;" onclick="this.parentElement.remove()"></i>`;
    container.appendChild(chip);
}

function addHashtag() {
    const input = document.getElementById('svHashtagInput');
    const val = input?.value?.trim();
    if (!val) return;
    addHashtagChip(val);
    input.value = '';
}

function getHashtags() {
    return Array.from(document.querySelectorAll('#svHashtagsContainer .badge'))
        .map(b => b.textContent.replace('×', '').trim().replace(/^#/, ''));
}

// ── Save / copy / schedule / publish ─────────────────────────────────────

async function saveSocialDraft() {
    if (!svCurrentPieceId) { showToast('Nothing to save', 'warning'); return; }
    const r = await fetch(`${API_BASE_URL}/social/content/${svCurrentPieceId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: document.getElementById('svEditorTitle')?.value, body: document.getElementById('svEditorBody')?.value, hashtags: getHashtags(), status: 'draft' })
    });
    if (r.ok) showToast('Draft saved!', 'success'); else showToast('Save failed', 'danger');
}

function copySocialContent() {
    const title = document.getElementById('svEditorTitle')?.value || '';
    const body = document.getElementById('svEditorBody')?.value || '';
    const tags = getHashtags().map(t => '#' + t).join(' ');
    navigator.clipboard.writeText(`${title}\n\n${body}\n\n${tags}`)
        .then(() => showToast('Copied!', 'success'))
        .catch(() => showToast('Copy failed — select text manually', 'warning'));
}

function scheduleSocialContent() {
    if (!svCurrentPieceId) { showToast('Save draft first', 'warning'); return; }
    svSchedulingPieceId = svCurrentPieceId;
    new bootstrap.Modal(document.getElementById('svScheduleModal')).show();
}

async function confirmSchedule() {
    const dt = document.getElementById('svScheduleDateTime')?.value;
    if (!dt || !svSchedulingPieceId) return;
    await fetch(`${API_BASE_URL}/social/content/${svSchedulingPieceId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'scheduled', scheduled_at: dt })
    });
    bootstrap.Modal.getInstance(document.getElementById('svScheduleModal'))?.hide();
    showToast('Content scheduled!', 'success');
}

async function markSocialPublished() {
    if (!svCurrentPieceId) { showToast('Nothing to mark', 'warning'); return; }
    const url = prompt('Paste the published URL (optional):') || '';
    const r = await fetch(`${API_BASE_URL}/social/content/${svCurrentPieceId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'published', published_at: new Date().toISOString(), published_url: url || null })
    });
    if (r.ok) { showToast('Marked as published!', 'success'); loadVisibilityScore(); }
}

function discardSocialDraft() {
    if (!svCurrentPieceId || !confirm('Discard this draft?')) return;
    fetch(`${API_BASE_URL}/social/content/${svCurrentPieceId}`, {
        method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
    }).then(r => {
        if (r.ok) {
            svCurrentPieceId = null;
            document.getElementById('svEditorPanel').style.display = 'none';
            showToast('Draft discarded', 'secondary');
        }
    });
}

// ── Post Composer ─────────────────────────────────────────────────────────

async function generatePost() {
    const btn = document.getElementById('svPostGenerateBtn');
    const bodyEl = document.getElementById('svPostBody');
    const topic = document.getElementById('svPostTopic')?.value?.trim();
    if (!topic) { showToast('Enter a topic first', 'warning'); return; }
    if (!authToken) { showToast('Please log in first', 'danger'); return; }
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Writing…';
    if (bodyEl) bodyEl.placeholder = 'Generating your post…';
    const platform = document.getElementById('svPostPlatform')?.value || 'linkedin';
    const tone = document.getElementById('svPostTone')?.value || 'thought_leader';
    try {
        const r = await fetch(`${API_BASE_URL}/social/content/generate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_topic: topic, content_type: 'post', platform, tone })
        });
        if (!r.ok) {
            const errData = await r.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error ${r.status}`);
        }
        const piece = await r.json();
        if (piece.error) throw new Error(piece.error);
        svPostPieceId = piece.id;
        if (bodyEl) {
            bodyEl.value = piece.body || '';
            bodyEl.placeholder = 'Your post will appear here…';
        }
        updatePostCharCount();
        document.getElementById('svPostHashtags').innerHTML = (piece.hashtags || []).map(t => `<span class="badge bg-primary me-1">#${t}</span>`).join('');
        const sb = document.getElementById('svPostScoreBadge');
        if (piece.ai_score) { sb.textContent = `${piece.ai_score}/10`; sb.style.removeProperty('display'); }
        renderPublishTargets('svPostPublishTargets', 'svPostPublishSection', piece.content_type || 'post');
        showToast('Post generated!', 'success');
    } catch (e) {
        console.error('[generatePost] error:', e);
        if (bodyEl) bodyEl.placeholder = '⚠ ' + e.message + ' — check console or try again';
        showToast(e.message, 'danger');
    }
    finally { btn.disabled = false; btn.innerHTML = '<i class="fas fa-brain me-2"></i>Generate Post'; }
}

function updatePostCharCount() {
    const body = document.getElementById('svPostBody')?.value || '';
    const el = document.getElementById('svPostCharCount');
    if (el) el.textContent = `${body.length} chars`;
}

async function savePostDraft() {
    if (!svPostPieceId) { showToast('Generate a post first', 'warning'); return; }
    const r = await fetch(`${API_BASE_URL}/social/content/${svPostPieceId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: document.getElementById('svPostBody')?.value, status: 'draft' })
    });
    if (r.ok) showToast('Post saved!', 'success');
}

function copyPostContent() {
    navigator.clipboard.writeText(document.getElementById('svPostBody')?.value || '')
        .then(() => showToast('Copied!', 'success'))
        .catch(() => showToast('Copy failed', 'warning'));
}

function schedulePost() {
    if (!svPostPieceId) { showToast('Save post first', 'warning'); return; }
    svSchedulingPieceId = svPostPieceId;
    new bootstrap.Modal(document.getElementById('svScheduleModal')).show();
}

async function markPostPublished() {
    if (!svPostPieceId) return;
    const url = prompt('Paste the published URL (optional):') || '';
    await fetch(`${API_BASE_URL}/social/content/${svPostPieceId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'published', published_at: new Date().toISOString(), published_url: url || null })
    });
    showToast('Marked as published!', 'success');
}

// ── Content Library ───────────────────────────────────────────────────────

async function loadContentLibrary() {
    const el = document.getElementById('svLibraryContent');
    if (!el || !authToken) return;
    el.innerHTML = '<div class="text-center py-4 text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Loading…</div>';
    const status = document.getElementById('svLibraryFilter')?.value || '';
    const platform = document.getElementById('svLibraryPlatform')?.value || '';
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (platform) params.set('platform', platform);
    try {
        const r = await fetch(`${API_BASE_URL}/social/content?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!r.ok) throw new Error('Could not load content');
        const { content } = await r.json();
        if (!content.length) {
            el.innerHTML = '<div class="text-center py-5 text-muted"><i class="fas fa-layer-group fa-3x mb-3 d-block"></i>No content yet — write your first article!</div>';
            return;
        }
        const SC = { draft: 'secondary', approved: 'info', scheduled: 'primary', published: 'success' };
        el.innerHTML = '<div class="row g-3">' + content.map(p => `
            <div class="col-12"><div class="card border-0 shadow-sm"><div class="card-body py-3">
              <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1 me-3">
                  <div class="fw-semibold">${p.title}</div>
                  <div class="small text-muted mt-1">
                    <span class="badge bg-${SC[p.status] || 'secondary'} me-2">${p.status}</span>
                    <span class="badge bg-light text-dark border me-2">${p.platform}</span>
                    <span class="badge bg-light text-dark border me-2">${p.content_type}</span>
                    ${p.word_count ? `<span class="text-muted">${p.word_count}w</span>` : ''}
                    ${p.ai_score ? `<span class="ms-2 text-success">★ ${p.ai_score}/10</span>` : ''}
                    ${p.scheduled_at ? `<span class="ms-2"><i class="fas fa-clock me-1"></i>${new Date(p.scheduled_at).toLocaleDateString()}</span>` : ''}
                    ${p.published_url ? `<a href="${p.published_url}" target="_blank" class="ms-2 text-primary small"><i class="fas fa-external-link-alt me-1"></i>View</a>` : ''}
                  </div>
                </div>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-primary" onclick="openContentEditor(${p.id})"><i class="fas fa-edit"></i></button>
                  <button class="btn btn-sm btn-outline-secondary" onclick="copyLibraryContent(${p.id})"><i class="fas fa-copy"></i></button>
                  <button class="btn btn-sm btn-outline-danger" onclick="deleteLibraryContent(${p.id})"><i class="fas fa-trash"></i></button>
                </div>
              </div>
              ${p.body ? `<div class="small text-muted mt-2 border-top pt-2" style="max-height:55px;overflow:hidden;">${p.body.substring(0, 200)}…</div>` : ''}
            </div></div></div>`).join('') + '</div>';
    } catch (e) { el.innerHTML = `<div class="alert alert-warning">${e.message}</div>`; }
}

async function openContentEditor(pieceId) {
    const r = await fetch(`${API_BASE_URL}/social/content/${pieceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
    if (!r.ok) { showToast('Could not load content', 'danger'); return; }
    const piece = await r.json();
    showSocialPanel('sv-article', document.querySelector('[data-panel="sv-article"]'));
    const fp = document.getElementById('svFormatPanel');
    if (fp) fp.style.removeProperty('display');
    populateSocialEditor(piece);
}

async function copyLibraryContent(pieceId) {
    const r = await fetch(`${API_BASE_URL}/social/content/${pieceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
    if (!r.ok) return;
    const p = await r.json();
    navigator.clipboard.writeText(`${p.title}\n\n${p.body || ''}\n\n${(p.hashtags || []).map(t => '#' + t).join(' ')}`)
        .then(() => showToast('Copied!', 'success'));
}

async function deleteLibraryContent(pieceId) {
    if (!confirm('Delete this content piece?')) return;
    const r = await fetch(`${API_BASE_URL}/social/content/${pieceId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });
    if (r.ok) { showToast('Deleted', 'secondary'); loadContentLibrary(); }
}

// ── Content Calendar ──────────────────────────────────────────────────────

async function loadContentCalendar() {
    const el = document.getElementById('svCalendarContent');
    if (!el || !authToken) return;
    try {
        const r = await fetch(`${API_BASE_URL}/social/content`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!r.ok) throw new Error('Could not load content');
        const { content } = await r.json();
        const items = content.filter(p => p.scheduled_at || p.status === 'published');
        if (!items.length) {
            el.innerHTML = '<div class="text-center py-5 text-muted"><i class="fas fa-calendar-alt fa-3x mb-3 d-block"></i>No scheduled content yet.<br>Schedule an article or post to see it here.</div>';
            return;
        }
        const SC = { draft: '#6c757d', approved: '#0dcaf0', scheduled: '#0d6efd', published: '#198754' };
        el.innerHTML = '<div class="list-group">' + items
            .sort((a, b) => new Date(a.scheduled_at || a.published_at || a.created_at) - new Date(b.scheduled_at || b.published_at || b.created_at))
            .map(p => {
                const dt = p.scheduled_at || p.published_at;
                const d = dt ? new Date(dt) : null;
                const dateStr = d ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
                const timeStr = d ? d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
                return `<div class="list-group-item border-0 shadow-sm mb-2 rounded-2 d-flex gap-3 align-items-center">
                  <div class="text-center" style="min-width:60px;">
                    <div class="fw-bold fs-5" style="color:${SC[p.status] || '#6c757d'}">${dateStr.split(' ')[0]}</div>
                    <div class="small text-muted">${dateStr.split(' ').slice(1).join(' ')}</div>
                    <div class="small text-muted">${timeStr}</div>
                  </div>
                  <div class="flex-grow-1">
                    <div class="fw-semibold">${p.title}</div>
                    <div class="small text-muted">
                      <span class="badge me-1" style="background:${SC[p.status] || '#6c757d'}">${p.status}</span>
                      ${p.platform} · ${p.content_type}
                      ${p.published_url ? `<a href="${p.published_url}" target="_blank" class="ms-2"><i class="fas fa-external-link-alt"></i></a>` : ''}
                    </div>
                  </div>
                  <button class="btn btn-sm btn-outline-primary" onclick="openContentEditor(${p.id})"><i class="fas fa-edit"></i></button>
                </div>`;
            }).join('') + '</div>';
    } catch (e) { el.innerHTML = `<div class="alert alert-warning">${e.message}</div>`; }
}

// ── LinkedIn Profile Audit (placeholder) ─────────────────────────────────

function openLinkedInAudit() {
    showToast('LinkedIn Profile Audit — launching as a standalone feature shortly!', 'info');
}

// ── Window exports ────────────────────────────────────────────────────────

window.loadSocialVisibility  = loadSocialVisibility;
window.showSocialPanel       = showSocialPanel;
window.loadPlatformSetup     = loadPlatformSetup;
window.savePlatformConfig    = savePlatformConfig;
window.togglePlatformCard    = togglePlatformCard;
window.copyAndOpenPlatform   = copyAndOpenPlatform;
window.autoPostToPlatform    = autoPostToPlatform;
window.renderPublishTargets  = renderPublishTargets;
window.suggestTopics         = suggestTopics;
window.useCustomTopic        = useCustomTopic;
window.selectTopic           = selectTopic;
window.generateSocialContent = generateSocialContent;
window.selectHook            = selectHook;
window.addHashtag            = addHashtag;
window.saveSocialDraft       = saveSocialDraft;
window.copySocialContent     = copySocialContent;
window.scheduleSocialContent = scheduleSocialContent;
window.confirmSchedule       = confirmSchedule;
window.markSocialPublished   = markSocialPublished;
window.discardSocialDraft    = discardSocialDraft;
window.generatePost          = generatePost;
window.updatePostCharCount   = updatePostCharCount;
window.savePostDraft         = savePostDraft;
window.copyPostContent       = copyPostContent;
window.schedulePost          = schedulePost;
window.markPostPublished     = markPostPublished;
window.loadContentLibrary    = loadContentLibrary;
window.openContentEditor     = openContentEditor;
window.copyLibraryContent    = copyLibraryContent;
window.deleteLibraryContent  = deleteLibraryContent;
window.loadContentCalendar   = loadContentCalendar;
window.openLinkedInAudit     = openLinkedInAudit;
