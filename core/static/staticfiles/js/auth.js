// Authentication related JavaScript functions

// Function to handle login form submission
function handleLogin(event) {
    event.preventDefault();
    // Add login logic here if needed
    document.getElementById('login-form').submit();
}

// Function to handle logout confirmation
function confirmLogout() {
    return confirm('Are you sure you want to log out?');
}

// Function to handle registration form validation
function validateRegistrationForm() {
    // Add registration form validation logic here if needed
    return true;
}

// Initialize auth-related event listeners when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Set up any needed event listeners for auth forms
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            if (!confirmLogout()) {
                e.preventDefault();
            }
        });
    }
    
    const registrationForm = document.getElementById('registration-form');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function(e) {
            if (!validateRegistrationForm()) {
                e.preventDefault();
            }
        });
    }
});
