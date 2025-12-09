import { createRouter, createWebHistory } from 'vue-router'

// Lazy-loaded route components
const Login = () => import('../views/auth/Login.vue')
const Dashboard = () => import('../views/Dashboard.vue')
const AssetList = () => import('../views/assets/AssetList.vue')
const AssetCreate = () => import('../views/assets/AssetCreate.vue')
const AssetDetail = () => import('../views/assets/AssetDetail.vue')
const AssetEdit = () => import('../views/assets/AssetEdit.vue')
const ApiKeys = () => import('../views/ApiKeys.vue')
const ProfileSettings = () => import('../views/settings/ProfileSettings.vue')
const NotFound = () => import('../views/NotFound.vue')

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/auth/Login.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/register',
        name: 'Register',
        component: () => import('../views/auth/Register.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/forgot-password',
        name: 'ForgotPassword',
        component: () => import('../views/auth/ForgotPassword.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/reset-password',
        name: 'ResetPassword',
        component: () => import('../views/auth/ResetPassword.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/help',
        name: 'Help',
        component: () => import('../views/Help.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/',
        component: () => import('../layouts/AppShell.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: '/dashboard'
            },
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: Dashboard
            },
            {
                path: 'assets',
                children: [
                    {
                        path: '',
                        name: 'AssetList',
                        component: AssetList
                    },
                    {
                        path: 'create',
                        name: 'AssetCreate',
                        component: AssetCreate
                    },
                    {
                        path: ':slug',
                        name: 'AssetDetail',
                        component: AssetDetail
                    },
                    {
                        path: ':slug/edit',
                        name: 'AssetEdit',
                        component: AssetEdit
                    }
                ]
            },
            {
                path: 'api-keys',
                name: 'ApiKeys',
                component: ApiKeys
            },
            {
                path: 'settings',
                children: [
                    {
                        path: 'profile',
                        name: 'ProfileSettings',
                        component: ProfileSettings
                    },
                    {
                        path: 'team',
                        name: 'TeamSettings',
                        component: () => import('../views/settings/TeamSettings.vue')
                    },
                    {
                        path: 'organization',
                        name: 'OrganizationSettings',
                        component: () => import('../views/settings/OrganizationSettings.vue')
                    },
                    {
                        path: 'activity',
                        name: 'ActivityLog',
                        component: () => import('../views/settings/ActivityLog.vue')
                    }
                ]
            }
        ]
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: NotFound
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
    const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true'

    console.log('Router guard:', {
        to: to.path,
        from: from.path,
        requiresAuth,
        isAuthenticated,
        isAuthenticatedValue: localStorage.getItem('isAuthenticated')
    })

    if (requiresAuth && !isAuthenticated) {
        console.log('→ Redirecting to login (not authenticated)')
        // Store intended route for post-login redirect
        localStorage.setItem('intendedRoute', to.fullPath)
        next({ name: 'Login' })
    } else if (to.name === 'Login' && isAuthenticated) {
        console.log('→ Redirecting to dashboard (already authenticated)')
        next({ name: 'Dashboard' })
    } else {
        console.log('→ Allowing navigation')
        next()
    }
})

export default router
