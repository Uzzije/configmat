import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import Sidebar from '@/components/Sidebar.vue'

// Mock useRoute
vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({
        path: '/dashboard'
    }))
}))

describe('Sidebar.vue', () => {
    it('renders navigation items', () => {
        const wrapper = mount(Sidebar, {
            global: {
                stubs: {
                    'router-link': RouterLinkStub
                }
            }
        })

        expect(wrapper.text()).toContain('Dashboard')
        expect(wrapper.text()).toContain('Assets')
        expect(wrapper.text()).toContain('Settings')
    })

    it('highlights active route', async () => {
        const wrapper = mount(Sidebar, {
            global: {
                stubs: {
                    'router-link': RouterLinkStub
                }
            }
        })

        // Find stub by prop
        const links = wrapper.findAllComponents(RouterLinkStub)
        const dashboardLink = links.find(c => c.props().to === '/dashboard')

        expect(dashboardLink).toBeDefined()
        expect(dashboardLink.classes()).toContain('bg-primary')

        const assetsLink = links.find(c => c.props().to === '/assets')
        expect(assetsLink.classes()).not.toContain('bg-primary')
    })
})
