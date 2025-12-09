import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import Help from '@/views/Help.vue'

describe('Help.vue', () => {
    it('renders help content', () => {
        const wrapper = mount(Help)
        expect(wrapper.text()).toContain('Help & Documentation')
        expect(wrapper.text()).toContain('Getting Started')
    })
})
