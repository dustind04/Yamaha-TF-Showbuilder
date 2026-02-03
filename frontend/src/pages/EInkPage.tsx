import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { einkApi, channelApi } from '../services/api'
import { Monitor, RefreshCw, Trash2, Edit2, Check, TestTube } from 'lucide-react'
import clsx from 'clsx'

export default function EInkPage() {
  const queryClient = useQueryClient()
  const [editingDisplay, setEditingDisplay] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [bulkLabels, setBulkLabels] = useState<Record<number, string>>({})

  const { data: displays, isLoading } = useQuery({
    queryKey: ['eink-status'],
    queryFn: einkApi.getStatus,
    refetchInterval: 5000,
  })

  const { data: channels } = useQuery({
    queryKey: ['channels', 'input'],
    queryFn: () => channelApi.getAll('input'),
  })

  const updateDisplayMutation = useMutation({
    mutationFn: ({ index, text }: { index: number; text: string }) =>
      einkApi.updateDisplay(index, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
      setEditingDisplay(null)
    },
  })

  const updateChannelLabelMutation = useMutation({
    mutationFn: ({ channel, text }: { channel: number; text: string }) =>
      einkApi.updateChannelLabel(channel, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
    },
  })

  const bulkUpdateMutation = useMutation({
    mutationFn: (labels: Record<number, string>) => einkApi.bulkUpdate(labels),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
    },
  })

  const clearAllMutation = useMutation({
    mutationFn: einkApi.clearAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
    },
  })

  const refreshMutation = useMutation({
    mutationFn: einkApi.refresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
    },
  })

  const testPatternMutation = useMutation({
    mutationFn: einkApi.testPattern,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eink-status'] })
    },
  })

  const handleStartEdit = (index: number, currentText: string) => {
    setEditingDisplay(index)
    setEditText(currentText)
  }

  const handleSaveEdit = (index: number) => {
    updateDisplayMutation.mutate({ index, text: editText })
  }

  const handleSyncFromChannels = () => {
    if (channels) {
      const labels: Record<number, string> = {}
      channels.forEach((ch) => {
        if (ch.name) {
          labels[ch.channel_number] = ch.name
        }
      })
      bulkUpdateMutation.mutate(labels)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading displays...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Monitor size={24} />
          E-Ink Display Management
        </h1>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleSyncFromChannels}
            className="btn btn-primary flex items-center gap-2"
            disabled={bulkUpdateMutation.isPending}
          >
            <RefreshCw size={16} />
            Sync from Channel Names
          </button>
          <button
            onClick={() => refreshMutation.mutate()}
            className="btn btn-secondary flex items-center gap-2"
            disabled={refreshMutation.isPending}
          >
            <RefreshCw size={16} className={refreshMutation.isPending ? 'animate-spin' : ''} />
            Refresh All Displays
          </button>
          <button
            onClick={() => testPatternMutation.mutate()}
            className="btn btn-secondary flex items-center gap-2"
            disabled={testPatternMutation.isPending}
          >
            <TestTube size={16} />
            Test Pattern
          </button>
          <button
            onClick={() => clearAllMutation.mutate()}
            className="btn btn-danger flex items-center gap-2"
            disabled={clearAllMutation.isPending}
          >
            <Trash2 size={16} />
            Clear All
          </button>
        </div>
      </div>

      {/* Display Grid */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">
          Display Status ({displays?.filter(d => d.connected).length || 0} / {displays?.length || 16} connected)
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {(displays || Array.from({ length: 16 }, (_, i) => ({
            index: i,
            connected: false,
            current_text: '',
            channel_number: i + 1,
          }))).map((display) => (
            <div
              key={display.index}
              className={clsx(
                'p-3 rounded-lg border-2 transition-colors',
                display.connected
                  ? 'bg-gray-800 border-green-600'
                  : 'bg-gray-900 border-gray-700'
              )}
            >
              {/* Display Header */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">CH {display.index + 1}</span>
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  display.connected ? 'bg-green-500' : 'bg-gray-600'
                )} />
              </div>

              {/* E-Ink Display Simulation */}
              <div className="bg-gray-200 text-gray-900 rounded p-2 h-16 flex items-center justify-center text-center">
                {editingDisplay === display.index ? (
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full text-center bg-white border border-gray-400 rounded px-1 text-sm"
                    maxLength={12}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit(display.index)
                      if (e.key === 'Escape') setEditingDisplay(null)
                    }}
                  />
                ) : (
                  <span className="font-mono text-sm font-bold truncate">
                    {display.current_text || '---'}
                  </span>
                )}
              </div>

              {/* Actions */}
              <div className="flex justify-center mt-2 space-x-1">
                {editingDisplay === display.index ? (
                  <button
                    onClick={() => handleSaveEdit(display.index)}
                    className="p-1 bg-green-700 rounded hover:bg-green-600"
                    title="Save"
                  >
                    <Check size={14} />
                  </button>
                ) : (
                  <button
                    onClick={() => handleStartEdit(display.index, display.current_text)}
                    className="p-1 bg-gray-700 rounded hover:bg-gray-600"
                    title="Edit"
                  >
                    <Edit2 size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bulk Edit */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Bulk Edit Labels</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          {Array.from({ length: 16 }, (_, i) => {
            const channel = channels?.find(c => c.channel_number === i + 1)
            return (
              <div key={i} className="space-y-1">
                <label className="text-xs text-gray-400">CH {i + 1}</label>
                <input
                  type="text"
                  value={bulkLabels[i + 1] || channel?.name || ''}
                  onChange={(e) => setBulkLabels(prev => ({
                    ...prev,
                    [i + 1]: e.target.value
                  }))}
                  className="input text-sm py-1"
                  placeholder="Label"
                  maxLength={12}
                />
              </div>
            )
          })}
        </div>
        <button
          onClick={() => bulkUpdateMutation.mutate(bulkLabels)}
          className="btn btn-primary mt-4"
          disabled={bulkUpdateMutation.isPending || Object.keys(bulkLabels).length === 0}
        >
          Update All Labels
        </button>
      </div>

      {/* Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">About E-Ink Displays</h2>
        <div className="text-sm text-gray-400 space-y-2">
          <p>
            E-ink displays are positioned above each physical input on the TF-Rack
            or TIO stage box to show channel labels that are visible without power.
          </p>
          <p>
            Labels automatically update when channel names change or when scenes
            are recalled with saved label information.
          </p>
          <p>
            <strong>Supported displays:</strong> Waveshare 2.9" e-Paper (296x128)
          </p>
        </div>
      </div>
    </div>
  )
}
