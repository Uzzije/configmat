import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import ChatBox from '@/components/ChatBox.vue'
import api from '@/api/client'

// Mock API Client
vi.mock('@/api/client', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn()
    }
}))

describe('ChatBox.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('toggles open and loads messages', async () => {
        api.get.mockResolvedValue({ data: [] })
        api.post.mockResolvedValue({}) // mark_read response

        const wrapper = mount(ChatBox, { attachTo: document.body })

        // Initial: closed
        expect(wrapper.find('.w-80').exists()).toBe(false)

        // Click toggle
        await wrapper.find('button[title="Contact Support"]').trigger('click')

        expect(wrapper.find('.w-80').exists()).toBe(true)
        expect(api.get).toHaveBeenCalledWith('/chat/messages/')
        // mark_read called logic? 
        // toggleChat code: api.post(...)

        wrapper.unmount()
    })

    it('sends a message', async () => {
        api.get.mockResolvedValue({ data: [] })
        api.post.mockResolvedValue({ data: {} }) // default

        const wrapper = mount(ChatBox, { attachTo: document.body })
        // Open manually (mock logic dependent)
        wrapper.vm.isOpen = true
        await wrapper.vm.$nextTick()

        // Setup send response
        const newMsg = { id: 1, message: 'Hello', created_at: new Date().toISOString(), is_from_admin: false }
        api.post.mockResolvedValue({ data: newMsg })
        // Note: mark_read is NOT called because we manually set isOpen without toggleChat

        const input = wrapper.find('input')
        await input.setValue('Hello')
        await wrapper.find('form').trigger('submit.prevent')

        expect(api.post).toHaveBeenCalledWith('/chat/messages/', { message: 'Hello' })
        expect(wrapper.text()).toContain('Hello')

        wrapper.unmount()
    })

    it('polls for unread count when closed', async () => {
        api.get.mockResolvedValue({ data: { count: 5 } })
        const wrapper = mount(ChatBox)

        // Trigger timer
        await vi.advanceTimersByTimeAsync(5000)

        expect(api.get).toHaveBeenCalledWith('/chat/messages/unread_count/')
        expect(wrapper.find('span.bg-destructive').text()).toBe('5')
    })
})
