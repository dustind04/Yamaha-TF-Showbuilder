import { create } from 'zustand'
import type { WSMessage } from '../types'

interface WebSocketState {
  socket: WebSocket | null
  connected: boolean
  meters: number[]
  connect: () => void
  disconnect: () => void
  subscribe: (topic: string) => void
  unsubscribe: (topic: string) => void
  onMessage: (callback: (msg: WSMessage) => void) => () => void
}

const messageCallbacks: Set<(msg: WSMessage) => void> = new Set()

export const useWebSocket = create<WebSocketState>((set, get) => ({
  socket: null,
  connected: false,
  meters: new Array(32).fill(0),

  connect: () => {
    const wsUrl = `ws://${window.location.host}/ws/live`
    const socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      console.log('WebSocket connected')
      set({ socket, connected: true })
    }

    socket.onclose = () => {
      console.log('WebSocket disconnected')
      set({ socket: null, connected: false })
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (!get().connected) {
          get().connect()
        }
      }, 3000)
    }

    socket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)

        // Handle meter updates internally
        if (msg.type === 'meters' && msg.inputs) {
          set({ meters: msg.inputs })
        }

        // Notify all callbacks
        messageCallbacks.forEach((callback) => callback(msg))
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    set({ socket })
  },

  disconnect: () => {
    const { socket } = get()
    if (socket) {
      socket.close()
      set({ socket: null, connected: false })
    }
  },

  subscribe: (topic: string) => {
    const { socket, connected } = get()
    if (socket && connected) {
      socket.send(JSON.stringify({ type: 'subscribe', topic }))
    }
  },

  unsubscribe: (topic: string) => {
    const { socket, connected } = get()
    if (socket && connected) {
      socket.send(JSON.stringify({ type: 'unsubscribe', topic }))
    }
  },

  onMessage: (callback: (msg: WSMessage) => void) => {
    messageCallbacks.add(callback)
    return () => messageCallbacks.delete(callback)
  },
}))
