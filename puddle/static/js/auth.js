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
            const response = await fetch('/accounts/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    username,
                    password,
                    remember_me: rememberMe
                })
            });
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Login error:', error);
            return { status: 'error', message: 'Failed to login' };
        }
    },

    // Logout
    async logout() {
        try {
            const response = await fetch('/accounts/logout/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
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
    }
};

// Form handling object
const forms = {
    // Handle login form submission
    async handleLogin(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        const result = await auth.login(
            formData.get('username'),
            formData.get('password'),
            formData.get('remember_me') === 'on'
        );

        if (result.status === 'success') {
            window.location.href = result.redirect_url || '/';
        } else {
            ui.showError(result.message);
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
    // Login form
    const loginForm = document.querySelector('form[action*="login"]');
    if (loginForm) {
        loginForm.addEventListener('submit', forms.handleLogin);
    }

    // Registration form
    const registerForm = document.querySelector('form[action*="register"]');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': auth.getCsrfToken()
                    },
                    body: formData
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    window.location.href = data.redirect_url || '/';
                } else {
                    ui.showErrors(data.errors);
                }
            } catch (error) {
                console.error('Registration error:', error);
                ui.showError('An error occurred during registration');
            }
        });
    }

    // Profile update form
    const profileForm = document.querySelector('form[action*="profile"]');
    if (profileForm) {
        profileForm.addEventListener('submit', forms.handleProfileUpdate);
    }
}); 