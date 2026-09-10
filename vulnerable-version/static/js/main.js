/**
 * Aura Financial Tracker - Vulnerable Version
 * Main JavaScript (WITH INTENTIONAL VULNERABILITIES)
 * Sprint 1: Water Breathing - First Form
 */

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('⚠️ Aura Vulnerable Version - Loaded');
    console.log('🐛 Debug Mode: ENABLED');
    
    // VULNERABILITY: Exposing session data in console
    console.log('Session Data:', getSessionData());
    
    // Initialize Bootstrap tooltips
    initializeTooltips();
    
    // Auto-dismiss alerts after 5 seconds
    autoDismissAlerts();
    
    // VULNERABILITY: No form validation
    // VULNERABILITY: No CSRF protection
});

/**
 * VULNERABILITY: Expose session data
 */
function getSessionData() {
    // This would normally be hidden, but we're exposing it for the vulnerable version
    const sessionDiv = document.createElement('div');
    sessionDiv.innerHTML = document.body.innerHTML;
    return {
        exposed: 'Session data should not be in JavaScript',
        hint: 'Check the page source and console for vulnerabilities'
    };
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * VULNERABILITY: No password strength checking
 */
function initializePasswordStrength() {
    // Intentionally left empty - no password strength validation
    console.log('💡 Hint: No password strength validation implemented!');
}

/**
 * Auto-dismiss alerts after 5 seconds
 */
function autoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-info):not(.alert-warning):not(.alert-danger)');
    
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * VULNERABILITY: No input sanitization
 * This function exists but doesn't actually sanitize anything
 */
function sanitizeInput(input) {
    // VULN: Returns input as-is (no sanitization)
    return input;
}

/**
 * VULNERABILITY: eval() usage (very dangerous)
 * Never use eval() in production!
 */
function executeUserInput(code) {
    try {
        // VULN: Executing arbitrary code from user input
        eval(code);
    } catch(e) {
        console.error('Error executing code:', e);
    }
}

/**
 * VULNERABILITY: Storing sensitive data in localStorage
 */
function storeCredentials(username, password) {
    // VULN: Storing credentials in localStorage (accessible via JavaScript)
    localStorage.setItem('username', username);
    localStorage.setItem('password', password);
    console.log('💡 Hint: Credentials stored in localStorage!');
}

/**
 * VULNERABILITY: No CSRF token validation
 */
function submitForm(formData) {
    // VULN: No CSRF token check
    fetch('/auth/login', {
        method: 'POST',
        body: formData
    });
}

/**
 * Show loading spinner
 */
function showLoading(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
    overlay.style.backgroundColor = 'rgba(220, 53, 69, 0.5)';
    overlay.style.zIndex = '9999';
    
    overlay.innerHTML = `
        <div class="text-center text-white">
            <div class="spinner-border mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>${message}</p>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

/**
 * Hide loading spinner
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * VULNERABILITY: DOM-based XSS
 */
function displayUserContent(content) {
    // VULN: Directly inserting user content into DOM (XSS vulnerability)
    document.getElementById('user-content').innerHTML = content;
}

/**
 * VULNERABILITY: Insecure random token generation
 */
function generateToken() {
    // VULN: Using Math.random() for security tokens (predictable)
    return 'token_' + Math.random().toString(36).substr(2, 9);
}

// VULNERABILITY: Expose API endpoints in comments
/*
 * API Endpoints:
 * - /auth/login (POST)
 * - /auth/register (POST)
 * - /auth/debug/session (GET) - Shows session data!
 * - /admin (GET) - No authentication required!
 */

// VULNERABILITY: Log all form submissions
document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function(e) {
        const formData = new FormData(form);
        console.log('📝 Form submitted with data:');
        for (let [key, value] of formData.entries()) {
            console.log(`  ${key}: ${value}`);
        }
    });
});

// VULNERABILITY: Window object exposure
window.adminAccess = function() {
    console.log('💡 Hint: Try accessing /admin endpoint!');
    window.location.href = '/admin';
};

// VULNERABILITY: Debug helper functions exposed globally
window.debug = {
    getSession: getSessionData,
    executeCode: executeUserInput,
    storeCredentials: storeCredentials,
    generateToken: generateToken
};

console.log('⚠️ Vulnerable version JavaScript initialized');
console.log('💡 Type window.debug in console to see available debug functions!');
console.log('💡 Type window.adminAccess() to access admin panel!');
