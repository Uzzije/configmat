import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import AppShell from '@/layouts/AppShell.vue'

// Mock child components to avoid deep rendering issues
vi.mock('@/components/TopNav.vue', () => ({ default: { template: '<div class="topnav-stub"></div>' } }))
vi.mock('@/components/Sidebar.vue', () => ({ default: { template: '<div class="sidebar-stub"></div>' } }))
vi.mock('@/components/ChatBox.vue', () => ({ default: { template: '<div class="chatbox-stub"></div>' } }))

describe('AppShell.vue', () => {
    it('renders layout structure', () => {
        const wrapper = mount(AppShell, {
            global: {
                stubs: ['RouterView']
            }
        })

        expect(wrapper.find('.topnav-stub').exists()).toBe(true)
        expect(wrapper.find('.sidebar-stub').exists()).toBe(true)
        expect(wrapper.find('.chatbox-stub').exists()).toBe(true)
        expect(wrapper.findComponent({ name: 'RouterView' }).exists()).toBe(true)
        expect(wrapper.find('main').classes()).toContain('ml-64')
    })
})
