import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sceneApi } from '../services/api'
import { Film, Plus, Play, Save, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import type { Scene } from '../types'

export default function ScenesPage() {
  const queryClient = useQueryClient()
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [newSceneName, setNewSceneName] = useState('')
  const [newSceneNumber, setNewSceneNumber] = useState(1)

  const { data: scenes, isLoading } = useQuery({
    queryKey: ['scenes'],
    queryFn: sceneApi.getAll,
  })

  const createMutation = useMutation({
    mutationFn: (data: { scene_number: number; name: string }) =>
      sceneApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes'] })
      setIsCreating(false)
      setNewSceneName('')
    },
  })

  const storeMutation = useMutation({
    mutationFn: (id: number) => sceneApi.store(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes'] })
    },
  })

  const recallMutation = useMutation({
    mutationFn: (id: number) => sceneApi.recall(id, { update_eink: true }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => sceneApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes'] })
      setSelectedScene(null)
    },
  })

  const handleCreateScene = () => {
    if (newSceneName.trim()) {
      createMutation.mutate({
        scene_number: newSceneNumber,
        name: newSceneName.trim(),
      })
    }
  }

  const getNextSceneNumber = () => {
    if (!scenes || scenes.length === 0) return 1
    const maxNumber = Math.max(...scenes.map(s => s.scene_number))
    return maxNumber + 1
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading scenes...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Film size={24} />
          Scene Management
        </h1>
        <button
          onClick={() => {
            setIsCreating(true)
            setNewSceneNumber(getNextSceneNumber())
          }}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus size={16} />
          New Scene
        </button>
      </div>

      {/* Create Scene Modal */}
      {isCreating && (
        <div className="card border border-blue-500">
          <h2 className="text-lg font-semibold mb-4">Create New Scene</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Scene Number</label>
              <input
                type="number"
                value={newSceneNumber}
                onChange={(e) => setNewSceneNumber(parseInt(e.target.value) || 1)}
                className="input w-32"
                min={1}
                max={200}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Scene Name</label>
              <input
                type="text"
                value={newSceneName}
                onChange={(e) => setNewSceneName(e.target.value)}
                className="input"
                placeholder="Enter scene name"
                maxLength={64}
              />
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleCreateScene}
                className="btn btn-primary"
                disabled={!newSceneName.trim() || createMutation.isPending}
              >
                Create
              </button>
              <button
                onClick={() => setIsCreating(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scene List */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Scenes ({scenes?.length || 0})</h2>
            {scenes && scenes.length > 0 ? (
              <div className="space-y-2">
                {scenes.map((scene) => (
                  <div
                    key={scene.id}
                    onClick={() => setSelectedScene(scene)}
                    className={clsx(
                      'flex items-center justify-between p-3 rounded cursor-pointer transition-colors',
                      selectedScene?.id === scene.id
                        ? 'bg-blue-900 border border-blue-500'
                        : 'bg-gray-800 hover:bg-gray-700'
                    )}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl font-bold text-gray-400 w-12">
                        {scene.scene_number.toString().padStart(2, '0')}
                      </span>
                      <div>
                        <div className="font-medium">{scene.name}</div>
                        {scene.description && (
                          <div className="text-sm text-gray-400">{scene.description}</div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {scene.fade_time > 0 && (
                        <span className="text-xs text-gray-400">{scene.fade_time}s fade</span>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          recallMutation.mutate(scene.id)
                        }}
                        className="p-2 hover:bg-green-900 rounded text-green-400"
                        title="Recall scene"
                      >
                        <Play size={16} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          storeMutation.mutate(scene.id)
                        }}
                        className="p-2 hover:bg-blue-900 rounded text-blue-400"
                        title="Store current state"
                      >
                        <Save size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No scenes created. Create your first scene to get started.</p>
            )}
          </div>
        </div>

        {/* Scene Details */}
        <div className="lg:col-span-1">
          {selectedScene ? (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Scene Details</h2>
                <button
                  onClick={() => deleteMutation.mutate(selectedScene.id)}
                  className="p-2 hover:bg-red-900 rounded text-red-400"
                  title="Delete scene"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-gray-400">Number</label>
                  <div className="text-2xl font-bold">{selectedScene.scene_number}</div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">Name</label>
                  <div className="font-medium">{selectedScene.name}</div>
                </div>

                {selectedScene.description && (
                  <div>
                    <label className="text-sm text-gray-400">Description</label>
                    <div className="text-sm">{selectedScene.description}</div>
                  </div>
                )}

                <div>
                  <label className="text-sm text-gray-400">Fade Time</label>
                  <div>{selectedScene.fade_time}s</div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">E-Ink Labels</label>
                  <div className="text-sm">
                    {selectedScene.eink_labels && Object.keys(selectedScene.eink_labels).length > 0
                      ? `${Object.keys(selectedScene.eink_labels).length} labels`
                      : 'None'}
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-700 space-y-2">
                  <button
                    onClick={() => recallMutation.mutate(selectedScene.id)}
                    className="btn btn-primary w-full flex items-center justify-center gap-2"
                    disabled={recallMutation.isPending}
                  >
                    <Play size={16} />
                    Recall Scene
                  </button>
                  <button
                    onClick={() => storeMutation.mutate(selectedScene.id)}
                    className="btn btn-secondary w-full flex items-center justify-center gap-2"
                    disabled={storeMutation.isPending}
                  >
                    <Save size={16} />
                    Store Current State
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <p className="text-gray-400 text-center py-8">
                Select a scene to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
