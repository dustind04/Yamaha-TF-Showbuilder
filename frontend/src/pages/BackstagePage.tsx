import { useQuery } from '@tanstack/react-query'
import { Monitor, RefreshCw, Battery, Radio, Volume2 } from 'lucide-react'
import clsx from 'clsx'
import api from '../services/api'

interface BackstageArtist {
  artist_id: number
  name: string
  image_url?: string
  primary_instrument?: string
  channel_number?: number
  mic_type?: string
  mic_number?: string
  iem_pack?: string
  iem_frequency?: string
  monitor_mix?: string
  notes?: string
}

interface BackstageData {
  show_name: string
  band_name: string
  venue?: string
  set_time?: string
  artists: BackstageArtist[]
}

interface WirelessDevice {
  artist_id: number
  artist_name: string
  image_url?: string
  mic_type?: string
  mic_number?: string
  mic_model?: string
  frequency?: string
  channel?: number
  iem_pack?: string
  iem_frequency?: string
  status: string
  battery_percent?: number
  rf_level?: number
  audio_level?: number
}

const backstageApi = {
  getCurrent: async (): Promise<BackstageData> => {
    const { data } = await api.get('/backstage/current')
    return data
  },
  getWirelessOverview: async (): Promise<{ devices: WirelessDevice[] }> => {
    const { data } = await api.get('/backstage/wireless-overview')
    return data
  }
}

function BatteryIndicator({ percent }: { percent?: number }) {
  if (percent === undefined) return null

  const color = percent > 50 ? 'text-green-500' :
                percent > 20 ? 'text-yellow-500' : 'text-red-500'

  return (
    <div className={clsx('flex items-center gap-1', color)}>
      <Battery size={16} />
      <span className="text-xs">{percent}%</span>
    </div>
  )
}

function RFIndicator({ level }: { level?: number }) {
  if (level === undefined) return null

  const bars = Math.ceil((level / 100) * 5)
  const color = level > 60 ? 'bg-green-500' :
                level > 30 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <div
          key={i}
          className={clsx(
            'w-1 rounded-sm',
            i <= bars ? color : 'bg-gray-600'
          )}
          style={{ height: `${i * 3 + 4}px` }}
        />
      ))}
    </div>
  )
}

export default function BackstagePage() {
  const { data: backstage, isLoading, refetch } = useQuery({
    queryKey: ['backstage-current'],
    queryFn: backstageApi.getCurrent,
    refetchInterval: 5000,
  })

  const { data: wireless } = useQuery({
    queryKey: ['wireless-overview'],
    queryFn: backstageApi.getWirelessOverview,
    refetchInterval: 2000,
  })

  if (isLoading) {
    return <div className="text-gray-400">Loading backstage display...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Monitor size={24} />
          Backstage Monitor
        </h1>
        <button
          onClick={() => refetch()}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Show/Band Header */}
      {backstage && backstage.show_name && (
        <div className="card bg-gradient-to-r from-blue-900 to-purple-900">
          <div className="text-center">
            <h2 className="text-3xl font-bold">{backstage.band_name}</h2>
            <div className="text-lg text-gray-300">{backstage.show_name}</div>
            {backstage.venue && (
              <div className="text-sm text-gray-400">{backstage.venue}</div>
            )}
            {backstage.set_time && (
              <div className="text-xl mt-2 font-mono">{backstage.set_time}</div>
            )}
          </div>
        </div>
      )}

      {/* Artist Cards - Micboard Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {backstage?.artists?.map((artist) => {
          // Find wireless info for this artist
          const wirelessInfo = wireless?.devices?.find(d => d.artist_id === artist.artist_id)

          return (
            <div
              key={artist.artist_id}
              className="card bg-gray-800 border border-gray-700 hover:border-blue-500 transition-colors"
            >
              {/* Artist Photo */}
              <div className="flex justify-center mb-3">
                <div className="w-20 h-20 bg-gray-700 rounded-full overflow-hidden">
                  {artist.image_url ? (
                    <img
                      src={artist.image_url}
                      alt={artist.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500 text-2xl font-bold">
                      {artist.name.charAt(0)}
                    </div>
                  )}
                </div>
              </div>

              {/* Artist Name */}
              <h3 className="text-lg font-bold text-center">{artist.name}</h3>
              <div className="text-sm text-gray-400 text-center mb-3">
                {artist.primary_instrument}
              </div>

              {/* Equipment Info */}
              <div className="space-y-2 text-sm">
                {/* Microphone */}
                {artist.mic_type && (
                  <div className="flex items-center justify-between bg-gray-700 rounded p-2">
                    <div className="flex items-center gap-2">
                      <Volume2 size={14} className="text-blue-400" />
                      <span>{artist.mic_number || 'MIC'}</span>
                    </div>
                    <span className="text-gray-400 text-xs">{artist.mic_type}</span>
                  </div>
                )}

                {/* IEM */}
                {artist.iem_pack && (
                  <div className="flex items-center justify-between bg-gray-700 rounded p-2">
                    <div className="flex items-center gap-2">
                      <Radio size={14} className="text-green-400" />
                      <span>{artist.iem_pack}</span>
                    </div>
                    {artist.iem_frequency && (
                      <span className="text-gray-400 text-xs">{artist.iem_frequency}</span>
                    )}
                  </div>
                )}

                {/* Monitor Mix */}
                {artist.monitor_mix && (
                  <div className="text-center text-xs text-gray-400">
                    Monitor: {artist.monitor_mix}
                  </div>
                )}

                {/* Channel Number */}
                {artist.channel_number && (
                  <div className="text-center">
                    <span className="bg-blue-600 px-3 py-1 rounded text-sm font-mono">
                      CH {artist.channel_number}
                    </span>
                  </div>
                )}
              </div>

              {/* Status Indicators */}
              {wirelessInfo && (
                <div className="flex justify-center gap-3 mt-3 pt-3 border-t border-gray-700">
                  <BatteryIndicator percent={wirelessInfo.battery_percent} />
                  <RFIndicator level={wirelessInfo.rf_level} />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Wireless Overview - Micboard Style */}
      {wireless?.devices && wireless.devices.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Radio size={20} />
            Wireless Status
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="py-2 px-4">Artist</th>
                  <th className="py-2 px-4">Device</th>
                  <th className="py-2 px-4">Frequency</th>
                  <th className="py-2 px-4">Battery</th>
                  <th className="py-2 px-4">RF</th>
                  <th className="py-2 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {wireless.devices.map((device, i) => (
                  <tr key={i} className="border-b border-gray-800">
                    <td className="py-2 px-4 font-medium">{device.artist_name}</td>
                    <td className="py-2 px-4">
                      {device.mic_number || device.iem_pack || '-'}
                      {device.mic_model && (
                        <span className="text-gray-400 text-xs ml-1">({device.mic_model})</span>
                      )}
                    </td>
                    <td className="py-2 px-4 font-mono text-xs">
                      {device.frequency || device.iem_frequency || '-'}
                    </td>
                    <td className="py-2 px-4">
                      <BatteryIndicator percent={device.battery_percent} />
                    </td>
                    <td className="py-2 px-4">
                      <RFIndicator level={device.rf_level} />
                    </td>
                    <td className="py-2 px-4">
                      <span className={clsx(
                        'px-2 py-0.5 rounded text-xs',
                        device.status === 'online' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      )}>
                        {device.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Full Screen Display Mode Button */}
      <div className="text-center">
        <button
          onClick={() => {
            document.documentElement.requestFullscreen?.()
          }}
          className="btn btn-secondary"
        >
          Enter Full Screen Display Mode
        </button>
      </div>
    </div>
  )
}
