import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { patchApi, deviceApi } from '../services/api'
import { GitBranch, Plus, Trash2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

export default function PatchPage() {
  const queryClient = useQueryClient()
  const [selectedInput, setSelectedInput] = useState<number | null>(null)
  const [sourceType, setSourceType] = useState<'analog' | 'dante'>('analog')

  const { data: patches } = useQuery({
    queryKey: ['patches'],
    queryFn: () => patchApi.getAll(),
  })

  const { data: matrix } = useQuery({
    queryKey: ['patch-matrix'],
    queryFn: patchApi.getMatrix,
  })

  const { data: tioDevices } = useQuery({
    queryKey: ['tio-devices'],
    queryFn: deviceApi.getTioDevices,
  })

  const quickPatchMutation = useMutation({
    mutationFn: ({ input, sourceType, sourcePort, device }: any) =>
      patchApi.quickPatch(input, sourceType, sourcePort, device),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patches'] })
      queryClient.invalidateQueries({ queryKey: ['patch-matrix'] })
    },
  })

  const autoPatchTioMutation = useMutation({
    mutationFn: ({ tioName, startChannel }: { tioName: string; startChannel: number }) =>
      patchApi.autoPatchTio(tioName, startChannel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patches'] })
      queryClient.invalidateQueries({ queryKey: ['patch-matrix'] })
    },
  })

  const deletePatchMutation = useMutation({
    mutationFn: (id: number) => patchApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patches'] })
      queryClient.invalidateQueries({ queryKey: ['patch-matrix'] })
    },
  })

  const handleQuickPatch = (input: number, sourcePort: number, device?: string) => {
    quickPatchMutation.mutate({
      input,
      sourceType: sourceType === 'dante' ? 'dante_tio' : 'analog',
      sourcePort,
      device,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <GitBranch size={24} />
          Patch Bay
        </h1>
      </div>

      {/* Source Type Selection */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Source Type</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setSourceType('analog')}
            className={clsx(
              'px-4 py-2 rounded',
              sourceType === 'analog' ? 'bg-blue-600' : 'bg-gray-700'
            )}
          >
            Analog (Local)
          </button>
          <button
            onClick={() => setSourceType('dante')}
            className={clsx(
              'px-4 py-2 rounded',
              sourceType === 'dante' ? 'bg-blue-600' : 'bg-gray-700'
            )}
          >
            Dante (Network)
          </button>
        </div>
      </div>

      {/* TIO Auto-Patch */}
      {sourceType === 'dante' && tioDevices && tioDevices.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Quick TIO Patch</h2>
          <div className="flex flex-wrap gap-2">
            {tioDevices.map((tio) => (
              <button
                key={tio.name}
                onClick={() => autoPatchTioMutation.mutate({ tioName: tio.name, startChannel: 1 })}
                className="btn btn-primary flex items-center gap-2"
                disabled={autoPatchTioMutation.isPending}
              >
                <Plus size={16} />
                Auto-patch {tio.name}
              </button>
            ))}
          </div>
          <p className="text-sm text-gray-400 mt-2">
            Automatically maps TIO inputs 1-16 to TF-Rack channels 1-16
          </p>
        </div>
      )}

      {/* Patch Matrix */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Input Patch Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="py-2 px-4 text-left">TF-Rack Input</th>
                <th className="py-2 px-4 text-left">Source</th>
                <th className="py-2 px-4 text-left">Type</th>
                <th className="py-2 px-4 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 32 }, (_, i) => i + 1).map((input) => {
                const inputPatch = matrix?.inputs?.[input]
                return (
                  <tr
                    key={input}
                    className={clsx(
                      'border-b border-gray-800 hover:bg-gray-800',
                      selectedInput === input && 'bg-gray-800'
                    )}
                    onClick={() => setSelectedInput(input)}
                  >
                    <td className="py-2 px-4">CH {input}</td>
                    <td className="py-2 px-4">
                      {inputPatch ? (
                        inputPatch.type === 'analog' ? (
                          `Analog ${inputPatch.source}`
                        ) : (
                          `${inputPatch.source_device}:${inputPatch.source_port}`
                        )
                      ) : (
                        <span className="text-gray-500">Not patched</span>
                      )}
                    </td>
                    <td className="py-2 px-4">
                      <span className={clsx(
                        'px-2 py-1 rounded text-xs',
                        inputPatch?.type === 'dante' ? 'bg-green-900 text-green-300' : 'bg-blue-900 text-blue-300'
                      )}>
                        {inputPatch?.type || 'none'}
                      </span>
                    </td>
                    <td className="py-2 px-4">
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleQuickPatch(input, input, tioDevices?.[0]?.name)
                          }}
                          className="p-1 hover:bg-gray-700 rounded"
                          title="Quick patch"
                        >
                          <RefreshCw size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Active Patches */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Active Patches ({patches?.length || 0})</h2>
        {patches && patches.length > 0 ? (
          <div className="space-y-2">
            {patches.map((patch) => (
              <div
                key={patch.id}
                className="flex items-center justify-between p-3 bg-gray-800 rounded"
              >
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium">
                    {patch.source_device}:{patch.source_port}
                  </span>
                  <GitBranch size={16} className="text-gray-400" />
                  <span className="text-sm font-medium">
                    {patch.dest_device}:{patch.dest_port}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{patch.patch_type}</span>
                  <button
                    onClick={() => deletePatchMutation.mutate(patch.id)}
                    className="p-1 hover:bg-red-900 rounded text-red-400"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">No active patches</p>
        )}
      </div>
    </div>
  )
}
