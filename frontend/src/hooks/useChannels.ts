import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { channelApi } from '../services/api'
import type { Channel } from '../types'

export function useChannels(channelType?: string) {
  return useQuery({
    queryKey: ['channels', channelType],
    queryFn: () => channelApi.getAll(channelType),
  })
}

export function useChannel(id: number) {
  return useQuery({
    queryKey: ['channel', id],
    queryFn: () => channelApi.get(id),
    enabled: id > 0,
  })
}

export function useUpdateChannel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: Partial<Channel> }) =>
      channelApi.update(id, updates),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(['channel', variables.id], data)
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}

export function useSetFader() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, level }: { id: number; level: number }) =>
      channelApi.setFader(id, level),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['channel', variables.id] })
    },
  })
}

export function useToggleMute() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => channelApi.toggleMute(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['channel', id] })
      queryClient.invalidateQueries({ queryKey: ['channels'] })
    },
  })
}
