import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Music, Plus, Search, Printer, Key, Save, Trash2, List } from 'lucide-react'
import clsx from 'clsx'
import type { Song } from '../types'

const API_BASE = '/api'

// API functions
const songsApi = {
  getAll: async (search?: string): Promise<Song[]> => {
    const params = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await fetch(`${API_BASE}/songs/${params}`)
    return res.json()
  },
  get: async (id: number): Promise<Song> => {
    const res = await fetch(`${API_BASE}/songs/${id}`)
    return res.json()
  },
  create: async (song: Partial<Song>): Promise<Song> => {
    const res = await fetch(`${API_BASE}/songs/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(song)
    })
    return res.json()
  },
  delete: async (id: number): Promise<void> => {
    await fetch(`${API_BASE}/songs/${id}`, { method: 'DELETE' })
  },
  getChart: async (id: number, key?: string): Promise<any> => {
    const params = key ? `?key=${key}&format=text` : '?format=text'
    const res = await fetch(`${API_BASE}/songs/${id}/chart${params}`)
    return res.json()
  },
  transpose: async (id: number, targetKey: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/songs/${id}/transpose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_key: targetKey })
    })
    return res.json()
  },
  quickSaveScene: async (id: number): Promise<any> => {
    const res = await fetch(`${API_BASE}/songs/${id}/scene/save`, { method: 'POST' })
    return res.json()
  },
  getKeys: async (): Promise<{ keys: string[] }> => {
    const res = await fetch(`${API_BASE}/songs/keys`)
    return res.json()
  },
  searchExternal: async (query: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/songs/search/external?q=${encodeURIComponent(query)}`)
    return res.json()
  }
}

type ViewMode = 'list' | 'detail' | 'create' | 'import'

export default function SongsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSong, setSelectedSong] = useState<Song | null>(null)
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [externalSearchQuery, setExternalSearchQuery] = useState('')
  const [externalResults, setExternalResults] = useState<any>(null)

  const queryClient = useQueryClient()

  // Queries
  const { data: songs, isLoading } = useQuery({
    queryKey: ['songs', searchQuery],
    queryFn: () => songsApi.getAll(searchQuery || undefined)
  })

  const { data: keys } = useQuery({
    queryKey: ['song-keys'],
    queryFn: songsApi.getKeys
  })

  const { data: chartData, refetch: refetchChart } = useQuery({
    queryKey: ['song-chart', selectedSong?.id, selectedKey],
    queryFn: () => selectedSong ? songsApi.getChart(selectedSong.id, selectedKey || undefined) : null,
    enabled: !!selectedSong && viewMode === 'detail'
  })

  // Mutations
  const createSong = useMutation({
    mutationFn: songsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['songs'] })
      setViewMode('list')
    }
  })

  const deleteSong = useMutation({
    mutationFn: songsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['songs'] })
      setSelectedSong(null)
      setViewMode('list')
    }
  })

  const quickSave = useMutation({
    mutationFn: (id: number) => songsApi.quickSaveScene(id),
    onSuccess: (data) => {
      alert(data.message || 'Scene saved!')
    }
  })

  const handleExternalSearch = async () => {
    if (externalSearchQuery.length < 2) return
    const results = await songsApi.searchExternal(externalSearchQuery)
    setExternalResults(results)
  }

  const handleSelectSong = (song: Song) => {
    setSelectedSong(song)
    setSelectedKey(song.original_key)
    setViewMode('detail')
  }

  const handlePrint = () => {
    if (!selectedSong) return
    window.open(`${API_BASE}/songs/${selectedSong.id}/print${selectedKey ? `?key=${selectedKey}` : ''}`, '_blank')
  }

  // New song form state
  const [newSong, setNewSong] = useState({
    title: '',
    artist_name: '',
    original_key: 'C',
    tempo: '',
    chord_chart: '',
    lyrics: '',
    genre: ''
  })

  const handleCreateSong = () => {
    createSong.mutate({
      ...newSong,
      tempo: newSong.tempo ? parseInt(newSong.tempo) : undefined
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading songs...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Music className="w-6 h-6" />
          Songs & Setlists
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('list')}
            className={clsx(
              'px-4 py-2 rounded flex items-center gap-2',
              viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
            )}
          >
            <List className="w-4 h-4" /> Library
          </button>
          <button
            onClick={() => setViewMode('create')}
            className={clsx(
              'px-4 py-2 rounded flex items-center gap-2',
              viewMode === 'create' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
            )}
          >
            <Plus className="w-4 h-4" /> Add Song
          </button>
          <button
            onClick={() => setViewMode('import')}
            className={clsx(
              'px-4 py-2 rounded flex items-center gap-2',
              viewMode === 'import' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
            )}
          >
            <Search className="w-4 h-4" /> Import
          </button>
        </div>
      </div>

      {/* List View */}
      {viewMode === 'list' && (
        <div className="space-y-4">
          {/* Search */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search songs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded"
              />
            </div>
          </div>

          {/* Songs Table */}
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-800">
                <tr>
                  <th className="text-left p-3">Title</th>
                  <th className="text-left p-3">Artist</th>
                  <th className="text-left p-3">Key</th>
                  <th className="text-left p-3">Tempo</th>
                  <th className="text-left p-3">Genre</th>
                  <th className="text-left p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {songs?.map((song) => (
                  <tr
                    key={song.id}
                    className="border-t border-gray-700 hover:bg-gray-800 cursor-pointer"
                    onClick={() => handleSelectSong(song)}
                  >
                    <td className="p-3 font-medium">{song.title}</td>
                    <td className="p-3 text-gray-400">{song.artist_name}</td>
                    <td className="p-3">
                      <span className="px-2 py-1 bg-blue-600 rounded text-sm">{song.original_key}</span>
                    </td>
                    <td className="p-3 text-gray-400">{song.tempo ? `${song.tempo} BPM` : '-'}</td>
                    <td className="p-3 text-gray-400">{song.genre || '-'}</td>
                    <td className="p-3">
                      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                        {song.default_scene_id && (
                          <button
                            onClick={() => quickSave.mutate(song.id)}
                            className="p-1 text-green-400 hover:text-green-300"
                            title="Quick save scene"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => deleteSong.mutate(song.id)}
                          className="p-1 text-red-400 hover:text-red-300"
                          title="Delete song"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {songs?.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-gray-400">
                      No songs found. Add some songs to get started!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail View */}
      {viewMode === 'detail' && selectedSong && (
        <div className="space-y-4">
          <button
            onClick={() => setViewMode('list')}
            className="text-blue-400 hover:text-blue-300"
          >
            &larr; Back to Library
          </button>

          <div className="card">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold">{selectedSong.title}</h2>
                <p className="text-gray-400">{selectedSong.artist_name}</p>
              </div>
              <div className="flex gap-2">
                {selectedSong.default_scene_id && (
                  <button
                    onClick={() => quickSave.mutate(selectedSong.id)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" /> Quick Save Scene
                  </button>
                )}
                <button
                  onClick={handlePrint}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2"
                >
                  <Printer className="w-4 h-4" /> Print
                </button>
              </div>
            </div>

            {/* Key Selector */}
            <div className="flex items-center gap-4 mb-4">
              <span className="text-gray-400">Display Key:</span>
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-gray-400" />
                <select
                  value={selectedKey}
                  onChange={(e) => {
                    setSelectedKey(e.target.value)
                    refetchChart()
                  }}
                  className="bg-gray-800 border border-gray-700 rounded px-3 py-1"
                >
                  {keys?.keys.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>
              {selectedKey !== selectedSong.original_key && (
                <span className="text-yellow-400 text-sm">
                  (Original: {selectedSong.original_key})
                </span>
              )}
            </div>

            {/* Song Info */}
            <div className="grid grid-cols-4 gap-4 mb-4 text-sm">
              <div>
                <span className="text-gray-400">Tempo:</span>
                <span className="ml-2">{selectedSong.tempo || 'N/A'} BPM</span>
              </div>
              <div>
                <span className="text-gray-400">Time:</span>
                <span className="ml-2">{selectedSong.time_signature}</span>
              </div>
              <div>
                <span className="text-gray-400">Duration:</span>
                <span className="ml-2">
                  {selectedSong.duration_seconds
                    ? `${Math.floor(selectedSong.duration_seconds / 60)}:${(selectedSong.duration_seconds % 60).toString().padStart(2, '0')}`
                    : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Genre:</span>
                <span className="ml-2">{selectedSong.genre || 'N/A'}</span>
              </div>
            </div>

            {/* Chord Chart */}
            {chartData?.chart && (
              <div className="bg-gray-900 p-4 rounded font-mono text-sm whitespace-pre-wrap">
                {chartData.chart}
              </div>
            )}

            {!chartData?.chart && !selectedSong.chord_chart && (
              <div className="bg-gray-900 p-4 rounded text-gray-400 text-center">
                No chord chart available for this song.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create View */}
      {viewMode === 'create' && (
        <div className="card max-w-2xl">
          <h2 className="text-xl font-bold mb-4">Add New Song</h2>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Title *</label>
                <input
                  type="text"
                  value={newSong.title}
                  onChange={(e) => setNewSong({ ...newSong, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                  placeholder="Song title"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Original Artist *</label>
                <input
                  type="text"
                  value={newSong.artist_name}
                  onChange={(e) => setNewSong({ ...newSong, artist_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                  placeholder="Artist name"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Key</label>
                <select
                  value={newSong.original_key}
                  onChange={(e) => setNewSong({ ...newSong, original_key: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                >
                  {keys?.keys.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Tempo (BPM)</label>
                <input
                  type="number"
                  value={newSong.tempo}
                  onChange={(e) => setNewSong({ ...newSong, tempo: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                  placeholder="120"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Genre</label>
                <input
                  type="text"
                  value={newSong.genre}
                  onChange={(e) => setNewSong({ ...newSong, genre: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                  placeholder="Rock, Pop, etc."
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Chord Chart (ChordPro format)</label>
              <textarea
                value={newSong.chord_chart}
                onChange={(e) => setNewSong({ ...newSong, chord_chart: e.target.value })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded h-40 font-mono text-sm"
                placeholder="{title: Song Title}&#10;{key: C}&#10;&#10;[C]Amazing [G]grace, how [Am]sweet the [F]sound"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Lyrics</label>
              <textarea
                value={newSong.lyrics}
                onChange={(e) => setNewSong({ ...newSong, lyrics: e.target.value })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded h-32"
                placeholder="Plain text lyrics..."
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCreateSong}
                disabled={!newSong.title || !newSong.artist_name}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50"
              >
                Create Song
              </button>
              <button
                onClick={() => setViewMode('list')}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import View */}
      {viewMode === 'import' && (
        <div className="card max-w-2xl">
          <h2 className="text-xl font-bold mb-4">Import from External Sources</h2>

          <div className="space-y-4">
            <p className="text-gray-400">
              Search for chord charts on popular open source sites, then import them into your local library.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={externalSearchQuery}
                onChange={(e) => setExternalSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleExternalSearch()}
                className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded"
                placeholder="Search for a song..."
              />
              <button
                onClick={handleExternalSearch}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded flex items-center gap-2"
              >
                <Search className="w-4 h-4" /> Search
              </button>
            </div>

            {externalResults && (
              <div className="bg-gray-800 p-4 rounded">
                <h3 className="font-medium mb-2">Search "{externalResults.query}" on:</h3>
                <div className="space-y-2">
                  {Object.entries(externalResults.search_urls || {}).map(([source, url]) => (
                    <a
                      key={source}
                      href={url as string}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-2 bg-gray-700 rounded hover:bg-gray-600"
                    >
                      {source.replace('_', ' ').toUpperCase()} &rarr;
                    </a>
                  ))}
                </div>
                <p className="mt-4 text-sm text-gray-400">
                  Find the chord chart you want, copy it, and use "Add Song" to add it to your library.
                </p>
              </div>
            )}

            <div className="border-t border-gray-700 pt-4">
              <h3 className="font-medium mb-2">Supported ChordPro Format:</h3>
              <pre className="bg-gray-900 p-4 rounded text-sm font-mono overflow-x-auto">
{`{title: Song Title}
{artist: Artist Name}
{key: G}
{tempo: 120}

{start_of_verse}
[G]Here are the [D]chords above the [Em]lyrics
[C]Just put them in [D]brackets like [G]this
{end_of_verse}

{start_of_chorus}
[Em]Chorus [C]goes [G]here
{end_of_chorus}`}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
