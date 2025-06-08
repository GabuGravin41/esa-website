// Authentication API object
const auth = {
    // Check authentication status
    async checkStatus() {
        try {
            const response = await fetch('/accounts/api/auth/status/');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error checking auth status:', error);
            return { status: 'error', message: 'Failed to check authentication status' };
        }
    },

    // Login
    async login(username, password, rememberMe = false) {
        try {
            // Create form data instead of JSON
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            formData.append('remember_me', rememberMe);
            
            const response = await fetch('/accounts/account_login/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                    // Note: Removed Content-Type to let browser set it with boundary for FormData
                },
                body: formData
            });
            
            // First check if the response is OK
            if (!response.ok) {
                console.error('Server error:', response.status, response.statusText);
                return { 
                    status: 'error', 
                    message: `Server error: ${response.status} ${response.statusText}` 
                };
            }
            
            // Then try to parse JSON
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Login error:', error);
            return { status: 'error', message: 'Failed to login. Check your network connection.' };
        }
    },

    // Logout
    async logout() {
        try {
            const formData = new FormData();
            
            const response = await fetch('/accounts/account_logout/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            
            if (!response.ok) {
                console.error('Server error during logout:', response.status, response.statusText);
                return { 
                    status: 'error', 
                    message: `Server error during logout: ${response.status}` 
                };
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Logout error:', error);
            return { status: 'error', message: 'Failed to logout' };
        }
    },

    // Register
    async register(formData) {
        try {
            const response = await fetch('/accounts/register/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Registration error:', error);
            return { status: 'error', message: 'Failed to register' };
        }
    },

    // Update profile
    async updateProfile(formData) {
        try {
            const response = await fetch('/accounts/profile/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Profile update error:', error);
            return { status: 'error', message: 'Failed to update profile' };
        }
    },

    // Get CSRF token from cookie
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },

    // Debug CSRF token issues
    debugCsrf() {
        const token = this.getCsrfToken();
        if (!token) {
            console.error('No CSRF token found in cookies!');
            return false;
        }
        console.log('CSRF token found:', token.substring(0, 5) + '...');
        return true;
    }
};

// Form handling object
const forms = {
    // Handle login form submission
    async handleLogin(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        // Add debug info to help troubleshoot
        console.log('Submitting login form to:', form.action);
        console.log('Form data username:', formData.get('username'));
        console.log('Remember me set:', formData.get('remember_me') ? true : false);
        
        const result = await auth.login(
            formData.get('username'),
            formData.get('password'),
            formData.get('remember_me') === 'on'
        );

        console.log('Login result:', result);
        
        if (result.status === 'success') {
            window.location.href = result.redirect_url || '/';
        } else {
            ui.showError(result.message || 'Login failed. Please try again.');
        }
    },

    // Handle registration form submission
    async handleRegister(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        const result = await auth.register(formData);

        if (result.status === 'success') {
            window.location.href = result.redirect_url || '/';
        } else {
            ui.showErrors(result.errors);
        }
    },

    // Handle profile update form submission
    async handleProfileUpdate(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        const result = await auth.updateProfile(formData);

        if (result.status === 'success') {
            ui.showSuccess('Profile updated successfully');
        } else {
            ui.showErrors(result.errors);
        }
    }
};

// UI helper object
const ui = {
    // Show error message
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'rounded-md bg-red-50 p-4 mb-4';
        errorDiv.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <ion-icon name="alert-circle" class="h-5 w-5 text-red-400"></ion-icon>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">Error</h3>
                    <div class="mt-2 text-sm text-red-700">
                        <p>${message}</p>
                    </div>
                </div>
            </div>
        `;
        this.insertMessage(errorDiv);
    },

    // Show success message
    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'rounded-md bg-green-50 p-4 mb-4';
        successDiv.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <ion-icon name="checkmark-circle" class="h-5 w-5 text-green-400"></ion-icon>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-green-800">Success</h3>
                    <div class="mt-2 text-sm text-green-700">
                        <p>${message}</p>
                    </div>
                </div>
            </div>
        `;
        this.insertMessage(successDiv);
    },

    // Show multiple error messages
    showErrors(errors) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'rounded-md bg-red-50 p-4 mb-4';
        errorDiv.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <ion-icon name="alert-circle" class="h-5 w-5 text-red-400"></ion-icon>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">
                        Please correct the following errors:
                    </h3>
                    <div class="mt-2 text-sm text-red-700">
                        <ul class="list-disc pl-5 space-y-1">
                            ${Object.entries(errors).map(([field, messages]) => 
                                messages.map(message => `<li>${field}: ${message}</li>`).join('')
                            ).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
        this.insertMessage(errorDiv);
    },

    // Insert message into the page
    insertMessage(messageDiv) {
        const container = document.querySelector('.container.mx-auto.px-4.py-4');
        if (container) {
            container.insertBefore(messageDiv, container.firstChild);
        } else {
            document.body.insertBefore(messageDiv, document.body.firstChild);
        }
    }
};

// Initialize form handlers when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Login form - be more specific with the selector
    const loginForm = document.querySelector('form[action*="account_login"]');
    if (loginForm) {
        console.log('Login form detected and handler attached');
        loginForm.addEventListener('submit', forms.handleLogin);
    } else {
        console.log('Login form not found on page');
    }

    // Registration form
    const registerForm = document.querySelector('form[action*="register"]');
    if (registerForm) {
        console.log('Register form detected and handler attached');
        registerForm.addEventListener('submit', forms.handleRegister);
    }

    // Profile update form
    const profileForm = document.querySelector('form[action*="profile"]');
    if (profileForm) {
        console.log('Profile form detected and handler attached');
        profileForm.addEventListener('submit', forms.handleProfileUpdate);
    }
});