import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, Plus, Trash2, Users, Music, MapPin } from 'lucide-react'
import clsx from 'clsx'
import api from '../services/api'

interface Show {
  id: number
  name: string
  description?: string
  venue?: string
  date?: string
  load_in_time?: string
  soundcheck_time?: string
  doors_time?: string
  show_time?: string
  technical_notes?: string
}

interface Band {
  id: number
  name: string
  genre?: string
  contact_name?: string
  notes?: string
}

const showsApi = {
  getAll: async (): Promise<Show[]> => {
    const { data } = await api.get('/shows/')
    return data
  },
  create: async (show: Partial<Show>): Promise<Show> => {
    const { data } = await api.post('/shows/', show)
    return data
  },
  update: async (id: number, show: Partial<Show>): Promise<Show> => {
    const { data } = await api.put(`/shows/${id}`, show)
    return data
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/shows/${id}`)
  },
  getBands: async (showId: number): Promise<{ bands: Band[] }> => {
    const { data } = await api.get(`/shows/${showId}/bands`)
    return data
  },
  addBand: async (showId: number, bandId: number): Promise<void> => {
    await api.post(`/shows/${showId}/bands/${bandId}`)
  },
  removeBand: async (showId: number, bandId: number): Promise<void> => {
    await api.delete(`/shows/${showId}/bands/${bandId}`)
  }
}

const bandsApi = {
  getAll: async (): Promise<Band[]> => {
    const { data } = await api.get('/bands/')
    return data
  },
  create: async (band: Partial<Band>): Promise<Band> => {
    const { data } = await api.post('/bands/', band)
    return data
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/bands/${id}`)
  }
}

export default function ShowsPage() {
  const queryClient = useQueryClient()
  const [selectedShow, setSelectedShow] = useState<Show | null>(null)
  const [isCreatingShow, setIsCreatingShow] = useState(false)
  const [isCreatingBand, setIsCreatingBand] = useState(false)
  const [newShowName, setNewShowName] = useState('')
  const [newShowVenue, setNewShowVenue] = useState('')
  const [newBandName, setNewBandName] = useState('')
  const [newBandGenre, setNewBandGenre] = useState('')

  const { data: shows, isLoading: showsLoading } = useQuery({
    queryKey: ['shows'],
    queryFn: showsApi.getAll,
  })

  const { data: bands } = useQuery({
    queryKey: ['bands'],
    queryFn: bandsApi.getAll,
  })

  const { data: showBands } = useQuery({
    queryKey: ['show-bands', selectedShow?.id],
    queryFn: () => selectedShow ? showsApi.getBands(selectedShow.id) : null,
    enabled: !!selectedShow,
  })

  const createShowMutation = useMutation({
    mutationFn: (show: Partial<Show>) => showsApi.create(show),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shows'] })
      setIsCreatingShow(false)
      setNewShowName('')
      setNewShowVenue('')
    },
  })

  const deleteShowMutation = useMutation({
    mutationFn: (id: number) => showsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shows'] })
      setSelectedShow(null)
    },
  })

  const createBandMutation = useMutation({
    mutationFn: (band: Partial<Band>) => bandsApi.create(band),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bands'] })
      setIsCreatingBand(false)
      setNewBandName('')
      setNewBandGenre('')
    },
  })

  const addBandToShowMutation = useMutation({
    mutationFn: ({ showId, bandId }: { showId: number; bandId: number }) =>
      showsApi.addBand(showId, bandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['show-bands'] })
    },
  })

  const removeBandFromShowMutation = useMutation({
    mutationFn: ({ showId, bandId }: { showId: number; bandId: number }) =>
      showsApi.removeBand(showId, bandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['show-bands'] })
    },
  })

  if (showsLoading) {
    return <div className="text-gray-400">Loading shows...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calendar size={24} />
          Shows & Bands
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => setIsCreatingBand(true)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Users size={16} />
            New Band
          </button>
          <button
            onClick={() => setIsCreatingShow(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus size={16} />
            New Show
          </button>
        </div>
      </div>

      {/* Create Show Form */}
      {isCreatingShow && (
        <div className="card border border-blue-500">
          <h2 className="text-lg font-semibold mb-4">Create New Show</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Show Name</label>
              <input
                type="text"
                value={newShowName}
                onChange={(e) => setNewShowName(e.target.value)}
                className="input"
                placeholder="e.g., Friday Night Live"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Venue</label>
              <input
                type="text"
                value={newShowVenue}
                onChange={(e) => setNewShowVenue(e.target.value)}
                className="input"
                placeholder="e.g., The Blue Note"
              />
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => createShowMutation.mutate({ name: newShowName, venue: newShowVenue })}
                className="btn btn-primary"
                disabled={!newShowName.trim()}
              >
                Create Show
              </button>
              <button onClick={() => setIsCreatingShow(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Band Form */}
      {isCreatingBand && (
        <div className="card border border-green-500">
          <h2 className="text-lg font-semibold mb-4">Create New Band</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Band Name</label>
              <input
                type="text"
                value={newBandName}
                onChange={(e) => setNewBandName(e.target.value)}
                className="input"
                placeholder="e.g., The Rockers"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Genre</label>
              <input
                type="text"
                value={newBandGenre}
                onChange={(e) => setNewBandGenre(e.target.value)}
                className="input"
                placeholder="e.g., Rock, Jazz, Pop"
              />
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => createBandMutation.mutate({ name: newBandName, genre: newBandGenre })}
                className="btn btn-primary"
                disabled={!newBandName.trim()}
              >
                Create Band
              </button>
              <button onClick={() => setIsCreatingBand(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shows List */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Shows ({shows?.length || 0})</h2>
            {shows && shows.length > 0 ? (
              <div className="space-y-3">
                {shows.map((show) => (
                  <div
                    key={show.id}
                    onClick={() => setSelectedShow(show)}
                    className={clsx(
                      'p-4 rounded-lg cursor-pointer transition-colors',
                      selectedShow?.id === show.id
                        ? 'bg-blue-900 border border-blue-500'
                        : 'bg-gray-800 hover:bg-gray-700'
                    )}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-lg">{show.name}</h3>
                        {show.venue && (
                          <div className="flex items-center gap-1 text-sm text-gray-400 mt-1">
                            <MapPin size={14} />
                            {show.venue}
                          </div>
                        )}
                        {show.date && (
                          <div className="flex items-center gap-1 text-sm text-gray-400">
                            <Calendar size={14} />
                            {new Date(show.date).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteShowMutation.mutate(show.id)
                        }}
                        className="p-2 hover:bg-red-900 rounded text-red-400"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No shows created yet.</p>
            )}
          </div>
        </div>

        {/* Show Details / Band Assignment */}
        <div>
          {selectedShow ? (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">{selectedShow.name}</h2>

              {selectedShow.venue && (
                <div className="mb-4">
                  <div className="text-sm text-gray-400">Venue</div>
                  <div>{selectedShow.venue}</div>
                </div>
              )}

              <h3 className="font-medium mb-2 flex items-center gap-2">
                <Music size={16} />
                Bands in Show
              </h3>

              {showBands?.bands && showBands.bands.length > 0 ? (
                <div className="space-y-2 mb-4">
                  {showBands.bands.map((band) => (
                    <div
                      key={band.id}
                      className="flex items-center justify-between p-2 bg-gray-800 rounded"
                    >
                      <div>
                        <span className="font-medium">{band.name}</span>
                        {band.genre && (
                          <span className="text-xs text-gray-400 ml-2">({band.genre})</span>
                        )}
                      </div>
                      <button
                        onClick={() => removeBandFromShowMutation.mutate({
                          showId: selectedShow.id,
                          bandId: band.id
                        })}
                        className="p-1 hover:bg-red-900 rounded text-red-400"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 mb-4">No bands assigned</p>
              )}

              {/* Add Band Dropdown */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Add Band</label>
                <select
                  className="input"
                  onChange={(e) => {
                    if (e.target.value) {
                      addBandToShowMutation.mutate({
                        showId: selectedShow.id,
                        bandId: parseInt(e.target.value)
                      })
                      e.target.value = ''
                    }
                  }}
                  defaultValue=""
                >
                  <option value="">Select a band...</option>
                  {bands?.filter(b =>
                    !showBands?.bands?.find(sb => sb.id === b.id)
                  ).map((band) => (
                    <option key={band.id} value={band.id}>
                      {band.name} {band.genre ? `(${band.genre})` : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="card">
              <p className="text-gray-400 text-center py-8">
                Select a show to manage bands
              </p>
            </div>
          )}

          {/* All Bands List */}
          <div className="card mt-4">
            <h2 className="text-lg font-semibold mb-4">All Bands ({bands?.length || 0})</h2>
            {bands && bands.length > 0 ? (
              <div className="space-y-2">
                {bands.map((band) => (
                  <div
                    key={band.id}
                    className="flex items-center justify-between p-2 bg-gray-800 rounded"
                  >
                    <div>
                      <span className="font-medium">{band.name}</span>
                      {band.genre && (
                        <span className="text-xs text-gray-400 ml-2">({band.genre})</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No bands created</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
