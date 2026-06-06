import axios from 'axios'
import type { Channel, Patch, Scene, Device, DanteDevice, EInkDisplay } from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Channel API
export const channelApi = {
  getAll: async (channelType?: string): Promise<Channel[]> => {
    const params = channelType ? { channel_type: channelType } : {}
    const { data } = await api.get('/channels/', { params })
    return data
  },

  get: async (id: number): Promise<Channel> => {
    const { data } = await api.get(`/channels/${id}`)
    return data
  },

  update: async (id: number, updates: Partial<Channel>): Promise<Channel> => {
    const { data } = await api.patch(`/channels/${id}`, updates)
    return data
  },

  setFader: async (id: number, level: number): Promise<void> => {
    await api.post(`/channels/${id}/fader`, { level })
  },

  toggleMute: async (id: number): Promise<{ mute: boolean }> => {
    const { data } = await api.post(`/channels/${id}/mute`)
    return data
  },

  setAuxSend: async (id: number, auxNumber: number, level: number, on: boolean): Promise<void> => {
    await api.post(`/channels/${id}/aux-send`, {
      aux_number: auxNumber,
      level,
      on,
    })
  },

  updateEQ: async (id: number, settings: any): Promise<void> => {
    await api.put(`/channels/${id}/eq`, settings)
  },

  updateComp: async (id: number, settings: any): Promise<void> => {
    await api.put(`/channels/${id}/compressor`, settings)
  },

  updateGate: async (id: number, settings: any): Promise<void> => {
    await api.put(`/channels/${id}/gate`, settings)
  },
}

// Patch API
export const patchApi = {
  getAll: async (patchType?: string): Promise<Patch[]> => {
    const params = patchType ? { patch_type: patchType } : {}
    const { data } = await api.get('/patches/', { params })
    return data
  },

  create: async (patch: Omit<Patch, 'id'>): Promise<Patch> => {
    const { data } = await api.post('/patches/', patch)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/patches/${id}`)
  },

  getMatrix: async (): Promise<any> => {
    const { data } = await api.get('/patches/matrix')
    return data
  },

  quickPatch: async (inputNumber: number, sourceType: string, sourcePort: number, sourceDevice?: string): Promise<any> => {
    const { data } = await api.post('/patches/quick-patch', {
      input_number: inputNumber,
      source_type: sourceType,
      source_port: sourcePort,
      source_device: sourceDevice,
    })
    return data
  },

  autoPatchTio: async (tioName: string, startChannel: number): Promise<any> => {
    const { data } = await api.post('/patches/auto-patch-tio', null, {
      params: { tio_name: tioName, start_channel: startChannel },
    })
    return data
  },
}

// Scene API
export const sceneApi = {
  getAll: async (): Promise<Scene[]> => {
    const { data } = await api.get('/scenes/')
    return data
  },

  get: async (id: number): Promise<Scene> => {
    const { data } = await api.get(`/scenes/${id}`)
    return data
  },

  create: async (scene: { scene_number: number; name: string; description?: string; fade_time?: number }): Promise<Scene> => {
    const { data } = await api.post('/scenes/', scene)
    return data
  },

  update: async (id: number, updates: Partial<Scene>): Promise<Scene> => {
    const { data } = await api.put(`/scenes/${id}`, updates)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/scenes/${id}`)
  },

  store: async (id: number): Promise<any> => {
    const { data } = await api.post(`/scenes/${id}/store`)
    return data
  },

  recall: async (id: number, options?: { fade_override?: number; update_eink?: boolean }): Promise<any> => {
    const { data } = await api.post(`/scenes/${id}/recall`, options || {})
    return data
  },

  preview: async (id: number): Promise<any> => {
    const { data } = await api.get(`/scenes/${id}/preview`)
    return data
  },

  updateEinkLabels: async (id: number, labels: Record<number, string>): Promise<void> => {
    await api.put(`/scenes/${id}/eink-labels`, { labels })
  },
}

// Device API
export const deviceApi = {
  getAll: async (): Promise<Device[]> => {
    const { data } = await api.get('/devices/')
    return data
  },

  getTFRackStatus: async (): Promise<any> => {
    const { data } = await api.get('/devices/tf-rack/status')
    return data
  },

  connectTFRack: async (ipAddress: string, port?: number): Promise<any> => {
    const { data } = await api.post('/devices/tf-rack/connect', null, {
      params: { ip_address: ipAddress, port: port || 49280 },
    })
    return data
  },

  disconnectTFRack: async (): Promise<void> => {
    await api.post('/devices/tf-rack/disconnect')
  },

  getDanteDevices: async (): Promise<DanteDevice[]> => {
    const { data } = await api.get('/devices/dante')
    return data
  },

  getTioDevices: async (): Promise<DanteDevice[]> => {
    const { data } = await api.get('/devices/dante/tio')
    return data
  },

  refreshDante: async (): Promise<void> => {
    await api.post('/devices/dante/refresh')
  },
}

// E-ink API
export const einkApi = {
  getStatus: async (): Promise<EInkDisplay[]> => {
    const { data } = await api.get('/eink/status')
    return data
  },

  updateDisplay: async (index: number, text: string, subtext?: string, color?: string): Promise<void> => {
    await api.post(`/eink/${index}/update`, {
      text,
      subtext: subtext || '',
      color: color || 'black',
    })
  },

  updateChannelLabel: async (channel: number, text: string, subtext?: string): Promise<void> => {
    await api.post(`/eink/channel/${channel}`, {
      text,
      subtext: subtext || '',
    })
  },

  bulkUpdate: async (labels: Record<number, string>): Promise<any> => {
    const { data } = await api.post('/eink/bulk-update', { labels })
    return data
  },

  clearAll: async (): Promise<void> => {
    await api.post('/eink/clear-all')
  },

  setMapping: async (displayIndex: number, channelNumber: number): Promise<void> => {
    await api.post('/eink/mapping', {
      display_index: displayIndex,
      channel_number: channelNumber,
      channel_type: 'input',
    })
  },

  refresh: async (): Promise<any> => {
    const { data } = await api.post('/eink/refresh')
    return data
  },

  testPattern: async (): Promise<void> => {
    await api.post('/eink/test-pattern')
  },
}

// Health check
export const healthCheck = async (): Promise<any> => {
  const { data } = await api.get('/health')
  return data
}

export default api
