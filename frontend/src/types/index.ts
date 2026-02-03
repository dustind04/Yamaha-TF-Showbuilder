// Channel types
export type ChannelType = 'input' | 'aux' | 'stereo' | 'matrix' | 'dca' | 'fx_send' | 'fx_return'

export interface Channel {
  id: number
  channel_number: number
  channel_type: ChannelType
  name: string
  color: string
  icon: string
  fader_level: number
  pan: number
  mute: boolean
  on: boolean
  phantom_power: boolean
  gain: number
  phase_invert: boolean
  eq_enabled: boolean
  comp_enabled: boolean
  gate_enabled: boolean
  eq_settings?: EQSettings
  comp_settings?: CompSettings
  gate_settings?: GateSettings
  aux_sends?: Record<string, { level: number; on: boolean }>
}

export interface EQBand {
  frequency: number
  gain: number
  q: number
  type: string
}

export interface EQSettings {
  hpf_enabled: boolean
  hpf_frequency: number
  low: EQBand
  low_mid: EQBand
  high_mid: EQBand
  high: EQBand
}

export interface CompSettings {
  threshold: number
  ratio: number
  attack: number
  release: number
  gain: number
  knee: string
}

export interface GateSettings {
  threshold: number
  range: number
  attack: number
  hold: number
  release: number
}

// Patch types
export type PatchType =
  | 'analog_to_channel'
  | 'dante_to_channel'
  | 'channel_to_dante'
  | 'channel_to_aux'
  | 'aux_to_dante'
  | 'direct_out'

export interface Patch {
  id: number
  patch_type: PatchType
  source_device: string
  source_port: number
  source_channel_name?: string
  dest_device: string
  dest_port: number
  dest_channel_name?: string
  channel_id?: number
  dante_flow_id?: string
}

// Scene types
export interface Scene {
  id: number
  scene_number: number
  name: string
  description?: string
  fade_time: number
  eink_labels: Record<string, string>
  mixer_state?: Record<string, any>
}

// Device types
export type DeviceType = 'tf_rack' | 'tio_1608_d' | 'dante_generic'

export interface Device {
  id: number
  device_type: DeviceType
  name: string
  ip_address?: string
  dante_name?: string
  dante_model?: string
  is_online: boolean
  input_count: number
  output_count: number
  sample_rate: number
}

export interface DanteDevice {
  name: string
  ip_address: string
  model: string
  manufacturer: string
  is_online: boolean
  input_channels: number
  output_channels: number
  sample_rate: number
}

// E-ink types
export interface EInkDisplay {
  index: number
  connected: boolean
  current_text: string
  channel_number?: number
  last_update?: string
}

// WebSocket message types
export interface WSMessage {
  type: string
  [key: string]: any
}

// API response types
export interface APIResponse<T> {
  status: string
  data?: T
  message?: string
}
