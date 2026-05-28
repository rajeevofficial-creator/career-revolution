// Career Revolution Frontend Application
// Complete working version

// Auto-detect: use same origin in production, localhost:8010 locally
const _isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL = _isLocal ? `http://${window.location.hostname}:8010` : window.location.origin;
const WS_URL      = _isLocal ? `ws://${window.location.hostname}:8010`   : `wss://${window.location.hostname}`;
let authToken = localStorage.getItem('authToken');
let currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
let currentJobFilter = 'recommended'; // Default to My Matches

// ── Global 401 interceptor ────────────────────────────────────────────────
// Any API call that returns 401 automatically clears the stale token and
// prompts the user to re-login instead of showing a cryptic error.
(function installAuthInterceptor() {
    const _fetch = window.fetch;
    window.fetch = async function(url, options) {
        const response = await _fetch(url, options);
        if (response.status === 401 &&
            typeof url === 'string' &&
            url.startsWith(API_BASE_URL) &&
            authToken) {
            // Token expired or invalid — surface it immediately
            handleSessionExpired();
        }
        return response;
    };
})();

let _sessionExpiredFired = false;
let liCurrentPage = 1;
function handleSessionExpired() {
    if (_sessionExpiredFired) return;   // only fire once per expiry event
    _sessionExpiredFired = true;
    authToken = null;
    localStorage.removeItem('authToken');
    showToast('Your session has expired — please log in again', 'warning');
    setTimeout(() => {
        loginModal.show();
        setTimeout(() => { _sessionExpiredFired = false; }, 5000); // reset after 5s
    }, 600);
}

// DOM Elements
const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
const registerModal = new bootstrap.Modal(document.getElementById('registerModal'));
const uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
const sourceModal = new bootstrap.Modal(document.getElementById('sourceModal'));
const toastEl = document.getElementById('liveToast');
const toast = new bootstrap.Toast(toastEl);

// Show login modal
function showLoginModal() {
    registerModal.hide();
    loginModal.show();
}

// Show register modal
function showRegisterModal() {
    loginModal.hide();
    registerModal.show();
}

function showForgotPasswordModal() {
    loginModal.hide();
    document.getElementById('forgotPasswordForm').reset();
    const alert = document.getElementById('forgotPasswordAlert');
    alert.className = 'alert d-none';
    new bootstrap.Modal(document.getElementById('forgotPasswordModal')).show();
}

function showResetPasswordModal(token = '') {
    bootstrap.Modal.getInstance(document.getElementById('forgotPasswordModal'))?.hide();
    const tokenField = document.getElementById('resetToken');
    if (token) {
        tokenField.value = token;
        document.getElementById('resetTokenField').classList.add('d-none');
    } else {
        tokenField.value = '';
        document.getElementById('resetTokenField').classList.remove('d-none');
    }
    document.getElementById('resetPasswordForm').reset();
    if (token) tokenField.value = token; // re-set after form.reset()
    const alert = document.getElementById('resetPasswordAlert');
    alert.className = 'alert d-none';
    new bootstrap.Modal(document.getElementById('resetPasswordModal')).show();
}

async function requestPasswordReset(email) {
    const btn = document.getElementById('forgotPasswordBtn');
    const alert = document.getElementById('forgotPasswordAlert');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sending...';
    try {
        const resp = await fetch(`${API_BASE_URL}/auth/request-password-reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await resp.json();
        alert.className = 'alert alert-success';
        alert.innerHTML = `<i class="fas fa-check-circle me-2"></i>${data.message || 'Reset link sent.'}<br>
            <small class="text-muted">Check your email. In development, the token is also printed in the server console.</small>`;
        // Show "paste token" link prominently after sending
        setTimeout(() => {
            alert.innerHTML += `<div class="mt-2"><a href="#" onclick="showResetPasswordModal()" class="btn btn-sm btn-outline-secondary">
                <i class="fas fa-paste me-1"></i>I have the token — set new password</a></div>`;
        }, 800);
    } catch (e) {
        alert.className = 'alert alert-danger';
        alert.textContent = 'Could not send reset email. Check server is running.';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Send Reset Link';
    }
}

async function resetPassword(token, newPassword, confirmPassword) {
    const btn = document.getElementById('resetPasswordBtn');
    const alert = document.getElementById('resetPasswordAlert');

    if (newPassword !== confirmPassword) {
        alert.className = 'alert alert-danger';
        alert.textContent = 'Passwords do not match.';
        return;
    }
    if (newPassword.length < 8) {
        alert.className = 'alert alert-danger';
        alert.textContent = 'Password must be at least 8 characters.';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Resetting...';
    try {
        const resp = await fetch(`${API_BASE_URL}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token.trim(), new_password: newPassword })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert.className = 'alert alert-success';
            alert.innerHTML = '<i class="fas fa-check-circle me-2"></i>Password reset successfully! You can now log in.';
            setTimeout(() => {
                bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal'))?.hide();
                loginModal.show();
            }, 1800);
        } else {
            alert.className = 'alert alert-danger';
            alert.textContent = data.detail || 'Reset failed. Token may be expired.';
        }
    } catch (e) {
        alert.className = 'alert alert-danger';
        alert.textContent = 'Server error. Please try again.';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check me-2"></i>Set New Password';
    }
}

// Show upload modal
function showUploadModal() {
    if (!authToken) {
        showToast('Please login to upload documents', 'warning');
        showLoginModal();
        return;
    }
    uploadModal.show();
}

// Check API status
async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            document.getElementById('apiStatusDetail').textContent = 'Backend API: Ready';
            document.querySelector('.api-status').className = 'api-status online';
        } else {
            document.getElementById('apiStatusDetail').textContent = 'Backend API: Offline';
            document.querySelector('.api-status').className = 'api-status offline';
        }
    } catch (error) {
        document.getElementById('apiStatusDetail').textContent = 'Backend API: Offline';
        document.querySelector('.api-status').className = 'api-status offline';
    }
}

// Check login status
function checkLoginStatus() {
    if (authToken) {
        // We have a token, but do we have a user?
        if (!currentUser) {
            // Token exists but no user info, fetch it
            loadDashboardData();
        } else {
            // Both exist, update UI then refresh data
            updateUIForLoggedInUser();
            loadDashboardData();
        }
    } else {
        updateUIForGuest();
    }
}

// Update UI for logged in user
function updateUIForLoggedInUser(profileData = null) {
    console.log('Updating UI for logged in user...', profileData);
    
    // Update navigation
    const nav = document.querySelector('.navbar-nav');
    if (nav) {
        // Remove existing login button if present
        const loginBtn = document.getElementById('navLoginBtn');
        if (loginBtn) {
            loginBtn.closest('.nav-item').remove();
        }

        // Remove existing user dropdown if already there (to avoid duplicates)
        const existingDropdown = nav.querySelector('.user-dropdown-item');
        if (existingDropdown) existingDropdown.remove();

        // Add user dropdown
        const userLi = document.createElement('li');
        userLi.className = 'nav-item dropdown user-dropdown-item';
        userLi.innerHTML = `
            <a class="nav-link dropdown-toggle d-flex align-items-center" href="#" role="button" data-bs-toggle="dropdown">
                ${profileData?.profile_picture_url 
                    ? `<img src="${API_BASE_URL}${profileData.profile_picture_url}" class="rounded-circle me-2" style="width: 24px; height: 24px; object-fit: cover;">`
                    : '<i class="fas fa-user-circle me-2"></i>'}
                ${currentUser?.full_name || currentUser?.email || 'User'}
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="#dashboard"><i class="fas fa-tachometer-alt me-2"></i>Dashboard</a></li>
                <li><a class="dropdown-item" href="#documents"><i class="fas fa-file me-2"></i>Documents</a></li>
                <li><a class="dropdown-item" href="#" onclick="showFullProfile(); return false;"><i class="fas fa-user-circle me-2"></i>Profile</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" onclick="clearLocalSession()"><i class="fas fa-trash-alt me-2"></i>Clear Session</a></li>
                <li><a class="dropdown-item" href="#" onclick="logout()"><i class="fas fa-sign-out-alt me-2"></i>Logout</a></li>
            </ul>

        `;
        nav.appendChild(userLi);
    }

    // Update hero section
    const hero = document.getElementById('heroSection');
    if (hero) {
        hero.innerHTML = `
            <div class="container text-center">
                <h1 class="display-4 fw-bold mb-4">Welcome back, ${currentUser?.full_name || 'Career Pro'}!</h1>
                <p class="lead mb-4">Your career transformation journey continues. Upload more documents or check your progress.</p>
                <div class="row justify-content-center">
                    <div class="col-md-10">
                        <div class="d-flex justify-content-center flex-wrap gap-3">
                            <button class="btn btn-primary btn-lg px-4" onclick="showUploadModal()">
                                <i class="fas fa-upload me-2"></i>Upload Documents
                            </button>
                            <button class="btn btn-outline-light btn-lg px-4" onclick="showFullProfile()">
                                <i class="fas fa-user-circle me-2"></i>View Full Profile
                            </button>
                            <button class="btn btn-outline-light btn-lg px-4" onclick="loadDashboardData()">
                                <i class="fas fa-sync-alt me-2"></i>Refresh Dashboard
                            </button>
                            <button class="btn btn-outline-danger btn-lg px-4 bg-white bg-opacity-10" onclick="clearLocalSession()">
                                <i class="fas fa-sync me-2"></i>Clear Session
                            </button>
                            <button class="btn btn-outline-danger btn-lg px-4 bg-white bg-opacity-10" onclick="showResetConfirmModal()">
                                <i class="fas fa-undo me-2"></i>Reset Profile
                            </button>

                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Show main logged in content container and hide hero
    const mainLoggedIn = document.getElementById('mainLoggedInContent');
    
    if (mainLoggedIn) mainLoggedIn.style.display = 'block';
    if (hero) hero.style.display = 'none';

    // Ensure the first tab is active if no tab is selected
    const activeTab = document.querySelector('#mainFeatureTabs .nav-link.active');
    if (!activeTab) {
        const dashboardTab = document.getElementById('tab-dashboard-btn');
        if (dashboardTab) dashboardTab.click();
    }

    // Refresh dashboard visuals
    if (currentUser) {
        const dashName = document.getElementById('dash-user-name');
        if (dashName) dashName.textContent = (currentUser.full_name && currentUser.full_name.trim()) ? currentUser.full_name : (currentUser.email || 'Career Pro');
    }
}

// Helper to switch main tabs with history support
function switchMainTab(tabId, updateHash = true) {
    console.log(`Switching to main tab: ${tabId}`);
    const tabBtn = document.getElementById(`${tabId}-btn`);
    if (tabBtn) {
        // Programmatic click triggers the onclick handler
        tabBtn.click();
        
        // Ensure the bootstrap tab instance actually shows it (in case click doesn't)
        const tabTrigger = bootstrap.Tab.getOrCreateInstance(tabBtn);
        tabTrigger.show();

        if (updateHash) {
            const hash = tabId.replace('tab-', '');
            window.location.hash = hash;
        }
    } else {
        console.warn(`Tab button ${tabId}-btn not found`);
    }
}

// Helper to show full profile and switch to a specific sub-tab
function showFullProfileTab(subTabId) {
    showFullProfile().then(() => {
        const subTabBtn = document.getElementById(`${subTabId}-tab`);
        if (subTabBtn) subTabBtn.click();
    });
}

// Update UI for guest
function updateUIForGuest() {
    // Hide logged in content and show hero
    const mainLoggedIn = document.getElementById('mainLoggedInContent');
    const hero = document.getElementById('heroSection');
    
    if (mainLoggedIn) mainLoggedIn.style.display = 'none';
    if (hero) hero.style.display = 'block';

    // Reset dashboard data
    document.getElementById('docCount').textContent = '0';
    document.getElementById('skillCount').textContent = '0';
    document.getElementById('profileCompletion').textContent = '0%';
    document.getElementById('jobMatches').textContent = '0';
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');

    // Set title based on type
    switch (type) {
        case 'success':
            toastTitle.textContent = 'Success';
            toastTitle.className = 'me-auto text-success';
            break;
        case 'error':
            toastTitle.textContent = 'Error';
            toastTitle.className = 'me-auto text-danger';
            break;
        case 'warning':
            toastTitle.textContent = 'Warning';
            toastTitle.className = 'me-auto text-warning';
            break;
        default:
            toastTitle.textContent = 'Info';
            toastTitle.className = 'me-auto text-info';
    }

    toastMessage.textContent = message;
    toast.show();
}

// Show high-visibility error popup (SweetAlert2)
function showErrorPopup(title, message, icon = 'error') {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: title,
            text: message,
            icon: icon,
            confirmButtonText: 'Understood',
            confirmButtonColor: '#4361ee',
            backdrop: `rgba(0,0,123,0.1)`
        });
    } else {
        // Fallback if Swal didn't load
        alert(`${title}: ${message}`);
    }
}

// Login function
async function login(email, password) {
    try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        // Load dashboard data (which also gets user/profile info)
        await loadDashboardData();

        showToast('Login successful!', 'success');
        loginModal.hide();

        return true;
    } catch (error) {
        showToast(error.message, 'error');
        return false;
    }
}

// Register function
async function register(fullName, email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
                full_name: fullName
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        showToast('Registration successful! Please login.', 'success');
        registerModal.hide();
        showLoginModal();

        return true;
    } catch (error) {
        showToast(error.message, 'error');
        return false;
    }
}

// Get user info
async function getUserInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to get user info');
        }

        const data = await response.json();
        currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));

    } catch (error) {
        console.error('Error getting user info:', error);
    }
}

// Load dashboard data
async function loadDashboardData() {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/dashboard`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load dashboard data');
        }

        const data = await response.json();

        // Update global state
        currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));

        // 1. Update dashboard stats and UI IMMEDIATELY with available data
        document.getElementById('docCount').textContent = data.stats.total_documents;
        document.getElementById('skillCount').textContent = data.stats.total_skills;
        document.getElementById('profileCompletion').textContent = `${data.stats.profile_completion}%`;
        
        // Use mock/cached job match count initially to avoid blocking
        document.getElementById('jobMatches').textContent = data.stats.job_matches || '...';

        // Update documents list
        updateDocumentsList(data.documents);
        
        // Update UI elements (Profile, Header, etc.)
        updateUIForLoggedInUser(data.profile);

        // Update Dashboard Highlights & Alerts
        updateDashboardHighlights(data);

        // 2. Fetch Fresh Job Matches ASYNCHRONOUSLY (Don't await)
        fetch(`${API_BASE_URL}/jobs/search`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        })
        .then(res => res.ok ? res.json() : null)
        .then(jobsData => {
            if (jobsData) {
                document.getElementById('jobMatches').textContent = jobsData.length;
            }
        })
        .catch(e => console.error('Error updating job count:', e));

        // 3. Keep background processes running
        const hasProcessing = data.documents && data.documents.some(doc =>
            doc.processing_status === 'pending' || doc.processing_status === 'processing'
        );
        if (hasProcessing) {
            startPolling();
        }

        // 4. Load auto-apply settings and portal accounts asynchronously
        loadAutoApplySettings().catch(() => {});

    } catch (error) {
        console.error('Error loading dashboard data:', error);
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
            showToast('Session expired. Please login again.', 'warning');
            logout();
        } else {
            showToast('Failed to load dashboard data: ' + error.message, 'error');
        }
        throw error; // Re-throw to inform caller (like login)
    }
}

// Update Dashboard Highlights (New Sections)
function updateDashboardHighlights(data) {
    const highlightContent = document.getElementById('profileHighlightContent');
    if (!highlightContent) return;
    
    renderMasterCV('profileHighlightContent', data);
    syncJobFinderFiltersWithProfile(data.profile);

    const profile = data.profile;
    // 2. Load Preferences if not already set (Quick UI update)

    // 2. Load Preferences if not already set (Quick UI update)
    if (profile) {
        document.getElementById('prefTargetRole').value = profile.desired_job_title || '';
        document.getElementById('prefLocation').value = profile.location || '';

        // Auto-populate country dropdown for Job Sources from profile location
        const countrySelect = document.getElementById('sourceCountrySelect');
        if (countrySelect) {
            const rawLocation = (profile.desired_location || profile.location || '').trim();
            const detectedCountry = rawLocation.includes(',')
                ? rawLocation.split(',').pop().trim()
                : rawLocation;
            if (detectedCountry) {
                // Try to match against existing options (case-insensitive)
                const options = Array.from(countrySelect.options);
                const match = options.find(o => o.value.toLowerCase() === detectedCountry.toLowerCase());
                if (match) countrySelect.value = match.value;
            }
        }
        
        // Job Types (Multi-select)
        if (profile.job_types) {
            let types = [];
            try {
                types = Array.isArray(profile.job_types) ? profile.job_types : JSON.parse(profile.job_types);
            } catch (e) {
                // Fallback for comma-separated strings
                types = typeof profile.job_types === 'string' ? profile.job_types.split(',') : [];
            }
            document.getElementById('typePerm').checked = types.includes('Permanent');
            document.getElementById('typeContract').checked = types.includes('Contract');
        }
        
        // Work Modes (Multi-select)
        if (profile.work_modes) {
            let modes = [];
            try {
                modes = Array.isArray(profile.work_modes) ? profile.work_modes : JSON.parse(profile.work_modes);
            } catch (e) {
                modes = typeof profile.work_modes === 'string' ? profile.work_modes.split(',') : [];
            }
            document.getElementById('modeOnsite').checked = modes.includes('onsite');
            document.getElementById('modeHybrid').checked = modes.includes('hybrid');
            document.getElementById('modeRemote').checked = modes.includes('remote');
        }
        
        // Experience Level
        if (profile.experience_level) {
            document.getElementById('prefExpLevel').value = profile.experience_level;
        }
        
        // Salary
        if (profile.salary_expectation) {
            document.getElementById('prefSalary').value = profile.salary_expectation;
        }
    }

    // 3. Detect Missing Info from 'data' directly
    const missing = [];
    if (!profile?.location) missing.push('location');
    if (!profile?.summary) missing.push('professional summary');
    if ((data.experiences || []).length === 0) missing.push('work history');
    if ((data.skills || []).length === 0) missing.push('skills');
    
    if (missing.length > 0 && data.stats.profile_completion < 90) {
        missingInfoContainer.style.display = 'block';
        missingInfoText.textContent = `Please add your ${missing.slice(0, 2).join(' and ')}${missing.length > 2 ? ' and more' : ''} to reach 100% profile completion.`;
    } else {
        missingInfoContainer.style.display = 'none';
    }
}

// Save Quick Preferences from Dashboard
async function saveQuickPreferences() {
    const targetRole = document.getElementById('prefTargetRole').value;
    const loc = document.getElementById('prefLocation').value;
    const salary = document.getElementById('prefSalary').value;
    const expLevel = document.getElementById('prefExpLevel').value;
    
    // Get multi-select job types
    const jobTypes = [];
    if (document.getElementById('typePerm').checked) jobTypes.push('Permanent');
    if (document.getElementById('typeContract').checked) jobTypes.push('Contract');
    
    // Get multi-select work modes
    const workModes = [];
    if (document.getElementById('modeOnsite').checked) workModes.push('onsite');
    if (document.getElementById('modeHybrid').checked) workModes.push('hybrid');
    if (document.getElementById('modeRemote').checked) workModes.push('remote');

    const btn = document.querySelector('#preferencesForm button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    btn.disabled = true;

    try {
        const data = {
            desired_job_title: targetRole,
            location: loc,
            salary_expectation: salary,
            experience_level: expLevel,
            job_types: JSON.stringify(jobTypes),
            work_modes: JSON.stringify(workModes)
        };

        const result = await saveProfileSection('/profile', data, 'Preferences');

        if (result) {
            showToast('Target preferences saved!', 'success');
        }
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
        loadDashboardData();
    }
}

// Update documents list
function updateDocumentsList(documents) {
    const documentsList = document.getElementById('documentsList');

    if (!documents || documents.length === 0) {
        documentsList.innerHTML = `
            <div class="text-center py-5">
                <p class="text-muted">No documents uploaded yet.</p>
                <button class="btn btn-outline-primary" onclick="showUploadModal()">
                    <i class="fas fa-upload me-2"></i>Upload Your First Document
                </button>
            </div>
        `;
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-hover"><thead><tr><th style="width: 40px;"><input class="form-check-input" type="checkbox" id="selectAllDocs" onchange="toggleSelectAllDocs()"></th><th>Type</th><th>Filename</th><th>Size</th><th>Uploaded</th><th>Status</th><th>Actions</th></tr></thead><tbody>';

    documents.forEach(doc => {
        const fileSize = doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A';
        const uploadDate = new Date(doc.upload_date).toLocaleDateString();

        let statusHtml = '';
        if (doc.is_processed) {
            statusHtml = '<span class="badge bg-success">Processed</span>';
        } else if (doc.processing_status === 'failed') {
            statusHtml = '<span class="badge bg-danger">Failed</span>';
        } else {
            statusHtml = `<span class="badge bg-warning text-dark">${doc.processing_status || 'Pending'}</span>`;
        }

        html += `
            <tr>
                <td><input class="form-check-input doc-checkbox" type="checkbox" value="${doc.id}" onchange="toggleDeleteSelectedBtn()"></td>
                <td><span class="badge bg-primary">${doc.document_type}</span></td>
                <td>${doc.original_filename}</td>
                <td>${fileSize}</td>
                <td>${uploadDate}</td>
                <td>${statusHtml}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewDocument('${doc.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteDocument('${doc.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    documentsList.innerHTML = html;
}

// Toggle upload mode between files and folders
function toggleUploadMode() {
    const fileInput = document.getElementById('fileInput');
    const isFolder = document.getElementById('modeFolder').checked;

    // Clear current selection
    fileInput.value = '';

    if (isFolder) {
        fileInput.setAttribute('webkitdirectory', '');
        fileInput.setAttribute('directory', '');
    } else {
        fileInput.removeAttribute('webkitdirectory');
        fileInput.removeAttribute('directory');
    }
}

// Upload document(s)
async function uploadDocument() {
    if (!authToken) {
        showToast('Please login to upload documents', 'warning');
        showLoginModal();
        return;
    }

    const fileInput = document.getElementById('fileInput');
    const documentType = document.getElementById('documentType').value;

    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select files or a folder', 'warning');
        return;
    }

    const files = Array.from(fileInput.files);
    const allowedTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'image/jpeg',
        'image/png'
    ];

    let successCount = 0;
    let failCount = 0;

    // Change button to show progress
    const uploadBtn = document.querySelector('#uploadModal .btn-primary');
    const originalBtnHtml = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';
    uploadBtn.disabled = true;

    for (const file of files) {
        // Skip hidden/system files often found in folders
        if (file.name.startsWith('.')) continue;

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            failCount++;
            continue;
        }

        // Relaxed type checking for folder uploads (since OS doesn't always provide MIME types)
        const ext = file.name.split('.').pop().toLowerCase();
        const validExtensions = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png'];
        const isMimeValid = file.type ? allowedTypes.includes(file.type) : false;
        const isExtValid = validExtensions.includes(ext);

        // At least one check needs to pass
        if (!isMimeValid && !isExtValid) {
            // Unrecognized extension and type
            continue;
        }

        const formData = new FormData();
        formData.append('document_type', documentType);
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE_URL}/documents/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                },
                body: formData
            });

            if (response.ok) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            failCount++;
        }
    }

    if (successCount > 0) {
        showToast(`Successfully uploaded ${successCount} file(s).` + (failCount > 0 ? ` Failed: ${failCount}` : '') + ` Starting AI Analysis...`, 'success');
        uploadModal.hide();
        fileInput.value = ''; // Clear file input

        // Disable refresh layout while processing
        uploadBtn.innerHTML = '<i class="fas fa-brain fa-spin me-2"></i>Analyzing Base Docs...';
        uploadBtn.disabled = true;

        // Now trigger the backend AI pipeline
        await processUploadedDocuments();

        loadDashboardData(); // Refresh dashboard
    } else {
        showToast('Failed to upload any files. Make sure they are supported types and under 10MB.', 'error');
    }

    // Restore button state
    uploadBtn.innerHTML = originalBtnHtml;
    uploadBtn.disabled = false;
}

// --- JOB SOURCES FUNCTIONS ---

async function loadJobSources() {
    if (!authToken) return;

    const sourcesListContent = document.getElementById('sourcesListContent');
    sourcesListContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2">Loading job sources...</p>
        </div>
    `;

    // Pass selected country so server filters the list
    const countrySelectEl = document.getElementById('sourceCountrySelect');
    const selectedCountry = countrySelectEl ? countrySelectEl.value : '';
    const url = selectedCountry
        ? `${API_BASE_URL}/jobs/sources?country=${encodeURIComponent(selectedCountry)}`
        : `${API_BASE_URL}/jobs/sources`;

    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `Server returned ${response.status}`);
        }

        const sources = await response.json();
        console.log('Sources loaded:', sources);
        renderJobSources(sources);
    } catch (error) {
        showToast('Load failed: ' + error.message, 'error');
        sourcesListContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>Error loading sources: ${error.message}
                <br><small>Make sure the backend server (port 8010) is running.</small>
                <div class="mt-2 text-center">
                    <button class="btn btn-outline-danger btn-sm" onclick="loadJobSources()">
                        <i class="fas fa-sync me-2"></i>Retry
                    </button>
                </div>
            </div>
        `;
    }
}

function renderJobSources(sources) {
    const container = document.getElementById('sourcesListContent');
    
    if (!sources || sources.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="fas fa-link fa-3x mb-3 opacity-25"></i>
                <p>No job sources found. Click the button above to discover tailored sources for you.</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead>
                    <tr>
                        <th>Active</th>
                        <th>Name & URL</th>
                        <th>Type</th>
                        <th>Validated</th>
                        <th>Tags</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;

    sources.forEach(source => {
        const tags = source.tags ? (Array.isArray(source.tags) ? source.tags : JSON.parse(source.tags)) : [];
        const tagsHtml = tags.slice(0, 4).map(tag => `<span class="badge bg-light text-dark border me-1">${tag}</span>`).join('');

        const typeColors = {
            'standard_portal': 'bg-primary',
            'global_with_local': 'bg-info text-dark',
            'boutique_recruiter': 'bg-warning text-dark',
            'company_career_page': 'bg-success',
            'government_portal': 'bg-secondary',
        };
        const typeBadgeClass = typeColors[source.source_type] || 'bg-primary';

        // Visual validation badge
        let validationBadge = '';
        if (source.maturity_level === 'invalid') {
            validationBadge = `<span class="badge bg-danger" title="${source.validation_notes || 'Did not pass visual check'}"><i class="fas fa-times-circle me-1"></i>Invalid</span>`;
        } else if (source.visual_validated === true) {
            const note = source.validation_notes ? source.validation_notes.replace(/"/g, '&quot;') : 'Confirmed: shows job listings';
            validationBadge = `<span class="badge bg-success" title="${note}"><i class="fas fa-check-circle me-1"></i>Verified</span>`;
        } else if (source.visual_validated === false) {
            const note = source.validation_notes ? source.validation_notes.replace(/"/g, '&quot;') : 'Visual check failed';
            validationBadge = `<span class="badge bg-warning text-dark" title="${note}"><i class="fas fa-exclamation-circle me-1"></i>Uncertain</span>`;
        } else if (source.maturity_level === 'qualified') {
            validationBadge = `<span class="badge bg-light text-dark border" title="URL verified but visual check not yet run"><i class="fas fa-link me-1"></i>URL OK</span>`;
        } else {
            validationBadge = `<span class="badge bg-light text-muted border"><i class="fas fa-clock me-1"></i>Pending</span>`;
        }

        let hostname = source.url;
        try { hostname = new URL(source.url).hostname; } catch(e) {}

        html += `
            <tr class="${source.maturity_level === 'invalid' ? 'table-warning' : ''}">
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" ${source.is_active ? 'checked' : ''}
                            onclick="toggleSourceActive(${source.id})">
                    </div>
                </td>
                <td>
                    <strong>${source.name}</strong><br>
                    <small><a href="${source.url}" target="_blank" class="text-muted"><i class="fas fa-external-link-alt me-1"></i>${hostname}</a></small>
                </td>
                <td><span class="badge ${typeBadgeClass}">${(source.source_type || 'general').replace(/_/g, ' ')}</span></td>
                <td>${validationBadge}</td>
                <td><div class="d-flex flex-wrap gap-1">${tagsHtml}</div></td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-secondary" onclick="showEditSourceModal(${JSON.stringify(source).replace(/"/g, '&quot;')})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteJobSource(${source.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;
}

function showAddSourceModal() {
    document.getElementById('sourceForm').reset();
    document.getElementById('sourceId').value = '';
    document.getElementById('sourceModalTitle').textContent = 'Add Job Source';
    sourceModal.show();
}

function showEditSourceModal(source) {
    document.getElementById('sourceId').value = source.id;
    document.getElementById('sourceName').value = source.name;
    document.getElementById('sourceUrl').value = source.url;
    document.getElementById('sourceType').value = source.source_type;
    document.getElementById('sourceDescription').value = source.description || '';
    
    const tags = source.tags ? (Array.isArray(source.tags) ? source.tags : JSON.parse(source.tags)) : [];
    document.getElementById('sourceTags').value = tags.join(', ');
    
    document.getElementById('sourceActive').checked = source.is_active;
    document.getElementById('sourceModalTitle').textContent = 'Edit Job Source';
    sourceModal.show();
}

async function handleSourceSubmit(event) {
    event.preventDefault();
    if (!authToken) return;

    const name = document.getElementById('sourceName').value;
    const url = document.getElementById('sourceUrl').value;
    const type = document.getElementById('sourceType').value;
    const description = document.getElementById('sourceDescription').value;
    const tags = document.getElementById('sourceTags').value.split(',').map(t => t.trim()).filter(t => t);
    const isActive = document.getElementById('sourceActive').checked;

    const btn = event.submitter;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/sources`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name, url, source_type: type, description, tags, is_active: isActive
            })
        });

        if (!response.ok) throw new Error('Failed to save source');

        showToast('Source saved successfully!', 'success');
        sourceModal.hide();
        loadJobSources();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function deleteJobSource(id) {
    if (!confirm('Are you sure you want to delete this source?')) return;
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/sources/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) throw new Error('Failed to delete source');

        showToast('Source deleted successfully', 'success');
        loadJobSources();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function toggleSourceActive(id) {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/sources/${id}/toggle`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) throw new Error('Failed to toggle source status');
        loadJobSources();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function runSourcing(force = false) {
    if (!authToken) return;

    const container = document.getElementById('sourcesListContent');
    const countrySelect = document.getElementById('sourceCountrySelect');
    // Country is optional — backend auto-detects from profile if not provided
    const selectedCountry = countrySelect ? countrySelect.value : '';

    const btn = document.getElementById('runDiscoveryBtn');
    const originalText = btn ? btn.innerHTML : '';
    
    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Syncing...';
        btn.disabled = true;
    }

    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;"></div>
            <h4 class="fw-bold">Syncing & Refining Sources...</h4>
            <p class="text-muted">This AI-driven discovery and URL refinement typically takes 30-60 seconds.</p>
        </div>
    `;
    
    showToast('Starting Job Sourcing Discovery...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/jobs/sources/run?force=${force}&country=${encodeURIComponent(selectedCountry)}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error ${response.status}`);
        }

        const result = await response.json();
        const validMsg = result.visually_valid != null
            ? ` | ${result.visually_valid} visually confirmed, ${result.visually_invalid || 0} flagged`
            : '';
        showToast(`Sourcing complete! ${result.new_sources} new sources, ${result.vetted_count} vetted${validMsg}.`, 'success');
        loadJobSources();
    } catch (error) {
        if (error.message && !error.message.includes('expired')) {
            showToast('Sync failed: ' + error.message, 'error');
        }
        loadJobSources(); // Refresh to clear loading state
    } finally {
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}

// Automatically process uploaded documents
// ...
async function processUploadedDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/analyze-uploaded`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Analysis failed');
        }

        const data = await response.json();
        showToast(`AI Analysis Complete! Processed ${data.successful_analyses} documents.`, 'success');
    } catch (error) {
        console.error('Processing error:', error);
        showToast('Files uploaded, but AI analysis failed or is still running.', 'warning');
    }
}

// View document analysis details
async function viewDocument(docId) {
    const modalEl = document.getElementById('analysisModal');
    const analysisModal = new bootstrap.Modal(modalEl);
    const contentDiv = document.getElementById('analysisContent');
    const titleH5 = document.getElementById('analysisModalTitle');
    const previewDiv = document.getElementById('filePreviewContainer');

    titleH5.textContent = 'Loading Analysis...';
    contentDiv.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Fetching analysis data from server...</p>
        </div>
    `;
    previewDiv.innerHTML = `
        <div class="text-center text-white opacity-50">
            <div class="spinner-border text-light" role="status"></div>
            <p class="mt-2">Loading preview...</p>
        </div>
    `;

    analysisModal.show();

    try {
        const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch document details');

        const doc = await response.json();
        titleH5.textContent = `Analysis: ${doc.original_filename}`;

        // Construction file URL
        const fileUrl = `${API_BASE_URL}/uploads/${doc.user_id}/${doc.document_type}/${doc.stored_filename}`;

        // Inject Preview
        if (doc.mime_type === 'application/pdf') {
            previewDiv.innerHTML = `<iframe src="${fileUrl}" width="100%" height="100%" style="border: none;"></iframe>`;
        } else if (doc.mime_type?.startsWith('image/')) {
            previewDiv.innerHTML = `<img src="${fileUrl}" class="img-fluid shadow" style="max-height: 100%; object-fit: contain;">`;
        } else {
            previewDiv.innerHTML = `
                <div class="text-center text-white p-5">
                    <i class="fas fa-file-download fa-4x mb-4 opacity-50"></i>
                    <h5>Preview not available</h5>
                    <p class="text-muted small">${doc.original_filename}</p>
                    <a href="${fileUrl}" target="_blank" class="btn btn-outline-light btn-sm mt-3">
                        <i class="fas fa-external-link-alt me-2"></i>Open File
                    </a>
                </div>
            `;
        }

        if (!doc.is_processed) {
            contentDiv.innerHTML = `
                <div class="alert alert-warning h-100 d-flex flex-column justify-content-center">
                    <h6><i class="fas fa-clock me-2"></i> Still Processing</h6>
                    <p class="small mb-0">AI analysis is currently in progress. This shouldn't take more than a minute.</p>
                    <hr>
                    <div class="progress" style="height: 5px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
                    </div>
                </div>
            `;
            return;
        }

        if (!doc.extracted_data) {
            contentDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i> Processed, but no structured data was extracted.
                </div>
            `;
            return;
        }

        const data = JSON.parse(doc.extracted_data);

        let html = `
            <div class="d-flex align-items-center mb-3">
                <span class="badge bg-primary me-2">${doc.document_type}</span>
                <span class="text-muted small">ID: ${doc.id}</span>
            </div>
            
            <section class="mb-4">
                <h6 class="border-bottom pb-2 fw-bold"><i class="fas fa-user me-2 text-primary"></i>Personal Info</h6>
                <div class="bg-white p-2 border rounded small">
                    <div class="mb-1"><strong>Name:</strong> ${data.personal_info?.name || 'Not detected'}</div>
                    <div class="mb-1"><strong>Email:</strong> ${data.personal_info?.emails?.join(', ') || 'Not detected'}</div>
                    <div class="mb-0"><strong>Phone:</strong> ${data.personal_info?.phones?.join(', ') || 'Not detected'}</div>
                </div>
            </section>
            
            <section class="mb-4">
                <h6 class="border-bottom pb-2 fw-bold"><i class="fas fa-tools me-2 text-primary"></i>Skills</h6>
                <div class="d-flex flex-wrap gap-1 mt-2">
                    ${data.skills && data.skills.length > 0
                ? data.skills.map(s => {
                    const name = typeof s === 'object' ? (s.skill_name || s.name || JSON.stringify(s)) : s;
                    return `<span class="badge bg-light text-dark border">${name}</span>`;
                }).join('')
                : '<p class="text-muted extra-small">No skills detected.</p>'}
                </div>
            </section>

            <section class="mb-4">
                <h6 class="border-bottom pb-2 fw-bold"><i class="fas fa-briefcase me-2 text-primary"></i>Experience</h6>
                <div class="mt-2">
                    ${data.experience && data.experience.length > 0
                ? data.experience.map(e => `
                            <div class="mb-2 p-2 border-start border-primary border-3 bg-white shadow-sm rounded-end">
                                <div class="fw-bold extra-small">${e.title || 'Role'}</div>
                                <div class="text-muted extra-small">${e.company || 'Company'}</div>
                            </div>
                        `).join('')
                : '<p class="text-muted extra-small">No experience entries.</p>'}
                </div>
            </section>

            <section>
                <h6 class="border-bottom pb-2 fw-bold"><i class="fas fa-quote-left me-2 text-primary"></i>Summary</h6>
                <p class="fst-italic extra-small mt-2 bg-white p-3 rounded border">
                    "${data.personal_info?.summary || 'No summary extracted.'}"
                </p>
            </section>
            
            <div class="alert alert-success mt-4 extra-small py-2 px-3 d-flex align-items-center">
                <i class="fas fa-check-circle me-2"></i> Verified by AI
            </div>
        `;

        contentDiv.innerHTML = html;

    } catch (error) {
        console.error('View error:', error);
        contentDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i> Error: ${error.message}
            </div>
        `;
        previewDiv.innerHTML = `<p class="text-white opacity-25">Preview failed to load</p>`;
    }
}

// View Full Profile (Editable)
function showFullProfileTab(tabId) {
    showFullProfile().then(() => {
        const tabBtn = document.getElementById(`${tabId}-tab`);
        if (tabBtn) {
            const tab = new bootstrap.Tab(tabBtn);
            tab.show();
        }
    });
}

// Helper to clean up encoding issues (e.g., â€“ instead of –)
function cleanText(text) {
    if (!text) return "";
    return text.toString()
        .replace(/â€“/g, '–')
        .replace(/â€”/g, '—')
        .replace(/â€˜/g, "‘")
        .replace(/â€™/g, "’")
        .replace(/â€œ/g, '“')
        .replace(/â€\?/g, '”')
        .replace(/\ufffd/g, '–');
}

// Helper to format date consistently (YYYY-MM)
function formatDateShort(dateStr) {
    if (!dateStr || dateStr.startsWith('1900')) return "";
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr.split('T')[0];
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}`;
    } catch (e) {
        return dateStr.split('T')[0];
    }
}

// Helper to render proficiency dots
function renderLanguagesDots(proficiency) {
    const levels = {
        'beginner': 1,
        'limited': 1,
        'intermediate': 2,
        'professional': 3,
        'advanced': 3,
        'fluent': 4,
        'native': 5,
        'expert': 5
    };
    const count = levels[proficiency.toLowerCase()] || 1;
    let dots = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= count) {
            dots += '<i class="fas fa-circle text-primary me-1" style="font-size: 10px;"></i>';
        } else {
            dots += '<i class="far fa-circle text-muted me-1" style="font-size: 10px;"></i>';
        }
    }
    return dots;
}

function renderMasterCV(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const profile = data.profile || {};
    const experiences = data.experiences || [];
    const educations = data.educations || [];
    const skills = data.skills || [];

    let html = '';

    // Profile Header with Photo
    if (profile.profile_picture_url) {
        html += `
            <div class="cv-section d-flex align-items-center gap-4">
                <img src="${API_BASE_URL}${profile.profile_picture_url}" class="rounded shadow-sm" style="width: 100px; height: 100px; object-fit: cover; border: 3px solid #f8f9fa;">
                <div>
                    <h3 class="fw-bold mb-1">${data.user?.full_name || 'Your Name'}</h3>
                    <p class="text-muted mb-0">${experiences[0]?.position || 'Professional'}</p>
                    <div class="mt-2">
                        <span class="badge bg-light text-dark border"><i class="fas fa-map-marker-alt me-1 text-primary"></i>${profile.location || 'Location not set'}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // 1. Professional Summary Section
    html += `
        <div class="cv-section">
            <div class="cv-section-header">
                <div class="cv-section-title">Professional Summary</div>
                <a class="cv-edit-link" onclick="showFullProfileTab('personal')">Edit</a>
            </div>
            <div class="cv-item-description">
                ${profile.summary ? cleanText(profile.summary) : '<span class="text-muted italic">No summary provided. Add one to help AI match your profile.</span>'}
            </div>
        </div>
    `;

    // 1b. Personal Information Section
    if (profile.dob || profile.nationality || profile.marital_status || profile.work_auth) {
        html += `
            <div class="cv-section">
                <div class="cv-section-header">
                    <div class="cv-section-title">Personal Information</div>
                    <a class="cv-edit-link" onclick="showFullProfileTab('personal')">Edit</a>
                </div>
                <div class="row mt-2 g-2">
                    ${profile.dob ? `<div class="col-6 small"><span class="fw-bold text-muted">Date of Birth:</span> ${cleanText(profile.dob)}</div>` : ''}
                    ${profile.nationality ? `<div class="col-6 small"><span class="fw-bold text-muted">Nationality:</span> ${cleanText(profile.nationality)}</div>` : ''}
                    ${profile.marital_status ? `<div class="col-6 small"><span class="fw-bold text-muted">Marital Status:</span> ${cleanText(profile.marital_status)}</div>` : ''}
                    ${profile.work_auth ? `<div class="col-6 small"><span class="fw-bold text-muted">Work Authorization:</span> ${cleanText(profile.work_auth)}</div>` : ''}
                </div>
            </div>
        `;
    }

    // 2. Experience Section
    html += `
        <div class="cv-section">
            <div class="cv-section-header">
                <div class="cv-section-title">Experience</div>
                <a class="cv-edit-link" onclick="showFullProfileTab('experience')">Edit Range</a>
            </div>
            ${experiences.length > 0 ? experiences.map(exp => `
                <div class="cv-item">
                    <div class="cv-item-title">${cleanText(exp.position)}</div>
                    <div class="cv-item-subtitle">${cleanText(exp.company)} ${exp.location ? `• ${cleanText(exp.location)}` : ''}</div>
                    <div class="cv-item-meta">${formatDateShort(exp.start_date)} - ${exp.end_date ? formatDateShort(exp.end_date) : 'Present'}</div>
                    ${exp.description ? `<div class="cv-item-description">${cleanText(exp.description)}</div>` : ''}
                </div>
            `).join('') : '<div class="text-muted small">No experience history added yet.</div>'}
        </div>
    `;

    // 3. Education Section
    html += `
        <div class="cv-section">
            <div class="cv-section-header">
                <div class="cv-section-title">Education</div>
                <a class="cv-edit-link" onclick="showFullProfileTab('education')">Edit</a>
            </div>
            ${educations.length > 0 ? educations.map(edu => `
                <div class="cv-item">
                    <div class="cv-item-title">${cleanText(edu.degree || edu.institution)}</div>
                    <div class="cv-item-subtitle">${edu.degree ? cleanText(edu.institution) : ''}</div>
                    <div class="cv-item-meta">${formatDateShort(edu.start_date)} ${edu.end_date ? `- ${formatDateShort(edu.end_date)}` : ''}</div>
                </div>
            `).join('') : '<div class="text-muted small">No education history added yet.</div>'}
        </div>
    `;

    // 4. Certifications Section (if available)
    if (profile.certifications || (data.certifications && data.certifications.length > 0)) {
        let certs = data.certifications || [];
        if (certs.length === 0 && profile.certifications) {
            try {
                certs = typeof profile.certifications === 'string' ? JSON.parse(profile.certifications) : profile.certifications;
            } catch(e) { certs = []; }
        }
        
        if (certs.length > 0) {
            html += `
                <div class="cv-section">
                    <div class="cv-section-header">
                        <div class="cv-section-title">Certifications</div>
                    </div>
                    <div class="mt-2">
                        ${certs.map(c => `
                            <div class="cv-item mb-1">
                                <i class="fas fa-certificate text-primary me-2"></i> ${typeof c === 'string' ? c : (c.name || 'Certification')}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    }

    // 5. Skills Section
    html += `
        <div class="cv-section">
            <div class="cv-section-header">
                <div class="cv-section-title">Skills & Expertise</div>
                <a class="cv-edit-link" onclick="showFullProfileTab('skills')">Edit</a>
            </div>
            <div class="d-flex flex-wrap gap-2 mt-2">
                ${skills.filter(s => s.category !== 'language').length > 0 ? skills.filter(s => s.category !== 'language').map(s => {
                    const name = typeof s === 'object' ? s.skill_name : s;
                    return `<span class="skill-badge-cv">${cleanText(name)}</span>`;
                }).join('') : '<div class="text-muted small">No technical skills added.</div>'}
            </div>
        </div>
    `;

    // 6. Languages Section
    const languages = skills.filter(s => s.category === 'language');
    if (languages.length > 0) {
        html += `
            <div class="cv-section">
                <div class="cv-section-header">
                    <div class="cv-section-title">Languages</div>
                    <a class="cv-edit-link" onclick="showFullProfileTab('languages')">Edit</a>
                </div>
                <div class="row mt-2 g-3">
                    ${languages.map(lang => `
                        <div class="col-md-6 d-flex align-items-center justify-content-between">
                            <span class="fw-bold">${cleanText(lang.skill_name)}</span>
                            <div>${renderLanguagesDots(lang.proficiency || 'intermediate')}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

async function showFullProfile() {
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    const profile = await fetchProfileData();
    if (!profile) return;

    // Populate Side Stats
    document.getElementById('profileEditorName').textContent = profile.user.full_name || 'User';
    document.getElementById('profileEditorTitle').textContent = profile.experiences?.[0]?.position || 'Professional';

    // Set avatar in editor
    const defaultIcon = document.getElementById('profileEditorDefaultIcon');
    const previewImg = document.getElementById('profileEditorPreview');
    if (profile.profile?.profile_picture_url) {
        if (defaultIcon) defaultIcon.style.display = 'none';
        if (previewImg) {
            previewImg.src = `${API_BASE_URL}${profile.profile.profile_picture_url}`;
            previewImg.style.display = 'block';
        }
    } else {
        if (defaultIcon) defaultIcon.style.display = 'block';
        if (previewImg) previewImg.style.display = 'none';
    }

    const progress = profile.profile?.completion_percentage || 0;
    const progressEl = document.getElementById('profileProgress');
    if (progressEl) progressEl.style.width = `${progress}%`;
    const progressTextEl = document.getElementById('profileProgressText');
    if (progressTextEl) progressTextEl.textContent = `${progress}%`;

    // Populate Personal Info Tab
    const piForm = document.getElementById('personalInfoForm');
    if (piForm) {
        if (piForm.desired_job_title) piForm.desired_job_title.value = profile.profile?.desired_job_title || '';
        piForm.phone.value = profile.profile?.phone || '';
        piForm.location.value = profile.profile?.location || '';
        piForm.linkedin_url.value = profile.profile?.linkedin_url || '';
        piForm.summary.value = profile.profile?.summary || '';
        
        // New fields
        if (piForm.dob) piForm.dob.value = profile.profile?.dob || '';
        if (piForm.nationality) piForm.nationality.value = profile.profile?.nationality || '';
        if (piForm.marital_status) piForm.marital_status.value = profile.profile?.marital_status || '';
        if (piForm.work_auth) piForm.work_auth.value = profile.profile?.work_auth || '';
    }

    // Handle Personal Info Submit
    piForm.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(piForm);
        const data = Object.fromEntries(formData.entries());
        await saveProfileSection('/profile', data, 'Personal Info');
    };

    // Populate Experience Tab
    renderExperienceList(profile.experiences || []);

    // Populate Education Tab
    renderEducationList(profile.educations || []);

    // Populate Skills Tab
    renderSkillsList(profile.skills || []);

    // Populate Languages Tab
    renderLanguagesList(profile.skills || []);

    modal.show();
}

async function fetchProfileData() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error('Failed to fetch dashboard');
        return await response.json();
    } catch (error) {
        showToast('Error loading profile: ' + error.message, 'danger');
        return null;
    }
}

async function saveProfileSection(endpoint, data, label) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`Failed to update ${label}`);
        showToast(`${label} updated successfully!`, 'success');
        return await response.json();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'danger');
        return null;
    }
}

function renderExperienceList(experiences) {
    const list = document.getElementById('experienceList');
    if (experiences.length === 0) {
        list.innerHTML = '<p class="text-muted text-center py-3">No experience records. Add one below!</p>';
        return;
    }

    list.innerHTML = experiences.map(exp => {
        const isUnknown = (exp.company?.includes('Unknown') || exp.position?.includes('Unknown') || exp.position === 'Professional');
        const isDated1900 = exp.start_date && exp.start_date.startsWith('1900');
        const needsValidation = isUnknown || isDated1900;
        
        const dateStr = isDated1900 ? 
            '<span class="text-danger">Verify Date</span>' : 
            `${new Date(exp.start_date).toLocaleDateString()} - ${exp.end_date ? new Date(exp.end_date).toLocaleDateString() : 'Present'}`;

        return `
        <div class="card mb-3 border-start border-4 shadow-sm ${needsValidation ? 'needs-validation border-danger' : 'border-primary'}" id="exp-card-${exp.id}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="card-title mb-0 font-weight-bold">
                        ${exp.company}
                        ${needsValidation ? '<span class="validation-badge ms-2"><i class="fas fa-exclamation-triangle"></i> Verify</span>' : ''}
                    </h6>
                    <div>
                        <button class="btn btn-sm btn-outline-info me-1" onclick="toggleEditExp(${exp.id})"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteExperience(${exp.id})"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
                <p class="${isUnknown && exp.position.includes('Unknown') ? 'text-danger' : 'text-primary'} small mb-2">${exp.position}</p>
                <div id="exp-view-${exp.id}">
                    <p class="small text-muted mb-2"><i class="far fa-calendar-alt me-1"></i> ${dateStr}</p>
                    <p class="mb-0 small">${exp.description || 'No description provided.'}</p>
                </div>
                <div id="exp-edit-${exp.id}" class="d-none">
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="extra-small text-muted">Company</label>
                            <input type="text" class="form-control form-control-sm" id="exp-company-${exp.id}" value="${exp.company}">
                        </div>
                        <div class="col-6">
                            <label class="extra-small text-muted">Position</label>
                            <input type="text" class="form-control form-control-sm" id="exp-title-${exp.id}" value="${exp.position}">
                        </div>
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="extra-small text-muted">Start Date</label>
                            <input type="date" class="form-control form-control-sm" id="exp-start-${exp.id}" value="${exp.start_date && !isDated1900 ? exp.start_date.split('T')[0] : ''}">
                        </div>
                        <div class="col-6">
                            <label class="extra-small text-muted">End Date</label>
                            <input type="date" class="form-control form-control-sm" id="exp-end-${exp.id}" value="${exp.end_date ? exp.end_date.split('T')[0] : ''}">
                        </div>
                    </div>
                    <div class="mb-2">
                        <label class="extra-small text-muted">Description</label>
                        <textarea class="form-control form-control-sm" id="exp-desc-${exp.id}" rows="3">${exp.description || ''}</textarea>
                    </div>
                    <div class="text-end">
                        <button class="btn btn-sm btn-link text-muted" onclick="toggleEditExp(${exp.id})">Cancel</button>
                        <button class="btn btn-sm btn-primary" onclick="saveExperience(${exp.id})">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    `}).join('');
}

function toggleEditExp(id) {
    document.getElementById(`exp-view-${id}`).classList.toggle('d-none');
    document.getElementById(`exp-edit-${id}`).classList.toggle('d-none');
}

async function saveExperience(id) {
    const data = {
        company: document.getElementById(`exp-company-${id}`).value,
        position: document.getElementById(`exp-title-${id}`).value,
        start_date: document.getElementById(`exp-start-${id}`).value,
        end_date: document.getElementById(`exp-end-${id}`).value || null,
        description: document.getElementById(`exp-desc-${id}`).value
    };

    // Convert date string to ISO if exists
    if (data.start_date) data.start_date = new Date(data.start_date).toISOString();
    if (data.end_date) data.end_date = new Date(data.end_date).toISOString();

    const result = await saveProfileSection(`/profile/experience/${id}`, data, 'Experience');
    if (result) {
        toggleEditExp(id);
        // Refresh local view or re-render
        const profile = await fetchProfileData();
        if (profile) renderExperienceList(profile.experiences);
    }
}

async function deleteExperience(id) {
    if (!confirm('Delete this experience entry?')) return;
    try {
        const response = await fetch(`${API_BASE_URL}/profile/experience/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error('Failed to delete');
        showToast('Experience deleted', 'success');
        document.getElementById(`exp-card-${id}`).remove();
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

function renderEducationList(educations) {
    const list = document.getElementById('educationList');
    if (educations.length === 0) {
        list.innerHTML = '<p class="text-muted text-center py-3">No education records. Add one below!</p>';
        return;
    }

    list.innerHTML = educations.map(edu => {
        const isVerified = edu.source_document_id !== null;
        const hasDate = edu.end_date !== null;
        
        return `
        <div class="card mb-3 border-start border-4 shadow-sm ${(isVerified && hasDate) ? 'verified border-success' : (hasDate ? 'border-primary' : 'needs-validation border-danger')}" id="edu-card-${edu.id}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="card-title mb-0 font-weight-bold">
                        ${edu.institution || 'Unknown Institution'}
                        ${(isVerified && hasDate) ? '<span class="verified-badge ms-2"><i class="fas fa-check-circle"></i> Verified</span>' : ''}
                        ${!hasDate ? '<span class="validation-badge ms-2"><i class="fas fa-exclamation-triangle"></i> Verify Date</span>' : ''}
                    </h6>
                    <div>
                        <button class="btn btn-sm btn-outline-info me-1" onclick="toggleEditEdu(${edu.id})"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteEducation(${edu.id})"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
                <p class="text-success small mb-2">${edu.degree} ${edu.field_of_study ? `in ${edu.field_of_study}` : ''}</p>
                <div id="edu-view-${edu.id}">
                    <p class="small text-muted mb-0"><i class="far fa-calendar-alt me-1"></i> ${edu.start_date ? new Date(edu.start_date).getFullYear() : ''} - ${edu.end_date ? new Date(edu.end_date).getFullYear() : 'Present'}</p>
                </div>
                <div id="edu-edit-${edu.id}" class="d-none">
                    <div class="mb-2">
                        <label class="extra-small text-muted">Institution</label>
                        <input type="text" class="form-control form-control-sm" id="edu-inst-${edu.id}" value="${edu.institution}">
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="extra-small text-muted">Degree</label>
                            <input type="text" class="form-control form-control-sm" id="edu-deg-${edu.id}" value="${edu.degree}">
                        </div>
                        <div class="col-6">
                            <label class="extra-small text-muted">Field</label>
                            <input type="text" class="form-control form-control-sm" id="edu-field-${edu.id}" value="${edu.field_of_study || ''}">
                        </div>
                    </div>
                    <div class="text-end">
                        <button class="btn btn-sm btn-link text-muted" onclick="toggleEditEdu(${edu.id})">Cancel</button>
                        <button class="btn btn-sm btn-success" onclick="saveEducation(${edu.id})">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    `}).join('');
}

function toggleEditEdu(id) {
    document.getElementById(`edu-view-${id}`).classList.toggle('d-none');
    document.getElementById(`edu-edit-${id}`).classList.toggle('d-none');
}

async function saveEducation(id) {
    const data = {
        institution: document.getElementById(`edu-inst-${id}`).value,
        degree: document.getElementById(`edu-deg-${id}`).value,
        field_of_study: document.getElementById(`edu-field-${id}`).value
    };

    const result = await saveProfileSection(`/profile/education/${id}`, data, 'Education');
    if (result) {
        toggleEditEdu(id);
        const profile = await fetchProfileData();
        if (profile) renderEducationList(profile.educations);
    }
}

async function deleteEducation(id) {
    if (!confirm('Delete this education entry?')) return;
    try {
        const response = await fetch(`${API_BASE_URL}/profile/education/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error('Failed to delete');
        showToast('Education deleted', 'success');
        document.getElementById(`edu-card-${id}`).remove();
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

async function addExperienceEntry() {
    try {
        const response = await fetch(`${API_BASE_URL}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                experiences: [{
                    company: 'New Company',
                    position: 'Position',
                    start_date: new Date().toISOString()
                }]
            })
        });
        if (!response.ok) throw new Error('Failed to add experience');
        showToast('Temporary entry added. Please edit it.', 'info');
        const data = await fetchProfileData();
        if (data) renderExperienceList(data.experiences);
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

async function addEducationEntry() {
    try {
        const response = await fetch(`${API_BASE_URL}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                educations: [{
                    institution: 'New Institution',
                    degree: 'Degree',
                    start_date: new Date().toISOString()
                }]
            })
        });
        if (!response.ok) throw new Error('Failed to add education');
        showToast('Temporary entry added. Please edit it.', 'info');
        const data = await fetchProfileData();
        if (data) renderEducationList(data.educations);
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

function renderSkillsList(skills) {
    const container = document.getElementById('skillsBadges');
    if (!container) return;
    
    // Filter out languages for the skills tab
    const filteredSkills = skills.filter(s => s.category !== 'language');
    
    if (filteredSkills.length === 0) {
        container.innerHTML = '<p class="text-muted w-100 text-center py-3">No technical skills listed yet.</p>';
        return;
    }

    container.innerHTML = filteredSkills.map(skill => `
        <span class="badge bg-primary d-flex align-items-center p-2">
            ${skill.skill_name}
            <i class="fas fa-times ms-2 cursor-pointer" onclick="deleteSkill('${skill.skill_name}')" style="cursor:pointer"></i>
        </span>
    `).join('');
}

function renderLanguagesList(skills) {
    const container = document.getElementById('languagesList');
    if (!container) return;

    const languages = skills.filter(s => s.category === 'language');
    if (languages.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No languages added. Add one below!</p>';
        return;
    }

    container.innerHTML = `
        <table class="table table-sm mt-3">
            <thead>
                <tr>
                    <th>Language</th>
                    <th>Proficiency</th>
                    <th class="text-end">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${languages.map(lang => `
                    <tr>
                        <td class="align-middle fw-bold">${cleanText(lang.skill_name)}</td>
                        <td class="align-middle">${renderLanguagesDots(lang.proficiency || 'intermediate')} <small class="text-muted ms-2">(${lang.proficiency})</small></td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteSkill('${lang.skill_name}')"><i class="fas fa-trash"></i></button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function addLanguageEntry() {
    const nameInput = document.getElementById('newLanguageName');
    const profSelect = document.getElementById('newLanguageProficiency');
    const name = nameInput.value.trim();
    if (!name) return;

    try {
        const response = await fetch(`${API_BASE_URL}/profile/skills`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ 
                name: name,
                category: 'language',
                proficiency: profSelect.value
            })
        });
        if (!response.ok) throw new Error('Failed to add language');
        showToast('Language added!', 'success');
        nameInput.value = '';
        const data = await fetchProfileData();
        if (data) {
            renderLanguagesList(data.skills);
            updateDashboardHighlights(); // Refresh CV view
        }
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

async function addNewSkill() {
    const input = document.getElementById('newSkillInput');
    const skillName = input.value.trim();
    if (!skillName) return;

    try {
        const response = await fetch(`${API_BASE_URL}/profile/skills`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ name: skillName })
        });
        if (!response.ok) throw new Error('Failed to add skill');
        showToast('Skill added!', 'success');
        input.value = '';
        const data = await fetchProfileData();
        if (data) renderSkillsList(data.skills);
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

async function deleteSkill(skillName) {
    if (!confirm(`Remove skill/language "${skillName}"?`)) return;
    try {
        const response = await fetch(`${API_BASE_URL}/profile/skills/${encodeURIComponent(skillName)}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error('Failed to remove entry');
        showToast('Removed successfully', 'success');
        const data = await fetchProfileData();
        if (data) {
            renderSkillsList(data.skills);
            renderLanguagesList(data.skills);
            updateDashboardHighlights();
        }
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

let pollingInterval = null;

function startPolling() {
    if (pollingInterval) return;

    console.log("Starting document status polling...");
    pollingInterval = setInterval(async () => {
        const response = await fetch(`${API_BASE_URL}/dashboard`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            const documents = data.documents || [];

            // Update the UI
            updateDocumentsList(documents);
            updateDashboardCounters(data);

            // Check if we still need to poll
            const hasProcessing = documents.some(doc =>
                doc.processing_status === 'pending' || doc.processing_status === 'processing'
            );

            if (!hasProcessing) {
                console.log("All documents processed. Stopping polling.");
                stopPolling();
            }
        }
    }, 5000); // Poll every 5 seconds
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Delete document
async function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to delete document');
        }

        showToast('Document deleted successfully!', 'success');
        loadDashboardData(); // Refresh dashboard

    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Toggle select all documents
function toggleSelectAllDocs() {
    const selectAll = document.getElementById('selectAllDocs').checked;
    const checkboxes = document.querySelectorAll('.doc-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll);
    toggleDeleteSelectedBtn();
}

// Toggle visibility of delete selected button
function toggleDeleteSelectedBtn() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    if (deleteBtn) {
        deleteBtn.style.display = checkboxes.length > 0 ? 'inline-block' : 'none';
    }
}

// Delete selected documents
async function deleteSelectedDocuments() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
    if (checkboxes.length === 0) return;

    if (!confirm(`Are you sure you want to delete ${checkboxes.length} selected document(s)?`)) {
        return;
    }

    let successCount = 0;
    let failCount = 0;

    // Change button text
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const originalHtml = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
    deleteBtn.disabled = true;

    for (const cb of checkboxes) {
        const docId = cb.value;
        try {
            const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });

            if (response.ok) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            failCount++;
        }
    }

    if (successCount > 0) {
        showToast(`Successfully deleted ${successCount} document(s).` + (failCount > 0 ? ` Failed: ${failCount}` : ''), 'success');
        loadDashboardData(); // Refresh dashboard, will reset checkboxes and button
        if (deleteBtn) deleteBtn.style.display = 'none'; // Ensure hidden upon refresh
    } else {
        showToast('Failed to delete selected documents.', 'error');
    }

    if (deleteBtn) {
        deleteBtn.innerHTML = originalHtml;
        deleteBtn.disabled = false;
    }
}

// Logout
function logout() {
    console.log('Logging out...');
    localStorage.clear(); 
    sessionStorage.clear();
    authToken = null;
    currentUser = null;

    showToast('Logged out successfully', 'info');
    
    // Reload page to reset UI and clear all states
    setTimeout(() => {
        window.location.href = '/';
        window.location.reload();
    }, 500);
}

// Hard reset for session issues
function clearLocalSession() {
    if (confirm('This will clear all local session data and reload the page. Use this to fix login/display issues. Continue?')) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/';
        window.location.reload();
    }
}


// Event Listeners
document.addEventListener('DOMContentLoaded', async function () {
    console.log('DOMContentLoaded - Initializing application...');
    
    // Login form submission
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            await login(email, password);
        });
    }

    // Register form submission
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const fullName = document.getElementById('registerFullName').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const confirmPassword = document.getElementById('registerConfirmPassword').value;

            if (password !== confirmPassword) {
                showToast('Passwords do not match', 'error');
                return;
            }

            if (password.length < 8) {
                showToast('Password must be at least 8 characters', 'error');
                return;
            }

            await register(fullName, email, password);
        });
    }

    // Forgot password form
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await requestPasswordReset(document.getElementById('forgotEmail').value);
        });
    }

    // Reset password form
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await resetPassword(
                document.getElementById('resetToken').value,
                document.getElementById('resetNewPassword').value,
                document.getElementById('resetConfirmPassword').value
            );
        });
    }

    // Check URL for reset token (e.g. opened from email link ?reset_token=xxx)
    const urlParams = new URLSearchParams(window.location.search);
    const urlResetToken = urlParams.get('reset_token');
    if (urlResetToken) {
        // Clean the token from URL bar without reload
        window.history.replaceState({}, '', window.location.pathname + window.location.hash);
        showResetPasswordModal(urlResetToken);
    }

    // Source Form
    const sourceForm = document.getElementById('sourceForm');
    if (sourceForm) {
        sourceForm.onsubmit = handleSourceSubmit;
    }

    // Check API Status first
    await checkApiStatus();
    
    // Initial hash detection
    const initialHash = window.location.hash.substring(1);
    console.log(`Initial hash detected: ${initialHash}`);

    // Restore session and update UI
    await checkLoginStatus();

    // If we have a hash, navigate to that tab after a short delay to ensure UI is ready
    if (initialHash) {
        setTimeout(() => {
            handleHashChange();
        }, 150);
    }

    // Handle hash changes (Back/Forward buttons)
    window.addEventListener('hashchange', handleHashChange);
    
    // Check API status every 60 seconds
    setInterval(checkApiStatus, 60000);
});

// Function to handle hash changes for navigation
function handleHashChange() {
    const hash = window.location.hash.substring(1); // Remove #
    if (!hash) return;

    // Map of hash to tab IDs
    const tabMap = {
        'dashboard': 'tab-dashboard',
        'documents': 'tab-documents',
        'jobs': 'tab-jobs',
        'applications': 'tab-applications',
        'social': 'tab-social',
        'sources': 'tab-sources'
    };

    if (tabMap[hash]) {
        switchMainTab(tabMap[hash], false); // Pass false to avoid recursive hash update
    }
}

// Export functions to global scope
window.showLoginModal = showLoginModal;
window.showRegisterModal = showRegisterModal;
window.showForgotPasswordModal = showForgotPasswordModal;
window.showResetPasswordModal = showResetPasswordModal;
window.showUploadModal = showUploadModal;
window.login = login;
window.register = register;
window.uploadDocument = uploadDocument;
window.viewDocument = viewDocument;
window.showFullProfile = showFullProfile;
window.startPolling = startPolling;
window.deleteDocument = deleteDocument;
window.deleteSelectedDocuments = deleteSelectedDocuments;
window.toggleSelectAllDocs = toggleSelectAllDocs;
window.toggleDeleteSelectedBtn = toggleDeleteSelectedBtn;
window.toggleUploadMode = toggleUploadMode;
window.logout = logout;
window.loadDashboardData = loadDashboardData;
window.toggleEditExp = toggleEditExp;
window.saveExperience = saveExperience;
window.deleteExperience = deleteExperience;
window.addExperienceEntry = addExperienceEntry;
window.toggleEditEdu = toggleEditEdu;
window.saveEducation = saveEducation;
window.deleteEducation = deleteEducation;
window.addEducationEntry = addEducationEntry;
window.addNewSkill = addNewSkill;
window.deleteSkill = deleteSkill;
window.showResetConfirmModal = showResetConfirmModal;
window.confirmResetProfile = confirmResetProfile;
window.loadJobFinder = loadJobFinder;
window.loadApplications = loadApplications;
window.loadSocialEngine = loadSocialEngine;
window.loadJobSources = loadJobSources;
window.showAddSourceModal = showAddSourceModal;
window.showEditSourceModal = showEditSourceModal;
window.deleteJobSource = deleteJobSource;
window.toggleSourceActive = toggleSourceActive;
window.runSourcing = runSourcing;
window.vetSources = vetSources;
window.changeJobPage = changeJobPage;
window.switchJobFilter = switchJobFilter;

function switchJobFilter(filterType) {
    currentJobFilter = filterType;
    loadJobFinder(1);
}

// --- AI SEARCH SETTINGS LOGIC ---


function syncJobFinderFiltersWithProfile(profile) {
    if (!profile) return;

    // Sync Frontend Filters with Profile
    // Job Types
    const profileJobTypes = profile.job_types ? (typeof profile.job_types === 'string' ? JSON.parse(profile.job_types) : profile.job_types) : [];
    const permCb = document.getElementById('filterTypePermanent');
    const contCb = document.getElementById('filterTypeContract');
    if (permCb) permCb.checked = profileJobTypes.includes('Permanent');
    if (contCb) contCb.checked = profileJobTypes.includes('Contract') || profileJobTypes.includes('Contract / Freelance');

    // Work Modes
    const profileWorkModes = profile.work_modes ? (typeof profile.work_modes === 'string' ? JSON.parse(profile.work_modes) : profile.work_modes) : [];
    ['On-site', 'Hybrid', 'Remote'].forEach(mode => {
        const cb = document.getElementById(`filterMode${mode.replace('-', '')}`);
        if (cb) cb.checked = profileWorkModes.includes(mode);
    });

    // Exp Level
    const expLevelSelect = document.getElementById('filterExpLevel');
    if (expLevelSelect) expLevelSelect.value = profile.experience_level || '';
}

async function saveAISettings(isDeepCheck = false) {
    const role = document.getElementById('finderTargetRole').value;
    const seniority = document.getElementById('finderSeniority').value;
    const region = document.getElementById('finderRegion').value;

    // Helper to extract country from location string
    const extractCountry = (loc) => {
        if (!loc) return 'Switzerland';
        const locLower = loc.toLowerCase();
        if (locLower.includes('switzerland') || locLower.includes('schweiz') || locLower.includes('suisse') || locLower.includes('svizzera')) return 'Switzerland';
        if (locLower.includes('germany') || locLower.includes('deutschland')) return 'Germany';
        if (locLower.includes('france') || locLower.includes('frankreich')) return 'France';
        if (locLower.includes('italy') || locLower.includes('italien')) return 'Italy';
        if (locLower.includes('austria') || locLower.includes('österreich')) return 'Austria';
        
        // Default to Switzerland for this user's typical context if it's a Swiss zip code/address pattern
        if (/\b\d{4}\b/.test(loc) || locLower.includes('ch-')) return 'Switzerland';
        
        // Final fallback: use the last part if comma separated
        const parts = loc.split(',');
        return parts[parts.length - 1].trim();
    };

    const targetCountry = extractCountry(region);

    const btn = document.querySelector('#aiFinderSettingsForm button');
    const originalText = btn.innerHTML;
    
    if (isDeepCheck) {
        btn.innerHTML = '<i class="fas fa-brain fa-spin me-2"></i>Running Deep Alignment...';
    } else {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Applying...';
    }
    btn.disabled = true;

    try {
        const data = {
            desired_job_title: role,
            experience_level: seniority,
            location: region // Keep full location in profile
        };

        const result = await saveProfileSection('/profile', data, 'Discovery Settings');

        if (result) {
            showToast(`AI Discovery Persona updated for ${targetCountry}!`, 'success');
            if (isDeepCheck) {
                runDeepAlignment();
            } else {
                toggleAISettings();
                loadJobFinder();
            }
        }
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// --- JOB FINDER AGENT FUNCTIONS ---

// ── Phase 1 + 2: Refresh Jobs ─────────────────────────────────────────────
async function refreshJobs() {
    if (!authToken) return;
    const btn = document.getElementById('refreshJobsBtn');
    const container = document.getElementById('jobListContent');

    const setBtn = (html, disabled) => { if (btn) { btn.innerHTML = html; btn.disabled = disabled; } };
    const phase = (msg) => {
        if (container) container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-3" role="status" style="width:3rem;height:3rem;"></div>
                <h4 class="fw-bold">${msg}</h4>
                <p class="text-muted">This may take 30–90 seconds depending on source count.</p>
            </div>`;
    };

    setBtn('<i class="fas fa-spinner fa-spin me-2"></i>Refreshing…', true);

    try {
        // ── Phase 1: raw ingestion ────────────────────────────────────────
        phase('Phase 1 of 2 — Downloading jobs from all sources…');
        const r1 = await fetch(`${API_BASE_URL}/jobs/refresh`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!r1.ok) throw new Error(`Ingestion failed (${r1.status})`);
        const d1 = await r1.json();

        // ── Phase 2: user alignment ───────────────────────────────────────
        phase(`Phase 2 of 2 — Aligning ${d1.new_jobs || 0} new jobs to your profile…`);
        const r2 = await fetch(`${API_BASE_URL}/jobs/align`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!r2.ok) throw new Error(`Alignment failed (${r2.status})`);
        const d2 = await r2.json();

        showToast(
            `Done! ${d1.new_jobs || 0} new jobs from ${d1.sources_searched || 0} sources · ` +
            `${d2.new_matches || 0} new matches (top score: ${d2.top_score || 0}%)`,
            'success'
        );
        currentJobFilter = 'all';
        loadJobFinder();

    } catch (err) {
        showToast('Refresh failed: ' + err.message, 'danger');
        if (container) container.innerHTML = `<div class="alert alert-danger m-3">Refresh failed: ${err.message}</div>`;
    } finally {
        setBtn('<i class="fas fa-sync me-2"></i>Refresh Jobs', false);
    }
}

// ── AI Deep Alignment (Phase 2 with LLM verification) ───────────────────────
async function runDeepAlignment() {
    if (!authToken) return;
    const btn = document.getElementById('deepCheckBtn');
    const container = document.getElementById('jobListContent');

    const originalText = btn ? btn.innerHTML : '';
    if (btn) { btn.innerHTML = '<i class="fas fa-brain fa-spin me-2"></i>Running AI Deep Check…'; btn.disabled = true; }
    if (container) container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-info mb-3" role="status" style="width:3rem;height:3rem;"></div>
            <h4 class="fw-bold">AI Deep Alignment in progress…</h4>
            <p class="text-muted">LLM is verifying your top job matches. Takes 1–3 minutes.</p>
        </div>`;

    try {
        const r = await fetch(`${API_BASE_URL}/jobs/align?deep_check=true`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!r.ok) throw new Error(`Deep check failed (${r.status})`);
        const d = await r.json();
        showToast(`AI verified ${d.deep_verified || 0} top matches (scored ${d.jobs_scored || 0} total)`, 'success');
        currentJobFilter = 'recommended';
        loadJobFinder();
    } catch (err) {
        showToast('Deep alignment failed: ' + err.message, 'danger');
    } finally {
        if (btn) { btn.innerHTML = originalText; btn.disabled = false; }
    }
}

// ── Load / display jobs (pure query — no ingestion) ──────────────────────────
async function loadJobFinder(page = 1) {
    console.log(`loadJobFinder called page=${page}`);
    const container = document.getElementById('jobListContent');
    const paginationContainer = document.getElementById('jobPagination');

    if (!container) {
        console.error('Job list container (#jobListContent) not found in DOM');
        return;
    }

    if (!authToken) {
        console.warn('loadJobFinder aborted: No authToken found');
        return;
    }

    // Get filter values from UI
    const locationFilterEl = document.getElementById('jobLocationFilter');
    const locationFilter = locationFilterEl ? locationFilterEl.value : '';
    const searchQueryEl = document.getElementById('jobSearchInput');
    const searchQuery = searchQueryEl ? searchQueryEl.value : '';

    // New filters
    const jobTypes = [];
    if (document.getElementById('filterTypePermanent')?.checked) jobTypes.push('Permanent');
    if (document.getElementById('filterTypeContract')?.checked) jobTypes.push('Contract');
    
    const workModes = [];
    if (document.getElementById('filterModeOnsite')?.checked) workModes.push('On-site');
    if (document.getElementById('filterModeHybrid')?.checked) workModes.push('Hybrid');
    if (document.getElementById('filterModeRemote')?.checked) workModes.push('Remote');
    
    const expLevel = document.getElementById('filterExpLevel')?.value || '';
    const daysOld = document.getElementById('filterDaysOld')?.value || '0';

    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
            <p class="text-muted mt-2">Searching ${currentJobFilter === 'recommended' ? 'your matches' : 'the full market'}…</p>
        </div>`;
    if (paginationContainer) paginationContainer.innerHTML = '';

    try {
        let url = `${API_BASE_URL}/jobs/search?page=${page}&size=20&filter_type=${currentJobFilter}&_t=${Date.now()}`;
        if (locationFilter) url += `&location_filter=${encodeURIComponent(locationFilter)}`;
        if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;
        
        // Add new filters as multi-select Query parameters
        if (jobTypes.length > 0) {
            jobTypes.forEach(t => url += `&job_types=${encodeURIComponent(t)}`);
        }
        if (workModes.length > 0) {
            workModes.forEach(m => url += `&work_modes=${encodeURIComponent(m)}`);
        }
        if (expLevel) {
            url += `&experience_level=${encodeURIComponent(expLevel)}`;
        }
        if (daysOld && daysOld !== '0') {
            url += `&days_old=${daysOld}`;
        }

        // Add source-level country filter if selected (optional)
        const countrySelect = document.getElementById('sourceCountrySelect');
        const selectedCountry = countrySelect ? countrySelect.value : '';
        if (selectedCountry) {
            url += `&source_country=${encodeURIComponent(selectedCountry)}`;
        }

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to fetch jobs');
        const data = await response.json();
        const jobs = data.jobs;

        if (jobs.length === 0) {
            const areaName = locationFilter ? `in ${locationFilter}` : '';
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-search-minus fa-3x text-muted mb-3 shadow-none opacity-25"></i>
                    <h4>No jobs captured yet ${areaName}</h4>
                    <p class="text-muted">Our latest market crawl (131 sources) didn't find any broad matches for this specific area yet.</p>
                    <div class="mt-4">
                        <button class="btn btn-primary" onclick="refreshJobs()">
                            <i class="fas fa-sync me-2"></i>Run AI Search for ${locationFilter || 'Switzerland'}
                        </button>
                    </div>
                </div>
            `;
            if (paginationContainer) paginationContainer.innerHTML = '';
            return;
        }

        let html = '<div class="row">';
        jobs.forEach(job => {
            html += `
                <div class="col-md-6 mb-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h5 class="card-title fw-bold mb-0">
                                    <a href="${job.url || job.application_url || '#'}" target="_blank" rel="noopener noreferrer" class="text-primary text-decoration-none"
                                       style="cursor:pointer" title="Open job posting">
                                        ${job.title}
                                    </a>
                                </h5>
                                <div class="d-flex flex-column align-items-end gap-1">
                                    ${currentJobFilter === 'all' ? '' : 
                                      `<span class="badge bg-success">Alignment: ${Math.round((job.score ?? (job.relevance_score !== undefined ? job.relevance_score / 100 : 0.75)) * 100)}%</span>`
                                    }
                                    ${job.is_verified ? '<span class="badge bg-primary"><i class="fas fa-check-circle me-1"></i>Verified</span>' : ''}
                                    <div class="d-flex gap-1 mt-1">

                                        <button class="btn btn-xs btn-outline-info py-0 px-2" style="font-size: 0.7rem;" onclick="prepareToApply(${job.id})">
                                            <i class="fas fa-magic"></i> Prep
                                        </button>
                                        <button class="btn btn-xs btn-outline-primary py-0 px-2" style="font-size: 0.7rem;" onclick="autoApply(${job.id})">
                                            <i class="fas fa-robot"></i> Auto
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <h6 class="card-subtitle mb-2 text-muted"><i class="fas fa-building me-1"></i>${job.company}</h6>
                            <p class="small text-muted mb-3"><i class="fas fa-map-marker-alt me-1"></i>${job.location || 'Remote'}</p>
                            <div class="d-flex flex-wrap gap-1 mb-3">
                                ${(job.skills_matched || []).slice(0, 3).map(s => `<span class="badge bg-light text-dark border extra-small">${s}</span>`).join('')}
                                ${(job.skills_matched || []).length > 3 ? `<span class="badge bg-light text-dark border extra-small">+${job.skills_matched.length - 3} more</span>` : ''}
                            </div>
                        </div>
                        <div class="card-footer bg-transparent border-0 pb-3">
                            <a href="${job.url || job.application_url || '#'}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary w-100 mb-2">
                                <i class="fas fa-external-link-alt me-1"></i>View Job
                            </a>
                            <button class="btn btn-sm btn-primary w-100" onclick="prepareToApply(${job.id})">
                                <i class="fas fa-magic me-2"></i>Prepare To Apply
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;

        // Render pagination
        renderJobPagination(data.page, data.pages, data.total);

    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        if (paginationContainer) paginationContainer.innerHTML = '';
    }
}

function renderJobPagination(currentPage, totalPages, totalJobs) {
    const container = document.getElementById('jobPagination');
    if (!container) return;

    if (totalPages <= 1) {
        container.innerHTML = `<div class="text-center text-muted small">Showing ${totalJobs} jobs</div>`;
        return;
    }

    let html = `
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
            <div class="text-muted small">Showing Page ${currentPage} of ${totalPages} (${totalJobs} jobs)</div>
            <nav>
                <ul class="pagination pagination-sm mb-0">
                    <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                        <button class="page-link" onclick="changeJobPage(${currentPage - 1})">Previous</button>
                    </li>
    `;

    // Show at most 5 page buttons
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <button class="page-link" onclick="changeJobPage(${i})">${i}</button>
            </li>
        `;
    }

    html += `
                    <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                        <button class="page-link" onclick="changeJobPage(${currentPage + 1})">Next</button>
                    </li>
                </ul>
            </nav>
        </div>
    `;
    container.innerHTML = html;
}

function changeJobPage(page) {
    loadJobFinder(page);
}

async function loadApplications() {
    const tableBody = document.getElementById('applicationTableBody');
    if (!authToken || !tableBody) return;

    try {
        const response = await fetch(`${API_BASE_URL}/applications`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to fetch applications');
        const applications = await response.json();
        
        if (applications.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-5">
                        <i class="fas fa-clipboard-list fa-3x text-muted mb-3 opacity-25"></i>
                        <p class="text-muted">No applications tracked yet. Add one above or from the Job Finder!</p>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = applications.map(app => {
            const statusClass = {
                'draft': 'bg-secondary',
                'prepared': 'bg-info',
                'applied': 'bg-success',
                'interviewing': 'bg-primary',
                'rejected': 'bg-danger'
            }[app.status] || 'bg-secondary';

            return `
                <tr>
                    <td class="ps-4" style="cursor: pointer;" onclick="openApplicationModal(${app.id})">
                        <div class="fw-bold text-primary">${app.job_title || (app.job_opportunity_id ? 'LinkedIn Job' : 'Manual URL')}</div>
                        <div class="small text-muted text-truncate" style="max-width: 250px;">
                            <i class="fas fa-building me-1"></i>${app.company_name || 'Manual Entry'} 
                            ${app.city ? `· <i class="fas fa-map-marker-alt ms-1 me-1"></i>${app.city}` : ''}
                        </div>
                        <div class="extra-small text-muted text-truncate mt-1" style="max-width: 250px; opacity: 0.7;">
                            ${app.application_url || 'Fetching details...'}
                        </div>
                    </td>
                    <td>
                        <div class="d-flex gap-2">
                            <span class="badge ${app.tailored_cv ? 'bg-success' : 'bg-light text-dark border'}">
                                <i class="fas ${app.tailored_cv ? 'fa-check' : 'fa-times'} me-1"></i>CV
                            </span>
                            <span class="badge ${app.cover_letter ? 'bg-success' : 'bg-light text-dark border'}">
                                <i class="fas ${app.cover_letter ? 'fa-check' : 'fa-times'} me-1"></i>CL
                            </span>
                        </div>
                    </td>
                    <td>
                        <button class="btn btn-sm ${app.status === 'applied' ? 'btn-outline-success' : 'btn-outline-primary'}" 
                                onclick="runAutoApply(${app.id})" ${app.status === 'applied' ? 'disabled' : ''}>
                            <i class="fas fa-robot me-1"></i>${app.status === 'applied' ? 'Applied' : 'Run Auto'}
                        </button>
                    </td>
                    <td>
                        <span class="badge ${statusClass}">${app.status.toUpperCase()}</span>
                        <div class="extra-small text-muted mt-1">${new Date(app.generated_at).toLocaleDateString()}</div>
                    </td>
                    <td class="text-end pe-4">
                        <div class="btn-group">
                            <button class="btn btn-sm btn-primary" onclick="openApplicationModal(${app.id})">
                                <i class="fas fa-edit me-1"></i>Prep
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteApplication(${app.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error: ${error.message}</td></tr>`;
    }
}

async function loadSocialEngine() {
    const container = document.getElementById('socialEngineContent');
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/social/analysis`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to fetch social analysis');
        const data = await response.json();
        
        let html = `
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-header bg-white border-bottom-0 pt-4">
                            <h5 class="fw-bold mb-0">Topic Categories</h5>
                        </div>
                        <div class="card-body">
                            <div class="list-group list-group-flush">
                                ${data.topic_categories.map(cat => `
                                    <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                                        ${cat.category}
                                        <span class="badge bg-primary rounded-pill">${cat.score}/10</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-8 mb-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-header bg-white border-bottom-0 pt-4">
                            <h5 class="fw-bold mb-0">AI Content Ideas</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                ${data.content_ideas.map(idea => `
                                    <div class="col-md-12 mb-3">
                                        <div class="p-3 border rounded">
                                            <div class="d-flex justify-content-between align-items-center mb-2">
                                                <h6 class="fw-bold mb-0">${idea.title}</h6>
                                                <span class="badge bg-info text-dark extra-small">${idea.platform}</span>
                                            </div>
                                            <p class="small text-muted mb-0">${idea.description}</p>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}

// Reset Profile Logic
function showResetConfirmModal() {
    if (!authToken) {
        showLoginModal();
        return;
    }
    const modal = new bootstrap.Modal(document.getElementById('resetConfirmModal'));
    modal.show();
}

async function confirmResetProfile() {
    const modalEl = document.getElementById('resetConfirmModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    
    try {
        const response = await fetch(`${API_BASE_URL}/profile/reset`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Failed to reset profile');
        
        modal.hide();
        showToast('Profile reset successfully! You can start fresh now.', 'success');
        
        // Refresh dashboard to show empty state
        loadDashboardData();
        
    } catch (error) {
        showToast('Error resetting profile: ' + error.message, 'danger');
    }
}

async function addManualApplication() {
    const urlInput = document.getElementById('manualJobUrl');
    const url = urlInput.value.trim();
    if (!url) {
        showToast('Please enter a valid job URL', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/applications`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ application_url: url, status: 'draft' })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(errorData.detail || 'Failed to add application');
        }
        
        urlInput.value = '';
        showToast('Job added to tracker!', 'success');
        loadApplications();
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

async function prepareToApply(jobId) {
    try {
        const response = await fetch(`${API_BASE_URL}/applications`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ job_opportunity_id: jobId, status: 'draft' })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
            throw new Error(errorData.detail || 'Failed to start preparation');
        }
        const application = await response.json();
        
        const appTab = document.querySelector('[data-bs-target="#tab-applications"]');
        if (appTab) appTab.click();
        
        loadApplications();
        openApplicationModal(application.id);
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

let currentApplicationId = null;
let currentApplication = null;
let currentProfileData = null;

async function openApplicationModal(id) {
    currentApplicationId = id;
    const modal = new bootstrap.Modal(document.getElementById('applicationModal'));
    
    // Clear fields
    const fields = ['cvEditorName', 'cvEditorTagline', 'cvEditorExpertise', 'cvEditorBody', 
                   'cvEditorLocation', 'cvEditorPhone', 'cvEditorEmail', 'cvEditorLinkedin',
                   'cvEditorDob', 'cvEditorNationality', 'cvEditorMarital', 'cvEditorWorkAuth',
                   'cvEditorLanguages', 'cvEditorItSkills', 'cvEditorCerts', 'clEditor', 'appNotes'];
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.value = '';
    });
    
    document.getElementById('appLoadingState').style.display = 'block';
    document.getElementById('appEditorState').style.display = 'none';
    
    modal.show();

    try {
        const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Failed to load application (${response.status})`);
        }
        const app = await response.json();
        currentApplication = app;

        if (!app) throw new Error('Application not found');

        // Fetch profile data to populate sidebar
        const profResponse = await fetch(`${API_BASE_URL}/dashboard`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        currentProfileData = await profResponse.json();
        const profileData = currentProfileData;
        
        // Populate Sidebar
        document.getElementById('cvEditorLocation').value = profileData.profile?.location || '';
        document.getElementById('cvEditorPhone').value = profileData.profile?.phone || '';
        document.getElementById('cvEditorEmail').value = profileData.user?.email || '';
        document.getElementById('cvEditorLinkedin').value = profileData.profile?.linkedin_url || '';
        document.getElementById('cvEditorDob').value = profileData.profile?.dob || '';
        document.getElementById('cvEditorNationality').value = profileData.profile?.nationality || '';
        document.getElementById('cvEditorMarital').value = profileData.profile?.marital_status || '';
        document.getElementById('cvEditorWorkAuth').value = profileData.profile?.work_auth || '';
        
        // Languages & IT Skills text format
        document.getElementById('cvEditorLanguages').value = (profileData.skills || [])
            .filter(s => s.category === 'language')
            .map(s => `${s.skill_name} (${s.proficiency || 'Intermediate'})`).join(', ');
        
        document.getElementById('cvEditorItSkills').value = (profileData.skills || [])
            .filter(s => s.category !== 'language')
            .map(s => s.skill_name).join(', ');

        // Photo
        const img = document.getElementById('cvEditorPhotoImg');
        const placeholder = document.getElementById('cvEditorPhotoPlaceholder');
        if (profileData.profile?.profile_picture_url) {
            img.src = `${API_BASE_URL}${profileData.profile.profile_picture_url}`;
            img.style.display = 'block';
            placeholder.style.display = 'none';
        } else {
            img.style.display = 'none';
            placeholder.style.display = 'block';
        }

        document.getElementById('appJobTitle').textContent = app.job_title || (app.job_opportunity_id ? 'Matched Job' : 'Manual Entry');
        document.getElementById('appJobCompany').textContent = (app.company_name || '') + (app.city ? ` - ${app.city}` : '');
        document.getElementById('appJobUrl').href = app.application_url || '#';
        document.getElementById('appStatusSelect').value = app.status;
        document.getElementById('appNotes').value = app.notes || '';

        // Load job description — show warning badge if missing or too short (placeholder text)
        const rawDesc = app.job_description || '';
        const descIsMeaningful = rawDesc.length > 150;
        document.getElementById('appJobDescription').value = descIsMeaningful ? rawDesc : '';
        const descBadge = document.getElementById('appJobDescStatus');
        if (!descIsMeaningful) {
            descBadge.style.display = 'inline';
        } else {
            descBadge.style.display = 'none';
        }
        
        // Check profile staleness
        const profileUpdatedAt = new Date(profileData.profile?.updated_at || profileData.user?.updated_at);
        const appGeneratedAt = new Date(app.generated_at);
        const staleAlert = document.getElementById('appStaleAlert');
        
        if (profileUpdatedAt > appGeneratedAt) {
            staleAlert.innerHTML = `
                <div class="alert alert-warning border-0 shadow-sm d-flex align-items-center mb-0 mt-3">
                    <i class="fas fa-exclamation-circle me-3 fa-lg"></i>
                    <div class="flex-grow-1">
                        <strong>Profile Updated:</strong> Your master profile has changed. Regenerate to sync these materials.
                    </div>
                    <button class="btn btn-warning btn-sm fw-bold ms-3" onclick="reprepareMaterials()">
                        <i class="fas fa-redo me-1"></i>Regenerate
                    </button>
                </div>
            `;
            staleAlert.style.display = 'block';
        } else {
            staleAlert.style.display = 'none';
        }

        // 2. Show existing materials if available, else auto-trigger AI generation
        if (app.tailored_cv) {
            populateCVEditorFields(app.tailored_cv, profileData);
            document.getElementById('clEditor').value = app.cover_letter || '';
            document.getElementById('appLoadingState').style.display = 'none';
            document.getElementById('appEditorState').style.display = 'block';
        } else {
            // No materials yet — auto-generate
            await reprepareMaterials(true);
        }
    } catch (error) {
        showToast(error.message, 'danger');
        modal.hide();
    }
}

function populateCVEditorFields(fullMarkdown, profileData = null) {
    if (!fullMarkdown) return;
    
    // 1. Extract Name & Tagline for headers
    const nameMatch = fullMarkdown.match(/^# (.*)/m);
    let name = nameMatch ? nameMatch[1].trim() : '';
    let tagline = '';
    
    if (nameMatch) {
        const headerLines = fullMarkdown.substring(nameMatch.index + nameMatch[0].length).split('\n');
        for (let line of headerLines) {
            const trimmed = line.trim();
            if (trimmed && !trimmed.startsWith('#')) {
                tagline = trimmed;
                break;
            }
        }
    }
    
    if (!name && profileData) name = profileData.user?.full_name || '';
    if (!tagline && profileData) tagline = profileData.profile?.desired_job_title || '';
    
    // 2. Multi-section parsing with synonym support
    const rawSections = {};
    const sectionRegex = /^\s*#+\s*([^#\n]+)\s*$/gm;
    let match;
    const matches = [];
    while ((match = sectionRegex.exec(fullMarkdown)) !== null) {
        matches.push({ title: match[1].trim().toUpperCase(), index: match.index, line: match[0] });
    }

    for (let i = 0; i < matches.length; i++) {
        const start = matches[i].index + matches[i].line.length;
        const end = (i + 1 < matches.length) ? matches[i+1].index : fullMarkdown.length;
        rawSections[matches[i].title] = fullMarkdown.substring(start, end).trim();
    }
    
    const getSection = (synonyms) => {
        for (let s of synonyms) {
            if (rawSections[s]) return rawSections[s];
        }
        return '';
    };

    // 3. Map Content to UI Sections
    const exp = getSection(['PROFESSIONAL EXPERIENCE', 'EXPERIENCE', 'WORK HISTORY', 'WORK EXPERIENCE']);
    const edu = getSection(['EDUCATION', 'ACADEMIC BACKGROUND', 'QUALIFICATIONS']);
    const sum = getSection(['EXPERTISE', 'EXECUTIVE SUMMARY', 'SUMMARY', 'PROFESSIONAL SUMMARY', 'PROFILE']);
    const skills = getSection(['SKILLS / STRENGTHS', 'STRENGTHS', 'SKILLS', 'IT SKILLS', 'TECHNICAL SKILLS']);
    
    // 4. Populating UI with Fallbacks (using correct plural names from backend)
    document.getElementById('cvEditorName').value = name;
    document.getElementById('cvEditorTagline').value = sanitizeText(tagline);
    document.getElementById('cvEditorExpertise').value = sanitizeText(sum || (profileData ? profileData.profile?.summary : ''));
    
    // Set Alignment Header
    const jobLabel = document.getElementById('cvTargetLabel');
    if (jobLabel) {
        jobLabel.textContent = `${sanitizeText(tagline) || 'Target Role'}`;
    }

    document.getElementById('cvEditorExperience').value = normalizeExperienceDates(exp) || (profileData && profileData.experiences ? buildMasterExperienceMarkdown(profileData.experiences) : '');
    document.getElementById('cvEditorEducation').value = edu || (profileData && profileData.educations ? buildMasterEducationMarkdown(profileData.educations) : '');
    
    // Skills Fallback
    let skillsVal = skills;
    if (!skillsVal && profileData && profileData.skills) {
        skillsVal = profileData.skills.map(s => s.skill_name).join(', ');
    }
    document.getElementById('cvEditorSkills').value = skillsVal || '';

    // Sidebar and Photo population
    if (profileData) {
        document.getElementById('cvEditorLocation').value = profileData.profile?.location || '';
        document.getElementById('cvEditorPhone').value = (profileData.profile?.phone || profileData.user?.phone) || '';
        document.getElementById('cvEditorEmail').value = profileData.user?.email || '';
        document.getElementById('cvEditorLinkedin').value = profileData.profile?.linkedin_url || '';
        
        const img = document.getElementById('cvEditorPhotoImg');
        const placeholder = document.getElementById('cvEditorPhotoPlaceholder');
        if (img && placeholder) {
            if (profileData.profile?.profile_picture_url) {
                img.src = `${API_BASE_URL}${profileData.profile.profile_picture_url}`;
                img.style.display = 'block';
                placeholder.style.display = 'none';
            } else {
                img.style.display = 'none';
                placeholder.style.display = 'flex';
            }
        }
    }
}

function normalizeExperienceDates(text) {
    if (!text) return text;
    // "YYYY-MM" or "YYYY/MM" → "YYYY" (handles ranges like "2025-01 - 2026-01" → "2025 - 2026")
    return text.replace(/(\d{4})[-\/]\d{2}/g, '$1');
}

function sanitizeText(text) {
    if (!text) return "";
    // Handle common UTF-8 Misinterpretations (Â€“ -> –, etc.)
    return text.replace(/Â€“/g, "–")
               .replace(/Â\s/g, " ")
               .replace(/â€“/g, "–")
               .replace(/â€"/g, "—")
               .replace(/â€™/g, "'")
               .replace(/â€œ/g, '"')
               .replace(/â€/g, '"');
}

function buildMasterExperienceMarkdown(experienceList) {
    if (!experienceList) return "";
    const formatDate = (dateStr) => {
        if (!dateStr) return "";
        try {
            return dateStr.split('T')[0].substring(0, 4); // Returns YYYY only
        } catch (e) { return dateStr; }
    };
    
    return experienceList.map(exp => {
        const title = sanitizeText(exp.position || exp.title || 'Role');
        const company = sanitizeText(exp.company);
        const desc = sanitizeText(exp.description);
        return `${title.toUpperCase()} | ${company} | ${formatDate(exp.start_date)} - ${exp.is_current ? 'Present' : formatDate(exp.end_date)}\n${desc}`;
    }).join('\n\n');
}

function buildMasterEducationMarkdown(educationList) {
    if (!educationList) return "";
    const formatDate = (dateStr) => {
        if (!dateStr) return "";
        try {
            return dateStr.split('T')[0].substring(0, 4); // Returns YYYY only
        } catch (e) { return dateStr; }
    };

    return educationList.map(edu => {
        const deg = sanitizeText(edu.degree || 'Degree');
        const inst = sanitizeText(edu.institution);
        return `${deg.toUpperCase()} | ${inst} | ${formatDate(edu.end_date) || edu.completion_year || ''}`;
    }).join('\n\n');
}

function assembleMarkdownFromEditor() {
    const name = document.getElementById('cvEditorName').value;
    const tagline = document.getElementById('cvEditorTagline').value;
    const expertise = document.getElementById('cvEditorExpertise').value;
    const experience = document.getElementById('cvEditorExperience').value;
    const education = document.getElementById('cvEditorEducation').value;
    const skills = document.getElementById('cvEditorSkills').value;
    
    let md = `# ${name}\n${tagline}\n\n`;
    
    // Re-add hidden but necessary metadata sections for PDF engine
    md += `## CONTACT\n`;
    md += `- Location: ${document.getElementById('cvEditorLocation').value}\n`;
    md += `- Phone: ${document.getElementById('cvEditorPhone').value}\n`;
    md += `- Email: ${document.getElementById('cvEditorEmail').value}\n`;
    md += `- LinkedIn: ${document.getElementById('cvEditorLinkedin').value}\n\n`;

    md += `## PERSONAL\n`;
    md += `- Date of Birth: ${document.getElementById('cvEditorDob').value}\n`;
    md += `- Nationality: ${document.getElementById('cvEditorNationality').value}\n\n`;

    // The core sections edited by user
    md += `## EXPERTISE\n${expertise}\n\n`;
    md += `## PROFESSIONAL EXPERIENCE\n${experience}\n\n`;
    md += `## EDUCATION\n${education}\n\n`;
    md += `## SKILLS / STRENGTHS\n${skills}\n\n`;
    
    // Re-add IT Skills and Langs for completeness if they exist in sidebar
    md += `## IT SKILLS\n${document.getElementById('cvEditorItSkills').value}\n\n`;
    
    return md;
}

function _showDescriptionRequiredError(detail) {
    /**
     * Display a prominent, in-modal error block when the backend cannot obtain
     * the job description automatically. Points the user to the paste textarea.
     */
    const scrapeStatus = detail?.scrape_status || 'unknown';
    const userMessage = detail?.message || 'The job description could not be retrieved automatically.';
    const jobUrl = detail?.url;

    // Icon and label per status
    const iconMap = {
        auth_required: 'fa-lock',
        not_found:     'fa-unlink',
        too_short:     'fa-file-slash',
        empty:         'fa-circle-exclamation',
        no_url:        'fa-link-slash',
        error:         'fa-triangle-exclamation',
        unknown:       'fa-triangle-exclamation',
    };
    const icon = iconMap[scrapeStatus] || 'fa-triangle-exclamation';

    // Build action hint
    let actionHint = '';
    if (jobUrl) {
        actionHint = `
            <div class="mt-2">
                <a href="${jobUrl}" target="_blank" class="btn btn-sm btn-outline-secondary me-2">
                    <i class="fas fa-external-link-alt me-1"></i>Open Job Posting
                </a>
                <span class="text-muted small">→ copy the description → paste below</span>
            </div>`;
    }

    // Inject the error block above the Job Description textarea
    const descContainer = document.getElementById('appJobDescription')?.closest('.mb-3');
    if (descContainer) {
        // Remove any existing error block first
        const existing = descContainer.querySelector('.desc-error-block');
        if (existing) existing.remove();

        const errorDiv = document.createElement('div');
        errorDiv.className = 'desc-error-block alert alert-danger border-danger shadow-sm mb-2 p-3';
        errorDiv.innerHTML = `
            <div class="d-flex align-items-start gap-2">
                <i class="fas ${icon} fa-lg mt-1 flex-shrink-0"></i>
                <div>
                    <strong>Job description required before AI can tailor your CV</strong>
                    <p class="mb-0 mt-1 small">${userMessage}</p>
                    ${actionHint}
                </div>
            </div>`;
        descContainer.insertBefore(errorDiv, descContainer.firstChild);
    }

    // Also show the missing badge
    const descBadge = document.getElementById('appJobDescStatus');
    if (descBadge) {
        descBadge.textContent = '⚠ Job description required';
        descBadge.className = 'badge bg-danger ms-2 small';
        descBadge.style.display = 'inline';
    }

    // Scroll to and highlight the textarea
    const textarea = document.getElementById('appJobDescription');
    if (textarea) {
        textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
        textarea.classList.add('border-danger');
        textarea.focus();
        // Remove red border once the user starts typing
        textarea.addEventListener('input', () => {
            textarea.classList.remove('border-danger');
            const errBlock = textarea.closest('.mb-3')?.querySelector('.desc-error-block');
            if (errBlock) errBlock.remove();
        }, { once: true });
    }
}

async function reprepareMaterials(skipConfirm = false) {
    if (!currentApplicationId) return;

    // If called explicitly by user (not auto-triggered) and materials already exist, confirm first
    if (!skipConfirm && currentApplication && currentApplication.tailored_cv) {
        const confirmed = confirm('This will replace your existing CV and Cover Letter with a freshly AI-generated version. Continue?');
        if (!confirmed) return;
    }

    // UI Loading State with "AI Consultant" status
    const loadingEl = document.getElementById('appLoadingState');
    const editorEl = document.getElementById('appEditorState');
    const loadingText = loadingEl.querySelector('p');
    
    loadingEl.style.display = 'block';
    editorEl.style.display = 'none';
    
    if (loadingText) {
        loadingText.innerHTML = `
            <div class="d-flex flex-column align-items-center">
                <i class="fas fa-brain fa-3x mb-3 text-primary fa-pulse"></i>
                <div class="h5">AI Career Consultant is Working...</div>
                <div class="text-muted small">Phase 1-4: Analyze → Write → Audit → Refine</div>
                <div class="mt-2 badge bg-primary text-white">Multi-Agent Strategy Active</div>
            </div>
        `;
    }

    try {
        // Include any pasted job description so the AI can tailor the CV properly
        const pastedDesc = (document.getElementById('appJobDescription')?.value || '').trim();
        const prepBody = pastedDesc ? JSON.stringify({ job_description: pastedDesc }) : null;

        const response = await fetch(`${API_BASE_URL}/applications/${currentApplicationId}/prepare`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                ...(prepBody ? { 'Content-Type': 'application/json' } : {})
            },
            body: prepBody
        });

        // Hide the missing-description badge once prep starts (user has provided it or is retrying)
        const descBadge = document.getElementById('appJobDescStatus');
        if (descBadge) descBadge.style.display = 'none';

        if (!response.ok) {
            // Parse the error body — it may contain structured detail
            let errBody = null;
            try { errBody = await response.json(); } catch (_) {}
            const detail = errBody?.detail;

            if (response.status === 422 && detail?.error_code === 'description_required') {
                // Switch to editor state first (so scrollIntoView works), then inject error
                document.getElementById('appLoadingState').style.display = 'none';
                document.getElementById('appEditorState').style.display = 'block';
                _showDescriptionRequiredError(detail);
                return;
            }
            if (response.status === 429) {
                throw new Error('Gemini Rate Limit: The AI is busy. Please wait 60s and try again.');
            }
            if (response.status === 504 || response.status === 502) {
                throw new Error('AI Timeout: The refinement loop took too long. Try smaller edits.');
            }
            const msg = (typeof detail === 'string' ? detail : detail?.message) || 'AI preparation failed.';
            throw new Error(msg);
        }
        const result = await response.json();
        
        // We need the profileData to correctly populate fields with fallbacks
        // This assumes profileData is available in the scope, or passed as an argument.
        // For now, let's assume it's available globally or from a parent scope.
        // If not, it would need to be fetched or passed.
        // For this change, we'll use the existing `profileData` variable from `openApplicationModal`'s scope.
        if (currentApplication && currentApplication.id === currentApplicationId) { 
            currentApplication.tailored_cv = result.tailored_cv;
            currentApplication.cover_letter = result.cover_letter;
            currentApplication.cv_path = result.cv_path;
            currentApplication.cl_path = result.cl_path;
            
            // Refresh editor with new AI-tailored content
            populateCVEditorFields(result.tailored_cv, currentProfileData); 
            document.getElementById('clEditor').value = result.cover_letter || '';
        }
        
        document.getElementById('appLoadingState').style.display = 'none';
        document.getElementById('appEditorState').style.display = 'block';
        
        // Clear any description-required error block and stale alert
        document.querySelectorAll('.desc-error-block').forEach(el => el.remove());
        const descBadgeSuccess = document.getElementById('appJobDescStatus');
        if (descBadgeSuccess) descBadgeSuccess.style.display = 'none';
        const descInput = document.getElementById('appJobDescription');
        if (descInput) descInput.classList.remove('border-danger');
        document.getElementById('appStaleAlert').style.display = 'none';

        showToast('Materials tailored successfully!', 'success');
    } catch (error) {
        console.error('Preparation error:', error);
        showErrorPopup('Career Consultant Error', error.message || 'The AI Agent encountered an issue during the refinement loop.');
        document.getElementById('appLoadingState').style.display = 'none';
        document.getElementById('appEditorState').style.display = 'block';
    }
}

async function saveApplicationChanges() {
    if (!currentApplicationId) return;

    const btn = document.querySelector('#applicationModal .btn-primary[onclick*="saveApplicationChanges"]');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Regenerating PDFs...';
    btn.disabled = true;

    const updates = {
        status: document.getElementById('appStatusSelect').value,
        notes: document.getElementById('appNotes').value,
        tailored_cv: assembleMarkdownFromEditor(),
        cover_letter: document.getElementById('clEditor').value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/applications/${currentApplicationId}`, {
            method: 'PATCH',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        if (!response.ok) throw new Error('Failed to save changes');
        
        const updatedApp = await response.json();
        
        // Update local currentApplication object so Download Materials uses new paths
        currentApplication = updatedApp;
        
        showToast('Application updated and PDFs regenerated!', 'success');
        loadApplications();
        bootstrap.Modal.getInstance(document.getElementById('applicationModal')).hide();
    } catch (error) {
        showToast(error.message, 'danger');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTO-APPLY SETTINGS
// ─────────────────────────────────────────────────────────────────────────────

function selectLLMProvider(provider) {
    document.getElementById('aaLlmProvider').value = provider;
    const geminiBtn = document.getElementById('providerGemini');
    const claudeBtn = document.getElementById('providerClaude');
    const hint = document.getElementById('providerApiKeyHint');
    if (provider === 'gemini') {
        geminiBtn.style.border = '2px solid #4285f4';
        geminiBtn.style.color = '#4285f4';
        geminiBtn.style.background = '#f0f7ff';
        claudeBtn.style.border = '2px solid #ccc';
        claudeBtn.style.color = '#888';
        claudeBtn.style.background = '#fff';
        if (hint) hint.style.display = 'none';
    } else {
        claudeBtn.style.border = '2px solid #c76b00';
        claudeBtn.style.color = '#c76b00';
        claudeBtn.style.background = '#fff8f0';
        geminiBtn.style.border = '2px solid #ccc';
        geminiBtn.style.color = '#888';
        geminiBtn.style.background = '#fff';
        if (hint) hint.style.display = 'block';
    }
}

async function loadAutoApplySettings() {
    try {
        const resp = await fetch(`${API_BASE_URL}/auto-apply/settings`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();

        const alert = document.getElementById('autoApplySettingsAlert');

        if (data.configured) {
            if (data.linkedin_url) document.getElementById('aaLinkedinUrl').value = data.linkedin_url;
            if (data.linkedin_username) document.getElementById('aaLinkedinUser').value = data.linkedin_username;
            if (data.email_username) document.getElementById('aaEmailUser').value = data.email_username;
            if (data.linkedin_password_set) document.getElementById('aaLinkedinPass').placeholder = '••••••••';
            if (data.email_password_set) document.getElementById('aaEmailPass').placeholder = '••••••••';
            if (alert) {
                alert.textContent = '✓ Credentials configured. Leave password blank to keep existing.';
                alert.className = 'alert alert-success py-2 small mb-3';
                alert.style.display = 'block';
            }
            // Restore provider selection
            if (data.llm_provider) selectLLMProvider(data.llm_provider);
        }

        // Load portal accounts
        await loadAutoApplyAccounts();
    } catch (e) {
        console.warn('Could not load auto-apply settings:', e.message);
    }
}

async function saveAutoApplySettings() {
    const payload = {
        linkedin_url: document.getElementById('aaLinkedinUrl').value.trim() || null,
        linkedin_username: document.getElementById('aaLinkedinUser').value.trim() || null,
        email_username: document.getElementById('aaEmailUser').value.trim() || null,
        llm_provider: document.getElementById('aaLlmProvider').value || 'gemini',
    };

    const liPass = document.getElementById('aaLinkedinPass').value;
    const emPass = document.getElementById('aaEmailPass').value;
    if (liPass) payload.linkedin_password = liPass;
    if (emPass) payload.email_password = emPass;

    try {
        const resp = await fetch(`${API_BASE_URL}/auto-apply/settings`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) throw new Error('Failed to save');

        // Clear password fields after save
        document.getElementById('aaLinkedinPass').value = '';
        document.getElementById('aaEmailPass').value = '';
        document.getElementById('aaLinkedinPass').placeholder = '••••••••';
        document.getElementById('aaEmailPass').placeholder = '••••••••';

        const alert = document.getElementById('autoApplySettingsAlert');
        if (alert) {
            alert.textContent = '✓ Credentials saved securely with encryption.';
            alert.className = 'alert alert-success py-2 small mb-3';
            alert.style.display = 'block';
        }
        showToast('Auto-apply credentials saved securely!', 'success');
    } catch (e) {
        showToast('Error saving credentials: ' + e.message, 'danger');
    }
}

async function loadAutoApplyAccounts() {
    try {
        const resp = await fetch(`${API_BASE_URL}/auto-apply/accounts`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const accounts = await resp.json();
        const container = document.getElementById('autoApplyAccountsContainer');
        if (!container) return;

        if (accounts.length === 0) {
            container.innerHTML = '<p class="text-muted small text-center py-2">No accounts created yet.</p>';
            return;
        }

        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm small mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Platform</th>
                            <th>Username</th>
                            <th>Password</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${accounts.map(a => `
                            <tr>
                                <td>
                                    ${a.platform_url ? `<a href="${a.platform_url}" target="_blank" class="text-primary text-decoration-none">${a.platform_name}</a>` : a.platform_name}
                                </td>
                                <td class="font-monospace">${a.username || '—'}</td>
                                <td class="font-monospace">
                                    <span class="d-none" id="pwd-${a.id}">${a.password || '—'}</span>
                                    <span id="pwd-mask-${a.id}">••••••</span>
                                    <button class="btn btn-link btn-sm p-0 ms-1" onclick="togglePwd(${a.id})" title="Show/Hide">
                                        <i class="fas fa-eye small text-muted"></i>
                                    </button>
                                </td>
                                <td class="text-muted">${new Date(a.created_at).toLocaleDateString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        console.warn('Could not load auto-apply accounts:', e.message);
    }
}

function togglePwd(id) {
    const pwd = document.getElementById(`pwd-${id}`);
    const mask = document.getElementById(`pwd-mask-${id}`);
    if (!pwd || !mask) return;
    const hidden = pwd.classList.contains('d-none');
    pwd.classList.toggle('d-none', !hidden);
    mask.classList.toggle('d-none', hidden);
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTO-APPLY RUN & INTERVENTION LOOP
// ─────────────────────────────────────────────────────────────────────────────

let _interventionPollTimer = null;
let _interventionAppId = null;
let _autoApplyRunning = false;  // guard against double-click

async function runAutoApply(id) {
    const appId = id || currentApplicationId;
    if (!appId) return;

    // Prevent double-click spawning two browser windows
    if (_autoApplyRunning) {
        showToast('Auto-apply is already running. Please wait for it to complete.', 'warning');
        return;
    }

    if (!confirm('Start automated application process for this job?\n\nA browser window will open. Keep it visible — the automation needs to see the page.')) return;

    _autoApplyRunning = true;

    // Show live log panel inside the modal if open
    _startInterventionPoll(appId);

    showToast('🤖 Auto-Apply started! Watch the browser window that opens...', 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/applications/${appId}/apply`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            // 409 = already running server-side
            if (response.status === 409) {
                showToast('⚠️ Auto-apply is already running for this job on the server. Check the browser window.', 'warning');
                _autoApplyRunning = false;
                return;
            }
            throw new Error(errData.detail || `Auto-apply failed to start (${response.status})`);
        }
        const data = await response.json();

        if (data.status === 'applied') {
            showToast('✅ Application submitted successfully!', 'success');
            _stopInterventionPoll();
            loadApplications();
            await loadAutoApplyAccounts();
        } else if (data.status === 'intervention') {
            // Show the message immediately — poll will keep updating
            if (data.message) showToast(`⚠️ ${data.message}`, 'warning');
            loadApplications();
        } else {
            showToast(data.message || 'Auto-apply ended.', 'info');
            _stopInterventionPoll();
            loadApplications();
        }
    } catch (error) {
        showToast(error.message, 'danger');
        _stopInterventionPoll();
    } finally {
        _autoApplyRunning = false;
    }
}

function _startInterventionPoll(appId) {
    _stopInterventionPoll();
    _interventionAppId = appId;
    _interventionPollTimer = setInterval(() => _pollStatus(appId), 3000);
}

function _stopInterventionPoll() {
    if (_interventionPollTimer) {
        clearInterval(_interventionPollTimer);
        _interventionPollTimer = null;
    }
    _interventionAppId = null;
}

async function _pollStatus(appId) {
    try {
        const resp = await fetch(`${API_BASE_URL}/applications/${appId}/status`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.status === 'requires_intervention') {
            _stopInterventionPoll();
            showInterventionModal(appId, data.intervention_message, data.log);
            // Also fire a toast
            showToast(`⚠️ Auto-apply needs your help: ${(data.intervention_message || '').substring(0, 60)}...`, 'warning');
        } else if (data.status === 'applied') {
            _stopInterventionPoll();
            showToast('✅ Application submitted successfully!', 'success');
            loadApplications();
            await loadAutoApplyAccounts();
        }
    } catch (e) {
        // Silently ignore poll errors
    }
}

function showInterventionModal(appId, message, logLines) {
    _interventionAppId = appId;

    const msgEl = document.getElementById('interventionMessage');
    if (msgEl) msgEl.textContent = message || 'The automation needs your input.';

    // Render log
    const logEl = document.getElementById('interventionLog');
    if (logEl && logLines) {
        logEl.innerHTML = (logLines || []).map(l => `<div>› ${l}</div>`).join('');
        logEl.scrollTop = logEl.scrollHeight;
    }

    // Show input field if message suggests a code is needed
    const needsInput = message && (
        message.toLowerCase().includes('captcha') ||
        message.toLowerCase().includes('code') ||
        message.toLowerCase().includes('2fa') ||
        message.toLowerCase().includes('verification')
    );
    const inputArea = document.getElementById('interventionInputArea');
    if (inputArea) inputArea.style.display = needsInput ? 'block' : 'none';

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('interventionModal'));
    modal.show();
}

async function submitIntervention(action) {
    const appId = _interventionAppId;
    if (!appId) return;

    const inputData = document.getElementById('interventionInputData')?.value || '';
    try {
        const resp = await fetch(`${API_BASE_URL}/applications/${appId}/intervention`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action, intervention_data: inputData })
        });
        if (!resp.ok) throw new Error('Failed to send intervention');

        // Close modal
        const modalEl = document.getElementById('interventionModal');
        bootstrap.Modal.getInstance(modalEl)?.hide();

        if (action === 'abort') {
            showToast('Automation aborted.', 'info');
            _stopInterventionPoll();
            loadApplications();
        } else {
            showToast('Resuming automation...', 'info');
            _startInterventionPoll(appId);
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'danger');
    }
}


async function deleteApplication(id) {
    if (!confirm('Are you sure you want to remove this application from the tracker?')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) throw new Error('Failed to delete');
        
        showToast('Application removed', 'success');
        loadApplications();
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

function downloadMaterials() {
    console.log('downloadMaterials triggered');
    console.log('Current Application State:', currentApplication);

    if (currentApplication && currentApplication.cv_path && currentApplication.cl_path) {
        console.log('PDF Branch: Attempting to download high-fidelity files');
        const cvUrl = `${API_BASE_URL}/${currentApplication.cv_path.replace(/\\/g, '/')}`;
        const clUrl = `${API_BASE_URL}/${currentApplication.cl_path.replace(/\\/g, '/')}`;
        
        console.log('CV URL:', cvUrl);
        console.log('CL URL:', clUrl);

        // Open CV
        const a1 = document.createElement('a');
        a1.href = cvUrl;
        a1.download = cvUrl.split('/').pop();
        a1.target = '_blank';
        a1.click();
        
        // Open CL after short delay to avoid popup blockers
        setTimeout(() => {
            const a2 = document.createElement('a');
            a2.href = clUrl;
            a2.download = clUrl.split('/').pop();
            a2.target = '_blank';
            a2.click();
        }, 500);
        
        showToast('Downloading high-fidelity PDFs...', 'success');
        return;
    }

    console.warn('TXT Fallback Branch: No PDF paths found in currentApplication');
    // Fallback to legacy TXT if PDFs not generated
    const cv = document.getElementById('cvEditor').value;
    const cl = document.getElementById('clEditor').value;
    const content = `TAILORED CV HIGHLIGHTS:\n\n${cv}\n\n====================\n\nCOVER LETTER:\n\n${cl}`;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Application_Materials_${currentApplicationId || 'unknown'}.txt`;
    a.click();
}

async function vetSources() {
    if (!authToken) return;
    
    const btn = document.getElementById('vetSourcesBtn');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Vetting URLs...';
    btn.disabled = true;

    try {
        showToast('Starting deep URL vetting. This uses AI to find exact career pages from company homepages.', 'info');
        
        const response = await fetch(`${API_BASE_URL}/jobs/sources/vet`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Vetting failed');
        
        const result = await response.json();
        showToast(`Vetting complete! Updated ${result.updated} sources with exact career URLs.`, 'success');
        loadJobSources();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

window.prepareToApply = prepareToApply;
window.addManualApplication = addManualApplication;
window.openApplicationModal = openApplicationModal;
window.reprepareMaterials = reprepareMaterials;
window.saveApplicationChanges = saveApplicationChanges;
window.runAutoApply = runAutoApply;
window.deleteApplication = deleteApplication;
window.downloadMaterials = downloadMaterials;
window.loadApplications = loadApplications;
async function autoApplyFromFinder(jobId) {
    try {
        const response = await fetch(`${API_BASE_URL}/applications`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ job_opportunity_id: jobId, status: 'draft' })
        });

        if (!response.ok) throw new Error('Failed to start auto-apply');
        const application = await response.json();
        
        // Refresh and switch
        loadApplications();
        const appTab = document.querySelector('[data-bs-target="#tab-applications"]');
        if (appTab) appTab.click();
        
        // Run auto-apply
        runAutoApply(application.id);
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

// --- GLOBAL EXPORTS ---
// These functions are attached to the window object so they can be 
// accessed by inline onclick handlers in index.html

// Navigation & Auth
window.handleHashChange = handleHashChange;
window.switchMainTab = switchMainTab;
window.logout = logout;
window.showLoginModal = showLoginModal;
window.showRegisterModal = showRegisterModal;

// Profile & Dashboard
window.loadDashboardData = loadDashboardData;
window.showFullProfile = showFullProfile;
window.showFullProfileTab = showFullProfileTab;
window.saveQuickPreferences = saveQuickPreferences;
window.addNewSkill = addNewSkill;
window.deleteSkill = deleteSkill;
window.addExperienceEntry = addExperienceEntry;
window.toggleEditExp = toggleEditExp;
window.saveExperience = saveExperience;
window.deleteExperience = deleteExperience;
window.addEducationEntry = addEducationEntry;
window.toggleEditEdu = toggleEditEdu;
window.saveEducation = saveEducation;
window.deleteEducation = deleteEducation;
window.confirmResetProfile = confirmResetProfile;
window.showResetConfirmModal = showResetConfirmModal;

// Job Finder
window.loadJobFinder = loadJobFinder;
window.refreshJobs = refreshJobs;
window.runDeepAlignment = runDeepAlignment;
window.runTargetScoring = runTargetScoring;
window.switchJobFilter = switchJobFilter;
window.toggleAISettings = toggleAISettings;
window.saveAISettings = saveAISettings;
window.changeJobPage = changeJobPage;
window.prepareToApply = prepareToApply;
window['autoApply'] = autoApplyFromFinder;

// Apply Engine
window.loadApplications = loadApplications;
window.addManualApplication = addManualApplication;
window.openApplicationModal = openApplicationModal;
window.reprepareMaterials = reprepareMaterials;
window.downloadMaterials = downloadMaterials;
window.saveApplicationChanges = saveApplicationChanges;
window.runAutoApply = runAutoApply;
window.deleteApplication = deleteApplication;

// Auto-Apply Settings & Intervention
window.saveAutoApplySettings = saveAutoApplySettings;
window.loadAutoApplySettings = loadAutoApplySettings;
window.loadAutoApplyAccounts = loadAutoApplyAccounts;
window.togglePwd = togglePwd;
window.showInterventionModal = showInterventionModal;
window.submitIntervention = submitIntervention;

// Documents
window.showUploadModal = showUploadModal;
window.uploadDocument = uploadDocument;
window.toggleUploadMode = toggleUploadMode;
window.deleteSelectedDocuments = deleteSelectedDocuments;

// Sources
window.loadJobSources = loadJobSources;
window.showAddSourceModal = showAddSourceModal;
window.showEditSourceModal = showEditSourceModal;
window.deleteJobSource = deleteJobSource;
window.toggleSourceActive = toggleSourceActive;
window.runSourcing = runSourcing;
window.vetSources = vetSources;

// Social
window.loadSocialEngine = loadSocialEngine;
window.runTargetScoring = runTargetScoring;

console.log('Application exports completed.');
// --- TARGET SCORING DECOUPLING ---
async function runTargetScoring() {
    const btn = document.getElementById('targetScoringBtn');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Scoring...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/score`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) throw new Error('Target scoring failed');
        const data = await response.json();
        
        showToast(`Successfully matched ${data.scored_count} jobs to your profile!`, 'success');
        
        // Automatic switch to My Matches (recommended) after scoring
        switchJobFilter('recommended');
        
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        
    } catch (error) {
        console.error('Target scoring error:', error);
        showToast('Error during target scoring: ' + error.message, 'danger');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ── LinkedIn Tab ─────────────────────────────────────────────────────────────


async function loadLinkedIn() {
    await refreshLinkedInStatus();
}

async function refreshLinkedInStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/linkedin/status`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        applyLinkedInStatus(data);
        if (data.connected && !data.stale) {
            liCurrentPage = 1;
            await loadLinkedInJobs(1);
        }
    } catch (e) {
        console.error('LinkedIn status error:', e);
    }
}

function applyLinkedInStatus(data) {
    const badge = document.getElementById('liStatusBadge');
    const connectCard = document.getElementById('liConnectCard');
    const sessionCard = document.getElementById('liSessionCard');
    const emailInput = document.getElementById('liEmail');
    const pwInput = document.getElementById('liPassword');

    if (data.connected && !data.stale) {
        badge.className = 'badge bg-success fs-6 px-3 py-2';
        badge.innerHTML = '<i class="fab fa-linkedin me-1"></i> Connected';
        connectCard.classList.add('d-none');
        sessionCard.classList.remove('d-none');
        document.getElementById('liProfileName').textContent = data.profile_name || 'LinkedIn Account';
        document.getElementById('liLastLogin').textContent = data.last_login
            ? new Date(data.last_login).toLocaleDateString() : '—';
        document.getElementById('liLastFetch').textContent = data.last_fetch
            ? new Date(data.last_fetch).toLocaleDateString() : 'Never';
    } else {
        badge.className = 'badge bg-secondary fs-6 px-3 py-2';
        badge.innerHTML = data.stale
            ? '<i class="fas fa-exclamation-circle me-1"></i> Session expired'
            : '<i class="fas fa-circle me-1"></i> Not connected';
        connectCard.classList.remove('d-none');
        sessionCard.classList.add('d-none');

        if (data.has_credentials) {
            emailInput.value = 'Saved Credentials';
            emailInput.disabled = true;
            pwInput.value = '••••••••';
            pwInput.disabled = true;

            let helpDiv = document.getElementById('liUseDifferentCredsContainer');
            if (!helpDiv) {
                const rowDiv = emailInput.closest('.row');
                helpDiv = document.createElement('div');
                helpDiv.id = 'liUseDifferentCredsContainer';
                helpDiv.className = 'col-12 mt-2';
                helpDiv.innerHTML = `<span class="text-muted small">Using saved credentials. <a href="#" id="liUseDifferentCreds" class="text-primary text-decoration-none fw-semibold">Use a different account</a></span>`;
                rowDiv.appendChild(helpDiv);

                document.getElementById('liUseDifferentCreds').addEventListener('click', (e) => {
                    e.preventDefault();
                    emailInput.value = '';
                    emailInput.disabled = false;
                    pwInput.value = '';
                    pwInput.disabled = false;
                    emailInput.focus();
                    helpDiv.remove();
                });
            }
        } else {
            emailInput.value = '';
            emailInput.disabled = false;
            pwInput.value = '';
            pwInput.disabled = false;
            const helpDiv = document.getElementById('liUseDifferentCredsContainer');
            if (helpDiv) helpDiv.remove();
        }
    }
}

async function linkedInConnect() {
    const emailInput = document.getElementById('liEmail');
    const pwInput = document.getElementById('liPassword');
    const email = emailInput.value.trim();
    const pw = pwInput.value;
    const alert = document.getElementById('liConnectAlert');

    const useStored = (!email && !pw) || (email === 'Saved Credentials' || pw === '••••••••');

    if (!useStored && (!email || !pw)) {
        alert.className = 'alert alert-warning mt-3 mb-0';
        alert.textContent = 'Please enter your LinkedIn email and password.';
        alert.classList.remove('d-none');
        return;
    }

    alert.className = 'alert alert-info mt-3 mb-0';
    alert.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Connecting — opening LinkedIn in a headless browser. This takes 15–30 seconds…';
    alert.classList.remove('d-none');

    try {
        const bodyObj = useStored ? {} : { email, password: pw };
        const res = await fetch(`${API_BASE_URL}/linkedin/connect`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            },
            body: JSON.stringify(bodyObj)
        });
        const data = await res.json();
        if (!res.ok) {
            alert.className = 'alert alert-danger mt-3 mb-0';
            alert.textContent = data.detail || 'Connection failed.';
        } else {
            alert.className = 'alert alert-success mt-3 mb-0';
            alert.textContent = data.message;
            emailInput.value = '';
            pwInput.value = '';
            await refreshLinkedInStatus();
        }
    } catch (e) {
        alert.className = 'alert alert-danger mt-3 mb-0';
        alert.textContent = 'Network error: ' + e.message;
    }
}

async function linkedInDisconnect() {
    if (!confirm('Disconnect your LinkedIn session? You can reconnect anytime.')) return;
    await fetch(`${API_BASE_URL}/linkedin/disconnect`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
    });
    document.getElementById('liJobsContainer').innerHTML = `
        <div class="text-center text-muted py-5">
            <i class="fab fa-linkedin fa-3x mb-3 opacity-25"></i>
            <p>Connect your LinkedIn account to see personalised job recommendations.</p>
        </div>`;
    document.getElementById('liPagination').innerHTML = '';
    await refreshLinkedInStatus();
}

async function linkedInFetchJobs() {
    const btn = document.getElementById('liFetchBtn');
    const alertEl = document.getElementById('liActionAlert');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Fetching…';
    alertEl.className = 'alert alert-info';
    alertEl.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Fetching your LinkedIn "Jobs for You" feed — this takes 30–60 seconds…';
    alertEl.classList.remove('d-none');

    try {
        const res = await fetch(`${API_BASE_URL}/linkedin/fetch-jobs`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
        });
        const data = await res.json();
        if (!res.ok) {
            const msg = data.detail || 'Fetch failed.';
            const isThrottle = msg.toLowerCase().includes('please wait') || msg.toLowerCase().includes('minute');
            alertEl.className = isThrottle ? 'alert alert-warning' : 'alert alert-danger';
            alertEl.innerHTML = isThrottle
                ? `<i class="fas fa-clock me-2"></i>${msg}`
                : `<i class="fas fa-exclamation-circle me-2"></i>${msg}`;
        } else {
            alertEl.className = 'alert alert-success';
            alertEl.innerHTML = `<i class="fas fa-check-circle me-2"></i>${data.message}`;
            await loadLinkedInJobs(1);
            await refreshLinkedInStatus();
        }
    } catch (e) {
        alertEl.className = 'alert alert-danger';
        alertEl.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>Network error: ${e.message}`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
}

async function linkedInSearch() {
    const kw = document.getElementById('liSearchKw').value.trim();
    const alertEl = document.getElementById('liActionAlert');
    alertEl.className = 'alert alert-info';
    alertEl.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>Searching LinkedIn for "<strong>${kw || 'your profile keywords'}</strong>"…`;
    alertEl.classList.remove('d-none');

    try {
        const res = await fetch(`${API_BASE_URL}/linkedin/search-jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            },
            body: JSON.stringify({ keyword: kw, max_jobs: 50 })
        });
        const data = await res.json();
        if (!res.ok) {
            const msg = data.detail || 'Search failed.';
            const isThrottle = msg.toLowerCase().includes('please wait') || msg.toLowerCase().includes('minute');
            alertEl.className = isThrottle ? 'alert alert-warning' : 'alert alert-danger';
            alertEl.innerHTML = isThrottle
                ? `<i class="fas fa-clock me-2"></i>${msg}`
                : `<i class="fas fa-exclamation-circle me-2"></i>${msg}`;
        } else {
            alertEl.className = 'alert alert-success';
            alertEl.innerHTML = `<i class="fas fa-check-circle me-2"></i>${data.message}`;
            await loadLinkedInJobs(1);
        }
    } catch (e) {
        alertEl.className = 'alert alert-danger';
        alertEl.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>Network error: ${e.message}`;
    }
}

async function loadLinkedInJobs(page = 1) {
    liCurrentPage = page;
    const container = document.getElementById('liJobsContainer');
    const pagination = document.getElementById('liPagination');

    try {
        const res = await fetch(`${API_BASE_URL}/linkedin/jobs?page=${page}&size=20`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        if (!data.jobs || data.jobs.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fab fa-linkedin fa-3x mb-3 opacity-25"></i>
                    <p>No LinkedIn jobs fetched yet. Click <strong>Fetch Jobs For You</strong> to start.</p>
                </div>`;
            pagination.innerHTML = '';
            return;
        }

        let html = `<div class="row">`;
        data.jobs.forEach(job => {
            const easyApplyBadge = job.easy_apply
                ? `<span class="badge bg-success ms-1" title="Easy Apply"><i class="fas fa-bolt"></i> Easy Apply</span>`
                : '';
            const networkBadge = job.network_overlap
                ? `<span class="badge bg-info text-dark ms-1" title="${job.network_overlap}"><i class="fas fa-users"></i></span>`
                : '';
            const sourceBadge = job.fetch_source === 'jobs_for_you'
                ? `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary" style="font-size:0.65rem">For You</span>`
                : `<span class="badge bg-light text-dark border" style="font-size:0.65rem">Search</span>`;
            html += `
                <div class="col-md-6 mb-4">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h5 class="card-title fw-bold mb-0" style="font-size:1rem">
                                    <a href="${job.job_url}" target="_blank" rel="noopener noreferrer"
                                       class="text-primary text-decoration-none">${job.title}</a>
                                </h5>
                                <div class="d-flex flex-column align-items-end gap-1 ms-2">
                                    ${sourceBadge}
                                    <div class="d-flex gap-1 mt-1">${easyApplyBadge}${networkBadge}</div>
                                </div>
                            </div>
                            <h6 class="card-subtitle mb-1 text-muted small">
                                <i class="fas fa-building me-1"></i>${job.company}
                            </h6>
                            <p class="small text-muted mb-2">
                                <i class="fas fa-map-marker-alt me-1"></i>${job.location || 'Switzerland'}
                                ${job.posted_at_text ? `&nbsp;·&nbsp;<i class="fas fa-clock me-1"></i>${job.posted_at_text}` : ''}
                                ${job.network_overlap ? `&nbsp;·&nbsp;<i class="fas fa-users me-1 text-info"></i>${job.network_overlap}` : ''}
                            </p>
                        </div>
                        <div class="card-footer bg-transparent border-0 pb-3 d-flex gap-2">
                            <a href="${job.job_url}" target="_blank" rel="noopener noreferrer"
                               class="btn btn-sm btn-outline-primary flex-fill">
                                <i class="fab fa-linkedin me-1"></i>View on LinkedIn
                            </a>
                            <button class="btn btn-sm btn-primary flex-fill"
                                data-job-url="${job.job_url}"
                                data-job-title="${(job.title || '').replace(/"/g, '&quot;')}"
                                data-job-company="${(job.company || '').replace(/"/g, '&quot;')}"
                                onclick="linkedInPrepare(this)">
                                <i class="fas fa-magic me-1"></i>Prepare
                            </button>
                        </div>
                    </div>
                </div>`;
        });
        html += `</div>`;
        container.innerHTML = html;

        // Pagination
        if (data.pages > 1) {
            let pHtml = `<div class="d-flex justify-content-between align-items-center">
                <span class="text-muted small">Page ${data.page} of ${data.pages} (${data.total} jobs)</span>
                <div class="d-flex gap-2">`;
            if (page > 1) pHtml += `<button class="btn btn-sm btn-outline-secondary" onclick="loadLinkedInJobs(${page-1})">← Prev</button>`;
            if (page < data.pages) pHtml += `<button class="btn btn-sm btn-outline-secondary" onclick="loadLinkedInJobs(${page+1})">Next →</button>`;
            pHtml += `</div></div>`;
            pagination.innerHTML = pHtml;
        } else {
            pagination.innerHTML = `<p class="text-muted small text-center">${data.total} LinkedIn jobs</p>`;
        }
    } catch (e) {
        container.innerHTML = `<div class="alert alert-danger">Error loading jobs: ${e.message}</div>`;
    }
}

async function linkedInPrepare(btn) {
    const jobUrl   = btn.dataset.jobUrl;
    const jobTitle = btn.dataset.jobTitle;
    const company  = btn.dataset.jobCompany;

    try {
        showToast('Adding LinkedIn job to tracker…', 'info');

        const res = await fetch(`${API_BASE_URL}/applications`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                application_url: jobUrl,
                status: 'draft',
                job_title: jobTitle || null,
                company_name: company || null
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Failed to add job' }));
            showToast(err.detail || 'Failed to add job to tracker', 'danger');
            return;
        }

        const application = await res.json();

        // Switch to Applying Engine tab and open the prepare modal
        const appTab = document.querySelector('[data-bs-target="#tab-applications"]');
        if (appTab) appTab.click();
        loadApplications();
        openApplicationModal(application.id);
    } catch (e) {
        showToast('Error: ' + e.message, 'danger');
    }
}
