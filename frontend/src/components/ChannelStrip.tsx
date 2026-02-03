import { useState, useCallback } from 'react'
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import clsx from 'clsx'
import type { Channel } from '../types'
import { useUpdateChannel, useToggleMute, useSetFader } from '../hooks/useChannels'
import { useWebSocket } from '../services/websocket'

interface ChannelStripProps {
  channel: Channel
  showMeter?: boolean
  compact?: boolean
}

export default function ChannelStrip({ channel, showMeter = true, compact = false }: ChannelStripProps) {
  const [localFader, setLocalFader] = useState(channel.fader_level)
  const { meters } = useWebSocket()
  const updateChannel = useUpdateChannel()
  const toggleMute = useToggleMute()
  const setFader = useSetFader()

  const meterValue = meters[channel.channel_number - 1] || 0

  const handleFaderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value)
    setLocalFader(value)
  }, [])

  const handleFaderCommit = useCallback(() => {
    setFader.mutate({ id: channel.id, level: localFader })
  }, [channel.id, localFader, setFader])

  const handleMuteClick = useCallback(() => {
    toggleMute.mutate(channel.id)
  }, [channel.id, toggleMute])

  const handleOnClick = useCallback(() => {
    updateChannel.mutate({ id: channel.id, updates: { on: !channel.on } })
  }, [channel.id, channel.on, updateChannel])

  const meterDbToPercent = (value: number): number => {
    // Assuming meter value is 0-1
    return value * 100
  }

  const getMeterColor = (percent: number): string => {
    if (percent > 90) return 'bg-red-500'
    if (percent > 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div className={clsx(
      'channel-strip',
      `channel-color-${channel.color || 'off'}`,
      compact ? 'p-1' : 'p-2'
    )}>
      {/* Channel Name */}
      <div className="text-center mb-2">
        <div className="text-xs text-gray-400">CH {channel.channel_number}</div>
        <div className="text-sm font-medium truncate w-16" title={channel.name}>
          {channel.name || '---'}
        </div>
      </div>

      {/* Meter and Fader Container */}
      <div className="flex items-center space-x-1 mb-2">
        {/* Meter */}
        {showMeter && (
          <div className="meter-bar">
            <div
              className={clsx('meter-fill', getMeterColor(meterDbToPercent(meterValue)))}
              style={{ height: `${meterDbToPercent(meterValue)}%` }}
            />
          </div>
        )}

        {/* Fader */}
        <div className="relative h-48 w-8 bg-mixer-fader rounded flex items-center justify-center">
          <input
            type="range"
            min="-90"
            max="10"
            step="0.5"
            value={localFader}
            onChange={handleFaderChange}
            onMouseUp={handleFaderCommit}
            onTouchEnd={handleFaderCommit}
            className="h-40 w-2 appearance-none bg-gray-600 rounded cursor-pointer"
            style={{
              writingMode: 'vertical-lr',
              direction: 'rtl',
            }}
          />
          {/* Unity (0dB) marker */}
          <div className="absolute right-0 top-1/2 w-1 h-0.5 bg-white" style={{ top: '10%' }} />
        </div>
      </div>

      {/* Fader Value */}
      <div className="text-xs text-center mb-2">
        {localFader <= -90 ? '-∞' : `${localFader.toFixed(1)}`} dB
      </div>

      {/* Controls */}
      <div className="flex flex-col space-y-1">
        {/* On Button */}
        <button
          onClick={handleOnClick}
          className={clsx(
            'btn-on w-full py-1 text-xs rounded',
            channel.on && 'active'
          )}
        >
          {channel.on ? <Volume2 size={14} className="mx-auto" /> : <VolumeX size={14} className="mx-auto" />}
        </button>

        {/* Mute Button */}
        <button
          onClick={handleMuteClick}
          className={clsx(
            'btn-mute w-full py-1 text-xs rounded',
            channel.mute && 'active'
          )}
        >
          {channel.mute ? <MicOff size={14} className="mx-auto" /> : <Mic size={14} className="mx-auto" />}
        </button>
      </div>

      {/* Processing Indicators */}
      <div className="flex justify-center space-x-1 mt-2">
        <div className={clsx(
          'w-2 h-2 rounded-full',
          channel.eq_enabled ? 'bg-blue-500' : 'bg-gray-600'
        )} title="EQ" />
        <div className={clsx(
          'w-2 h-2 rounded-full',
          channel.comp_enabled ? 'bg-orange-500' : 'bg-gray-600'
        )} title="Comp" />
        <div className={clsx(
          'w-2 h-2 rounded-full',
          channel.gate_enabled ? 'bg-purple-500' : 'bg-gray-600'
        )} title="Gate" />
      </div>
    </div>
  )
}
