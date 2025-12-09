import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api/client';

export const useAuthStore = defineStore('auth', () => {
    // State - must be defined first
    const user = ref(JSON.parse(localStorage.getItem('user')) || null);

    // Router
    const router = useRouter();

    // Computed properties - use user ref defined above
    const isAuthenticated = computed(() => !!user.value);
    const isAdmin = computed(() => user.value?.role === 'admin');

    async function login(email, password) {
        try {
            const response = await api.post('/auth/login/', { email, password });
            const { access, refresh, user: userData } = response.data;

            // Save tokens and user data
            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            localStorage.setItem('user', JSON.stringify(userData));
            localStorage.setItem('isAuthenticated', 'true'); // Fix: Set auth flag for router guard

            user.value = userData;
            return true;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    async function register(userData) {
        try {
            const response = await api.post('/auth/register/', userData);
            const { access, refresh, user: newUserData } = response.data;

            // Auto-login after registration
            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            localStorage.setItem('user', JSON.stringify(newUserData));
            localStorage.setItem('isAuthenticated', 'true'); // Fix: Set auth flag for router guard

            user.value = newUserData;
            return true;
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    }

    function logout() {
        user.value = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        router.push('/login');
    }

    return {
        user,
        isAuthenticated,
        isAdmin,
        login,
        register,
        logout
    };
});
