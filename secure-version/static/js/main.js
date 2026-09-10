/**
 * Aura Financial Tracker - Secure Version
 * Main JavaScript
 * Sprint 1: Water Breathing - First Form
 */

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔒 Aura Secure Version - Loaded');
    
    // Initialize Bootstrap tooltips
    initializeTooltips();
    
    // Password strength indicator
    initializePasswordStrength();
    
    // Auto-dismiss alerts after 5 seconds
    autoDismissAlerts();
    
    // Form validation
    initializeFormValidation();
});

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
 * Password strength indicator
 */
function initializePasswordStrength() {
    const passwordInput = document.getElementById('password');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const strength = calculatePasswordStrength(password);
            updatePasswordStrengthUI(strength);
        });
    }
}

/**
 * Calculate password strength
 * @param {string} password - The password to check
 * @returns {number} - Strength score (0-3)
 */
function calculatePasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) strength++;
    
    return Math.min(strength, 3);
}

/**
 * Update password strength UI
 * @param {number} strength - Strength score
 */
function updatePasswordStrengthUI(strength) {
    const indicator = document.getElementById('password-strength-indicator');
    
    if (!indicator) return;
    
    const classes = ['weak', 'medium', 'strong'];
    const texts = ['Weak', 'Medium', 'Strong'];
    
    indicator.className = 'password-strength ' + classes[strength - 1];
    indicator.textContent = texts[strength - 1] || '';
}

/**
 * Auto-dismiss alerts after 5 seconds
 */
function autoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-info):not(.alert-warning)');
    
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Sanitize user input (XSS prevention)
 * @param {string} input - User input
 * @returns {string} - Sanitized input
 */
function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

/**
 * Show loading spinner
 * @param {string} message - Loading message
 */
function showLoading(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    overlay.style.zIndex = '9999';

    const inner = document.createElement('div');
    inner.className = 'text-center text-white';

    const spinner = document.createElement('div');
    spinner.className = 'spinner-border mb-3';
    spinner.setAttribute('role', 'status');
    const srOnly = document.createElement('span');
    srOnly.className = 'visually-hidden';
    srOnly.textContent = 'Loading...';
    spinner.appendChild(srOnly);

    const p = document.createElement('p');
    p.textContent = message; // was raw innerHTML interpolation — this function isn't
                              // currently called anywhere, but caller-supplied text
                              // shouldn't be able to inject markup if it ever is.

    inner.appendChild(spinner);
    inner.appendChild(p);
    overlay.appendChild(inner);

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
 * Confirm password match validation
 */
function validatePasswordMatch() {
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    
    if (password && confirmPassword) {
        confirmPassword.addEventListener('input', function() {
            if (this.value !== password.value) {
                this.setCustomValidity('Passwords do not match');
            } else {
                this.setCustomValidity('');
            }
        });
    }
}

// Initialize password match validation
validatePasswordMatch();

// Prevent multiple form submissions
document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function() {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        }
    });
});

console.log('✅ Secure version JavaScript initialized');
