import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User, Plus, Trash2, Edit2, Mic, Headphones, Upload, Camera } from 'lucide-react'
import clsx from 'clsx'
import api from '../services/api'

interface Artist {
  id: number
  name: string
  email?: string
  phone?: string
  primary_instrument?: string
  secondary_instruments?: string[]
  preferred_mic?: string
  preferred_di?: string
  in_ear_model?: string
  label_text?: string
  notes?: string
  bands?: { id: number; name: string }[]
  channel_preset?: Record<string, any>
}

const artistsApi = {
  getAll: async (): Promise<Artist[]> => {
    const { data } = await api.get('/artists/')
    return data
  },
  get: async (id: number): Promise<Artist> => {
    const { data } = await api.get(`/artists/${id}`)
    return data
  },
  create: async (artist: Partial<Artist>): Promise<Artist> => {
    const { data } = await api.post('/artists/', artist)
    return data
  },
  update: async (id: number, artist: Partial<Artist>): Promise<Artist> => {
    const { data } = await api.put(`/artists/${id}`, artist)
    return data
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/artists/${id}`)
  },
  uploadImage: async (id: number, file: File): Promise<void> => {
    const formData = new FormData()
    formData.append('file', file)
    await api.post(`/backstage/artists/${id}/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export default function ArtistsPage() {
  const queryClient = useQueryClient()
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    primary_instrument: '',
    preferred_mic: '',
    in_ear_model: '',
    label_text: '',
    notes: ''
  })

  const { data: artists, isLoading } = useQuery({
    queryKey: ['artists'],
    queryFn: artistsApi.getAll,
  })

  const { data: artistDetails } = useQuery({
    queryKey: ['artist', selectedArtist?.id],
    queryFn: () => selectedArtist ? artistsApi.get(selectedArtist.id) : null,
    enabled: !!selectedArtist,
  })

  const createMutation = useMutation({
    mutationFn: (artist: Partial<Artist>) => artistsApi.create(artist),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artists'] })
      setIsCreating(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Artist> }) =>
      artistsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artists'] })
      queryClient.invalidateQueries({ queryKey: ['artist'] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => artistsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artists'] })
      setSelectedArtist(null)
    },
  })

  const uploadImageMutation = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) =>
      artistsApi.uploadImage(id, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artist'] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      primary_instrument: '',
      preferred_mic: '',
      in_ear_model: '',
      label_text: '',
      notes: ''
    })
  }

  const handleEdit = () => {
    if (artistDetails) {
      setFormData({
        name: artistDetails.name || '',
        primary_instrument: artistDetails.primary_instrument || '',
        preferred_mic: artistDetails.preferred_mic || '',
        in_ear_model: artistDetails.in_ear_model || '',
        label_text: artistDetails.label_text || '',
        notes: artistDetails.notes || ''
      })
      setIsEditing(true)
    }
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0] && selectedArtist) {
      uploadImageMutation.mutate({ id: selectedArtist.id, file: e.target.files[0] })
    }
  }

  const instruments = [
    'Lead Vocals', 'Backup Vocals', 'Electric Guitar', 'Acoustic Guitar', 'Bass',
    'Drums', 'Keyboards', 'Saxophone', 'Trumpet', 'Violin', 'Percussion', 'DJ'
  ]

  const microphones = [
    'Shure SM58', 'Shure Beta 58A', 'Shure Beta 87A', 'Shure SM57',
    'Shure ULX-D HH Beta 58', 'Sennheiser e835', 'Sennheiser e945',
    'Audio-Technica AE4100', 'Shure QLXD2/B58'
  ]

  const iemSystems = [
    'Shure PSM 300', 'Shure PSM 900', 'Shure PSM 1000',
    'Sennheiser EW IEM G4', 'Audio-Technica M3'
  ]

  if (isLoading) {
    return <div className="text-gray-400">Loading artists...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <User size={24} />
          Artists
        </h1>
        <button
          onClick={() => { setIsCreating(true); resetForm() }}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus size={16} />
          New Artist
        </button>
      </div>

      {/* Create/Edit Form */}
      {(isCreating || isEditing) && (
        <div className="card border border-blue-500">
          <h2 className="text-lg font-semibold mb-4">
            {isCreating ? 'Create New Artist' : 'Edit Artist'}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="input"
                placeholder="Artist name"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Instrument/Role</label>
              <select
                value={formData.primary_instrument}
                onChange={(e) => setFormData(prev => ({ ...prev, primary_instrument: e.target.value }))}
                className="input"
              >
                <option value="">Select...</option>
                {instruments.map(inst => (
                  <option key={inst} value={inst}>{inst}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Preferred Microphone</label>
              <select
                value={formData.preferred_mic}
                onChange={(e) => setFormData(prev => ({ ...prev, preferred_mic: e.target.value }))}
                className="input"
              >
                <option value="">Select...</option>
                {microphones.map(mic => (
                  <option key={mic} value={mic}>{mic}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">IEM System</label>
              <select
                value={formData.in_ear_model}
                onChange={(e) => setFormData(prev => ({ ...prev, in_ear_model: e.target.value }))}
                className="input"
              >
                <option value="">Select...</option>
                {iemSystems.map(iem => (
                  <option key={iem} value={iem}>{iem}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">E-Ink Label</label>
              <input
                type="text"
                value={formData.label_text}
                onChange={(e) => setFormData(prev => ({ ...prev, label_text: e.target.value }))}
                className="input"
                placeholder="Display label (max 12 chars)"
                maxLength={12}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Notes</label>
              <input
                type="text"
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                className="input"
                placeholder="Additional notes"
              />
            </div>
          </div>
          <div className="flex space-x-2 mt-4">
            <button
              onClick={() => {
                if (isEditing && selectedArtist) {
                  updateMutation.mutate({ id: selectedArtist.id, data: formData })
                } else {
                  createMutation.mutate(formData)
                }
              }}
              className="btn btn-primary"
              disabled={!formData.name.trim()}
            >
              {isCreating ? 'Create' : 'Save'}
            </button>
            <button
              onClick={() => { setIsCreating(false); setIsEditing(false); resetForm() }}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Artists List */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">All Artists ({artists?.length || 0})</h2>
            {artists && artists.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {artists.map((artist) => (
                  <div
                    key={artist.id}
                    onClick={() => setSelectedArtist(artist)}
                    className={clsx(
                      'p-4 rounded-lg cursor-pointer transition-colors',
                      selectedArtist?.id === artist.id
                        ? 'bg-blue-900 border border-blue-500'
                        : 'bg-gray-800 hover:bg-gray-700'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gray-700 rounded-full flex items-center justify-center">
                        {artist.channel_preset?.image_path ? (
                          <img
                            src={`/api/backstage/artists/${artist.id}/image`}
                            alt={artist.name}
                            className="w-12 h-12 rounded-full object-cover"
                          />
                        ) : (
                          <User size={24} className="text-gray-400" />
                        )}
                      </div>
                      <div>
                        <div className="font-medium">{artist.name}</div>
                        <div className="text-sm text-gray-400">
                          {artist.primary_instrument || 'No instrument set'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No artists created yet.</p>
            )}
          </div>
        </div>

        {/* Artist Details */}
        <div>
          {artistDetails ? (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Artist Details</h2>
                <div className="flex gap-2">
                  <button onClick={handleEdit} className="p-2 hover:bg-gray-700 rounded">
                    <Edit2 size={16} />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(artistDetails.id)}
                    className="p-2 hover:bg-red-900 rounded text-red-400"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Artist Image */}
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <div className="w-24 h-24 bg-gray-700 rounded-full flex items-center justify-center overflow-hidden">
                    {artistDetails.channel_preset?.image_path ? (
                      <img
                        src={`/api/backstage/artists/${artistDetails.id}/image`}
                        alt={artistDetails.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User size={40} className="text-gray-400" />
                    )}
                  </div>
                  <label className="absolute bottom-0 right-0 p-1 bg-blue-600 rounded-full cursor-pointer hover:bg-blue-700">
                    <Camera size={16} />
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              <div className="text-center mb-4">
                <h3 className="text-xl font-bold">{artistDetails.name}</h3>
                <div className="text-gray-400">{artistDetails.primary_instrument}</div>
              </div>

              <div className="space-y-3 text-sm">
                {artistDetails.preferred_mic && (
                  <div className="flex items-center gap-2">
                    <Mic size={16} className="text-gray-400" />
                    <span>{artistDetails.preferred_mic}</span>
                  </div>
                )}
                {artistDetails.in_ear_model && (
                  <div className="flex items-center gap-2">
                    <Headphones size={16} className="text-gray-400" />
                    <span>{artistDetails.in_ear_model}</span>
                  </div>
                )}
                {artistDetails.label_text && (
                  <div>
                    <span className="text-gray-400">E-Ink Label:</span>
                    <span className="ml-2 font-mono bg-gray-200 text-gray-900 px-2 py-0.5 rounded">
                      {artistDetails.label_text}
                    </span>
                  </div>
                )}
                {artistDetails.bands && artistDetails.bands.length > 0 && (
                  <div>
                    <span className="text-gray-400">Bands:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {artistDetails.bands.map(band => (
                        <span key={band.id} className="px-2 py-0.5 bg-gray-700 rounded text-xs">
                          {band.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="card">
              <p className="text-gray-400 text-center py-8">
                Select an artist to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
