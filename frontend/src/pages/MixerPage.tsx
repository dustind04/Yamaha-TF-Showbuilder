import { useState } from 'react'
import { useChannels } from '../hooks/useChannels'
import ChannelStrip from '../components/ChannelStrip'
import clsx from 'clsx'

type ViewMode = 'all' | 'inputs' | 'aux' | 'dca'

export default function MixerPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('inputs')
  const [channelRange, setChannelRange] = useState<[number, number]>([1, 16])

  const channelType = viewMode === 'all' ? undefined : viewMode === 'inputs' ? 'input' : viewMode
  const { data: channels, isLoading, error } = useChannels(channelType)

  const filteredChannels = channels?.filter(ch => {
    if (viewMode === 'inputs') {
      return ch.channel_number >= channelRange[0] && ch.channel_number <= channelRange[1]
    }
    return true
  })

  const channelRanges = [
    { label: '1-16', range: [1, 16] as [number, number] },
    { label: '17-32', range: [17, 32] as [number, number] },
    { label: 'All', range: [1, 32] as [number, number] },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading channels...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-400">Error loading channels</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex space-x-2">
          {(['inputs', 'aux', 'dca', 'all'] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={clsx(
                'px-4 py-2 rounded text-sm font-medium transition-colors',
                viewMode === mode
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              )}
            >
              {mode === 'inputs' ? 'Inputs' :
               mode === 'aux' ? 'AUX' :
               mode === 'dca' ? 'DCA' : 'All'}
            </button>
          ))}
        </div>

        {viewMode === 'inputs' && (
          <div className="flex space-x-2">
            {channelRanges.map(({ label, range }) => (
              <button
                key={label}
                onClick={() => setChannelRange(range)}
                className={clsx(
                  'px-3 py-1 rounded text-sm transition-colors',
                  channelRange[0] === range[0] && channelRange[1] === range[1]
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                )}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Channel Strips */}
      <div className="bg-mixer-bg rounded-lg p-4 overflow-x-auto">
        <div className="flex space-x-2 min-w-max">
          {filteredChannels?.map((channel) => (
            <ChannelStrip
              key={channel.id}
              channel={channel}
              showMeter={true}
            />
          ))}
        </div>
      </div>

      {/* Master Section */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Master</h3>
        <div className="flex space-x-4">
          <div className="flex flex-col items-center">
            <span className="text-sm text-gray-400 mb-2">Stereo</span>
            <div className="w-12 h-48 bg-mixer-fader rounded flex items-center justify-center">
              <input
                type="range"
                min="-90"
                max="10"
                defaultValue="0"
                className="h-40 w-2 appearance-none bg-gray-600 rounded cursor-pointer"
                style={{
                  writingMode: 'vertical-lr',
                  direction: 'rtl',
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
