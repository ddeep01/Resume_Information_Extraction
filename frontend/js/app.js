/**
 * RecruiterAI - Web UI Application Logic
 */

const API_BASE = "/api";

// State
let currentSessionId = null;
let currentCandidates = [];
let statusPollInterval = null;

// DOM Elements
const views = {
    dashboard: document.getElementById('page-dashboard'),
    createSession: document.getElementById('page-create-session'),
    processing: document.getElementById('page-processing'),
    results: document.getElementById('page-results')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupWeightSliders();
    setupUploadDropzone();
    setupFormSubmission();
    setupFilters();
    loadDashboardSessions();
});

// View Navigation
function switchView(targetView) {
    Object.keys(views).forEach(key => {
        if (key === targetView) {
            views[key].classList.add('active');
        } else {
            views[key].classList.remove('active');
        }
    });

    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    if (targetView === 'dashboard') {
        document.getElementById('nav-dashboard').classList.add('active');
        loadDashboardSessions();
    }
}

function setupNavigation() {
    document.getElementById('btn-brand').addEventListener('click', () => switchView('dashboard'));
    document.getElementById('nav-dashboard').addEventListener('click', () => switchView('dashboard'));
    document.getElementById('nav-create-session').addEventListener('click', () => switchView('createSession'));
    document.getElementById('btn-create-session').addEventListener('click', () => switchView('createSession'));
    document.getElementById('btn-cancel-create').addEventListener('click', () => switchView('dashboard'));
    document.getElementById('btn-refresh-sessions').addEventListener('click', () => loadDashboardSessions());
    document.getElementById('btn-back-dashboard').addEventListener('click', () => switchView('dashboard'));
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-close-modal-footer').addEventListener('click', closeModal);
}

// --------------------------------------------------------------------------
// 1. DASHBOARD LOGIC
// --------------------------------------------------------------------------
async function loadDashboardSessions() {
    try {
        const res = await fetch(`${API_BASE}/sessions`);
        if (!res.ok) throw new Error("Failed to load sessions");
        const sessions = await res.json();

        renderDashboardSessions(sessions);
    } catch (err) {
        showToast("Error loading recruitment sessions: " + err.message, "error");
    }
}

function renderDashboardSessions(sessions) {
    const tbody = document.getElementById('tbody-sessions');
    tbody.innerHTML = '';

    let totalResumes = 0;
    let totalShortlisted = 0;

    document.getElementById('stat-total-sessions').textContent = sessions.length;

    if (sessions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-8 text-muted">
                    <i class="fa-solid fa-folder-open fa-2x"></i>
                    <p class="mt-2">No recruitment sessions found. Click "Create Recruitment Session" to start!</p>
                </td>
            </tr>`;
        document.getElementById('stat-total-resumes').textContent = '0';
        document.getElementById('stat-total-shortlisted').textContent = '0';
        return;
    }

    sessions.forEach(s => {
        totalResumes += s.processed_candidates || 0;
        totalShortlisted += s.shortlisted_candidates || 0;

        const dateStr = s.created_at ? new Date(s.created_at).toLocaleDateString() : 'N/A';
        
        let statusBadge = `<span class="badge badge-eligible">${s.processing_status}</span>`;
        if (s.processing_status === 'COMPLETED') {
            statusBadge = `<span class="badge badge-shortlisted"><i class="fa-solid fa-check"></i> Completed</span>`;
        } else if (s.processing_status === 'PROCESSING') {
            statusBadge = `<span class="badge badge-processing"><i class="fa-solid fa-spinner fa-spin"></i> Processing</span>`;
        } else if (s.processing_status === 'FAILED') {
            statusBadge = `<span class="badge badge-ineligible"><i class="fa-solid fa-xmark"></i> Failed</span>`;
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.session_id}</strong></td>
            <td><strong>${escapeHtml(s.job_title)}</strong></td>
            <td>${escapeHtml(s.required_degree)}</td>
            <td>${s.minimum_experience} yrs</td>
            <td>${s.top_n}</td>
            <td>${s.total_candidates || 0}</td>
            <td><strong class="text-emerald">${s.shortlisted_candidates || 0}</strong></td>
            <td>${statusBadge}</td>
            <td>${dateStr}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="openSessionResults('${s.session_id}')">
                    <i class="fa-solid fa-eye"></i> View
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('stat-total-resumes').textContent = totalResumes;
    document.getElementById('stat-total-shortlisted').textContent = totalShortlisted;
}

// --------------------------------------------------------------------------
// 2. CREATE SESSION & WEIGHTS LOGIC
// --------------------------------------------------------------------------
function setupWeightSliders() {
    const sEdu = document.getElementById('weight_education');
    const sPub = document.getElementById('weight_publication');
    const sAcad = document.getElementById('weight_academic');
    const sInd = document.getElementById('weight_industry');

    const updateWeights = () => {
        document.getElementById('weight-edu-val').textContent = `${sEdu.value}%`;
        document.getElementById('weight-pub-val').textContent = `${sPub.value}%`;
        document.getElementById('weight-acad-val').textContent = `${sAcad.value}%`;
        document.getElementById('weight-ind-val').textContent = `${sInd.value}%`;

        const total = parseInt(sEdu.value) + parseInt(sPub.value) + parseInt(sAcad.value) + parseInt(sInd.value);
        const badge = document.getElementById('weight-total-indicator');
        badge.textContent = `Total: ${total}%`;
        if (total === 100) {
            badge.classList.remove('error');
        } else {
            badge.classList.add('error');
        }
    };

    [sEdu, sPub, sAcad, sInd].forEach(s => s.addEventListener('input', updateWeights));
}

function setupUploadDropzone() {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('zip_file_input');
    const browseBtn = document.getElementById('btn-browse-file');
    const fileNameDiv = document.getElementById('selected-file-name');

    browseBtn.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('click', (e) => {
        if (e.target !== browseBtn) fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDiv.textContent = `Selected: ${fileInput.files[0].name} (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
            fileNameDiv.classList.remove('hidden');
        }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files.length > 0) {
            fileInput.files = dt.files;
            fileNameDiv.textContent = `Selected: ${dt.files[0].name} (${(dt.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
            fileNameDiv.classList.remove('hidden');
        }
    });
}

function setupFormSubmission() {
    const form = document.getElementById('form-create-session');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const sEdu = parseInt(document.getElementById('weight_education').value);
        const sPub = parseInt(document.getElementById('weight_publication').value);
        const sAcad = parseInt(document.getElementById('weight_academic').value);
        const sInd = parseInt(document.getElementById('weight_industry').value);

        if (sEdu + sPub + sAcad + sInd !== 100) {
            showToast("Scoring weights must sum to exactly 100%", "error");
            return;
        }

        const fileInput = document.getElementById('zip_file_input');
        if (!fileInput.files || fileInput.files.length === 0) {
            showToast("Please select a ZIP file containing candidate resumes", "error");
            return;
        }

        const btnSubmit = document.getElementById('btn-submit-session');
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Creating Session & Uploading ZIP...`;

        try {
            // 1. Create Session
            const sessionPayload = {
                job_title: document.getElementById('job_title').value,
                job_description: document.getElementById('job_description').value,
                required_degree: document.getElementById('required_degree').value,
                required_specialization: document.getElementById('required_specialization').value,
                minimum_experience: parseFloat(document.getElementById('minimum_experience').value),
                minimum_publications: parseInt(document.getElementById('minimum_publications').value),
                publication_window_years: parseInt(document.getElementById('publication_window_years').value),
                top_n: parseInt(document.getElementById('top_n').value),
                scoring_weights: {
                    education: sEdu / 100.0,
                    publication: sPub / 100.0,
                    academic_experience: sAcad / 100.0,
                    industry_experience: sInd / 100.0
                }
            };

            const createRes = await fetch(`${API_BASE}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sessionPayload)
            });
            if (!createRes.ok) throw new Error("Failed to create session");
            const sessionData = await createRes.json();
            currentSessionId = sessionData.session_id;

            // 2. Upload ZIP
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const uploadRes = await fetch(`${API_BASE}/sessions/${currentSessionId}/upload`, {
                method: 'POST',
                body: formData
            });
            if (!uploadRes.ok) throw new Error("Failed to upload ZIP file");

            // 3. Trigger Start Processing
            const startRes = await fetch(`${API_BASE}/sessions/${currentSessionId}/start`, {
                method: 'POST'
            });
            if (!startRes.ok) throw new Error("Failed to start processing job");

            showToast(`Session ${currentSessionId} created! Processing started.`, "success");
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = `<i class="fa-solid fa-play"></i> START SHORTLISTING & PROCESSING`;

            // Transition to Processing View
            startProcessingMonitor(currentSessionId);

        } catch (err) {
            showToast("Error creating session: " + err.message, "error");
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = `<i class="fa-solid fa-play"></i> START SHORTLISTING & PROCESSING`;
        }
    });
}

// --------------------------------------------------------------------------
// 3. PROCESSING MONITOR LOGIC
// --------------------------------------------------------------------------
function startProcessingMonitor(sessionId) {
    currentSessionId = sessionId;
    switchView('processing');
    document.getElementById('proc-session-title').textContent = `Session: ${sessionId}`;
    document.getElementById('proc-action-bar').classList.add('hidden');

    if (statusPollInterval) clearInterval(statusPollInterval);

    pollProcessingStatus();
    statusPollInterval = setInterval(pollProcessingStatus, 2000);

    document.getElementById('btn-view-results').onclick = () => {
        openSessionResults(sessionId);
    };
}

async function pollProcessingStatus() {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`${API_BASE}/sessions/${currentSessionId}/status`);
        if (!res.ok) return;
        const data = await res.json();

        // Update UI
        const pct = data.percentage || 0;
        document.getElementById('proc-percentage-text').textContent = `${Math.round(pct)}%`;
        document.getElementById('proc-bar-fill').style.width = `${pct}%`;
        
        // Conic gradient background for circular spinner
        const circle = document.getElementById('progress-circle-element');
        circle.style.background = `conic-gradient(var(--primary) ${pct}%, var(--bg-input) ${pct}%)`;

        document.getElementById('proc-stage-badge').textContent = data.stage || data.status;
        document.getElementById('proc-stat-total').textContent = data.total || 0;
        document.getElementById('proc-stat-processed').textContent = data.processed || 0;
        document.getElementById('proc-stat-failed').textContent = data.failed || 0;

        document.getElementById('proc-detail-msg').textContent = `Stage: ${data.stage}. Processed ${data.processed} of ${data.total} resumes...`;

        if (data.status === 'COMPLETED') {
            clearInterval(statusPollInterval);
            document.getElementById('proc-detail-msg').textContent = `Processing complete! Shortlisted ${data.shortlisted} candidates out of ${data.total}.`;
            document.getElementById('proc-action-bar').classList.remove('hidden');
            showToast("Resume shortlisting completed successfully!", "success");
        } else if (data.status === 'FAILED') {
            clearInterval(statusPollInterval);
            document.getElementById('proc-detail-msg').textContent = `Processing failed. ${data.error_message || ''}`;
            showToast("Processing job failed", "error");
        }
    } catch (err) {
        console.error("Status polling error:", err);
    }
}

// --------------------------------------------------------------------------
// 4. CANDIDATE RESULTS LOGIC
// --------------------------------------------------------------------------
async function openSessionResults(sessionId) {
    currentSessionId = sessionId;
    if (statusPollInterval) clearInterval(statusPollInterval);
    switchView('results');

    try {
        const sessionRes = await fetch(`${API_BASE}/sessions/${sessionId}`);
        if (!sessionRes.ok) throw new Error("Failed to fetch session detail");
        const sessionData = await sessionRes.json();

        document.getElementById('res-session-id').textContent = sessionData.session_id;
        document.getElementById('res-job-title').textContent = sessionData.job_title;
        document.getElementById('res-session-meta').textContent = `Required ${sessionData.required_degree} in ${sessionData.required_specialization} | Min ${sessionData.minimum_experience} Yrs Exp | Min ${sessionData.minimum_publications} Pubs`;

        loadCandidatesList();
    } catch (err) {
        showToast("Error opening session results: " + err.message, "error");
    }
}

async function loadCandidatesList() {
    if (!currentSessionId) return;

    const search = document.getElementById('search-candidate').value;
    const status = document.getElementById('filter-status').value;
    const sortBy = document.getElementById('sort-by').value;

    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status) params.append('status', status);
    if (sortBy) params.append('sort_by', sortBy);

    try {
        const res = await fetch(`${API_BASE}/sessions/${currentSessionId}/candidates?${params.toString()}`);
        if (!res.ok) throw new Error("Failed to load candidates");
        const data = await res.json();

        currentCandidates = data.candidates;

        document.getElementById('res-stat-total').textContent = data.total;
        document.getElementById('res-stat-eligible').textContent = data.eligible_count;
        document.getElementById('res-stat-shortlisted').textContent = data.shortlisted_count;

        renderCandidatesTable(data.candidates);
    } catch (err) {
        showToast("Error loading candidates: " + err.message, "error");
    }
}

function renderCandidatesTable(candidates) {
    const tbody = document.getElementById('tbody-candidates');
    tbody.innerHTML = '';

    if (!candidates || candidates.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="12" class="text-center py-8 text-muted">
                    <i class="fa-solid fa-user-slash fa-2x"></i>
                    <p class="mt-2">No candidate profiles match current filters.</p>
                </td>
            </tr>`;
        return;
    }

    candidates.forEach(cand => {
        const s = cand.shortlisting;
        const p = cand.personal_information;

        let statusBadge = `<span class="badge badge-ineligible">INELIGIBLE</span>`;
        if (s.shortlisted) {
            statusBadge = `<span class="badge badge-shortlisted"><i class="fa-solid fa-star"></i> SHORTLISTED</span>`;
        } else if (s.eligible) {
            statusBadge = `<span class="badge badge-eligible">ELIGIBLE</span>`;
        }

        const rankDisplay = s.rank ? `#${s.rank}` : '-';

        // Extract highest degree & exp
        const highestEdu = cand.education && cand.education.length > 0 ? cand.education[0].degree : 'N/A';
        const spec = cand.education && cand.education.length > 0 ? (cand.education[0].stream || 'N/A') : 'N/A';
        
        const totalExpYears = ((cand.experience.academic || []).reduce((a, b) => a + (b.duration_years || 0), 0) +
                              (cand.experience.industry || []).reduce((a, b) => a + (b.duration_years || 0), 0)).toFixed(1);

        const pubCount = cand.publications ? cand.publications.length : 0;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${rankDisplay}</strong></td>
            <td>
                <div class="font-semibold">${escapeHtml(p.full_name || 'Candidate')}</div>
                <div class="text-xs text-muted">${escapeHtml(p.email || '')}</div>
            </td>
            <td>${escapeHtml(p.current_designation || 'N/A')}</td>
            <td><span class="badge badge-tier1">${escapeHtml(highestEdu)}</span></td>
            <td>${escapeHtml(spec)}</td>
            <td>${totalExpYears} yrs</td>
            <td>${pubCount}</td>
            <td>${(s.education_score * 100).toFixed(0)}</td>
            <td>${(s.publication_score * 100).toFixed(0)}</td>
            <td><strong class="text-emerald text-base">${s.final_score.toFixed(1)}</strong></td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="openCandidateModal('${cand.candidate_id}')">
                    <i class="fa-solid fa-id-card"></i> Profile
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function setupFilters() {
    document.getElementById('search-candidate').addEventListener('input', debounce(loadCandidatesList, 300));
    document.getElementById('filter-status').addEventListener('change', loadCandidatesList);
    document.getElementById('sort-by').addEventListener('change', loadCandidatesList);
}

// --------------------------------------------------------------------------
// 5. CANDIDATE DETAIL MODAL LOGIC
// --------------------------------------------------------------------------
function openCandidateModal(candidateId) {
    const cand = currentCandidates.find(c => c.candidate_id === candidateId);
    if (!cand) return;

    const p = cand.personal_information;
    const s = cand.shortlisting;

    // Header & Initials Avatar
    const initials = (p.full_name || 'C').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    document.getElementById('modal-cand-avatar').textContent = initials;
    document.getElementById('modal-cand-name').textContent = p.full_name || 'Candidate Profile';
    document.getElementById('modal-cand-desig').textContent = p.current_designation || 'Designation N/A';

    // Status Banner & Final Score
    const banner = document.getElementById('modal-status-banner');
    const badge = document.getElementById('modal-cand-status-badge');
    badge.className = 'badge badge-lg ';
    if (s.shortlisted) {
        badge.classList.add('badge-shortlisted');
        badge.innerHTML = `<i class="fa-solid fa-star"></i> SHORTLISTED`;
    } else if (s.eligible) {
        badge.classList.add('badge-eligible');
        badge.innerHTML = `ELIGIBLE`;
    } else {
        badge.classList.add('badge-ineligible');
        badge.innerHTML = `INELIGIBLE`;
    }

    document.getElementById('modal-cand-rank-text').textContent = s.rank ? `Ranked #${s.rank} among eligible candidates` : `Criteria not satisfied`;
    document.getElementById('modal-cand-final-score').textContent = s.final_score.toFixed(1);

    // Personal Info
    document.getElementById('modal-cand-email').textContent = p.email || 'N/A';
    document.getElementById('modal-cand-phone').textContent = p.phone || 'N/A';
    document.getElementById('modal-cand-file').textContent = cand.source_file;
    document.getElementById('modal-cand-id').textContent = cand.candidate_id;

    // Reasons List
    const reasonsUl = document.getElementById('modal-cand-reasons');
    reasonsUl.innerHTML = '';
    (s.reasons || []).forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        reasonsUl.appendChild(li);
    });

    // Component Score Bars
    const eduPct = Math.round(s.education_score * 100);
    const pubPct = Math.round(s.publication_score * 100);
    const acadPct = Math.round(s.academic_experience_score * 100);
    const indPct = Math.round(s.industry_experience_score * 100);

    document.getElementById('modal-score-edu').textContent = `${eduPct} / 100`;
    document.getElementById('modal-bar-edu').style.width = `${eduPct}%`;

    document.getElementById('modal-score-pub').textContent = `${pubPct} / 100`;
    document.getElementById('modal-bar-pub').style.width = `${pubPct}%`;

    document.getElementById('modal-score-acad').textContent = `${acadPct} / 100`;
    document.getElementById('modal-bar-acad').style.width = `${acadPct}%`;

    document.getElementById('modal-score-ind').textContent = `${indPct} / 100`;
    document.getElementById('modal-bar-ind').style.width = `${indPct}%`;

    // Education Table
    const tbodyEdu = document.getElementById('modal-tbody-education');
    tbodyEdu.innerHTML = '';
    (cand.education || []).forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(e.qualification_type || 'N/A')}</strong></td>
            <td>${escapeHtml(e.degree || 'N/A')}</td>
            <td>${escapeHtml(e.stream || 'N/A')}</td>
            <td>${escapeHtml(e.university || 'N/A')}</td>
            <td>${escapeHtml(e.year || 'N/A')}</td>
            <td><span class="badge ${e.institution_tier === 'Tier 1' ? 'badge-tier1' : 'badge-tier2'}">${escapeHtml(e.institution_tier || 'Tier 3')}</span></td>
        `;
        tbodyEdu.appendChild(tr);
    });

    // Publications Table
    const tbodyPub = document.getElementById('modal-tbody-publications');
    tbodyPub.innerHTML = '';
    (cand.publications || []).forEach(pub => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="badge badge-eligible">${escapeHtml(pub.publication_type || 'other')}</span></td>
            <td>${escapeHtml(pub.publication_name || 'Untitled Paper')}</td>
            <td>${escapeHtml(pub.venue_name || 'N/A')}</td>
            <td>${pub.publication_year || 'N/A'}</td>
            <td><span class="badge ${pub.venue_tier === 'Tier 1' ? 'badge-tier1' : 'badge-tier2'}">${escapeHtml(pub.venue_tier || 'Tier 3')}</span></td>
        `;
        tbodyPub.appendChild(tr);
    });

    // Academic Experience
    const listAcad = document.getElementById('modal-list-academic');
    listAcad.innerHTML = '';
    const acads = cand.experience.academic || [];
    if (acads.length === 0) listAcad.innerHTML = '<p class="text-muted">No academic experience listed.</p>';
    acads.forEach(a => {
        const div = document.createElement('div');
        div.className = 'mini-stat';
        div.innerHTML = `
            <div class="font-semibold">${escapeHtml(a.role || 'Role N/A')} at ${escapeHtml(a.institution || 'Institute')}</div>
            <div class="text-xs text-muted">${a.duration_years} yrs | <span class="badge badge-tier1">${a.institution_tier || 'Tier 3'}</span></div>
        `;
        listAcad.appendChild(div);
    });

    // Industry Experience
    const listInd = document.getElementById('modal-list-industry');
    listInd.innerHTML = '';
    const inds = cand.experience.industry || [];
    if (inds.length === 0) listInd.innerHTML = '<p class="text-muted">No industry experience listed.</p>';
    inds.forEach(i => {
        const div = document.createElement('div');
        div.className = 'mini-stat';
        div.innerHTML = `
            <div class="font-semibold">${escapeHtml(i.role || 'Role N/A')} at ${escapeHtml(i.organization || 'Company')}</div>
            <div class="text-xs text-muted">${i.duration_years} yrs ${i.location ? '| ' + escapeHtml(i.location) : ''}</div>
        `;
        listInd.appendChild(div);
    });

    document.getElementById('modal-candidate').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-candidate').classList.add('hidden');
}

// --------------------------------------------------------------------------
// HELPER FUNCTIONS
// --------------------------------------------------------------------------
function showToast(message, type = "info") {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        background: var(--bg-card);
        color: var(--text-primary);
        padding: 0.9rem 1.25rem;
        border-radius: var(--radius-md);
        border: 1px solid ${type === 'error' ? 'var(--red)' : 'var(--primary)'};
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        animation: fadeIn 0.25s ease-out;
    `;
    const icon = type === 'error' ? 'fa-circle-exclamation text-red' : 'fa-circle-check text-emerald';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
