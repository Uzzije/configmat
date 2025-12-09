import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import AssetDetail from '@/views/assets/AssetDetail.vue'
import { assetService, configObjectService } from '@/api/services'
import CodeEditor from '@/components/CodeEditor.vue'

// Mock CodeEditor
vi.mock('@/components/CodeEditor.vue', () => ({
    default: { template: '<div class="code-editor-stub"></div>' }
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    }),
    useRoute: () => ({
        params: { slug: 'test-asset' }
    })
}))

vi.mock('@/api/services', () => ({
    assetService: {
        getAsset: vi.fn(),
        deleteAsset: vi.fn(),
        promoteAsset: vi.fn()
    },
    configObjectService: {
        getObjects: vi.fn(),
        createObject: vi.fn(),
        updateObjectValues: vi.fn(),
        deleteObject: vi.fn(),
        updateObject: vi.fn()
    }
}))

describe('AssetDetail.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()

        assetService.getAsset.mockResolvedValue({
            id: 1,
            name: 'Test Asset',
            slug: 'test-asset',
            environment: 'local',
            context: 'global'
        })

        configObjectService.getObjects.mockResolvedValue({
            results: [{
                id: 10,
                name: 'DB Config',
                object_type: 'kv',
                values: [] // No values
            }],
            count: 1
        })

        vi.spyOn(window, 'confirm').mockReturnValue(true)
    })

    it('renders asset details and config objects', async () => {
        const wrapper = mount(AssetDetail, { global: { plugins: [pinia] } })

        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(wrapper.text()).toContain('Test Asset')
        expect(wrapper.text()).toContain('DB Config')
    })

    it('opens add object modal', async () => {
        const wrapper = mount(AssetDetail, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        const addBtn = wrapper.findAll('button').find(b => b.text().includes('Add Object'))
        await addBtn.trigger('click')

        expect(wrapper.text()).toContain('Add Config Object')
    })

    it('deletes asset', async () => {
        const wrapper = mount(AssetDetail, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
        await deleteBtn.trigger('click')

        expect(assetService.deleteAsset).toHaveBeenCalledWith('test-asset')
    })
})
