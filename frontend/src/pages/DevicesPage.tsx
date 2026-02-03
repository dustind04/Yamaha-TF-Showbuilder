import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { deviceApi } from '../services/api'
import { Wifi, RefreshCw, Power, PowerOff, Server, Radio } from 'lucide-react'
import clsx from 'clsx'

export default function DevicesPage() {
  const queryClient = useQueryClient()
  const [tfIpAddress, setTfIpAddress] = useState('')

  const { data: tfStatus } = useQuery({
    queryKey: ['tf-rack-status'],
    queryFn: deviceApi.getTFRackStatus,
    refetchInterval: 5000,
  })

  const { data: danteDevices, isLoading: danteLoading } = useQuery({
    queryKey: ['dante-devices'],
    queryFn: deviceApi.getDanteDevices,
    refetchInterval: 10000,
  })

  const { data: tioDevices } = useQuery({
    queryKey: ['tio-devices'],
    queryFn: deviceApi.getTioDevices,
  })

  const connectMutation = useMutation({
    mutationFn: (ip: string) => deviceApi.connectTFRack(ip),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tf-rack-status'] })
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: () => deviceApi.disconnectTFRack(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tf-rack-status'] })
    },
  })

  const refreshDanteMutation = useMutation({
    mutationFn: deviceApi.refreshDante,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dante-devices'] })
      queryClient.invalidateQueries({ queryKey: ['tio-devices'] })
    },
  })

  const handleConnect = () => {
    if (tfIpAddress.trim()) {
      connectMutation.mutate(tfIpAddress.trim())
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wifi size={24} />
          Device Management
        </h1>
      </div>

      {/* TF-Rack Connection */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Server size={20} />
            Yamaha TF-Rack
          </h2>
          <div className={clsx(
            'px-3 py-1 rounded text-sm',
            tfStatus?.connected ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
          )}>
            {tfStatus?.connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        {tfStatus?.connected ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">IP Address:</span>
                <span className="ml-2">{tfStatus.ip_address}</span>
              </div>
              <div>
                <span className="text-gray-400">Port:</span>
                <span className="ml-2">{tfStatus.port}</span>
              </div>
              <div>
                <span className="text-gray-400">Sample Rate:</span>
                <span className="ml-2">{tfStatus.sample_rate || 48000} Hz</span>
              </div>
            </div>
            <button
              onClick={() => disconnectMutation.mutate()}
              className="btn btn-danger flex items-center gap-2"
              disabled={disconnectMutation.isPending}
            >
              <PowerOff size={16} />
              Disconnect
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={tfIpAddress}
                onChange={(e) => setTfIpAddress(e.target.value)}
                placeholder="192.168.1.100"
                className="input flex-1"
              />
              <button
                onClick={handleConnect}
                className="btn btn-primary flex items-center gap-2"
                disabled={!tfIpAddress.trim() || connectMutation.isPending}
              >
                <Power size={16} />
                Connect
              </button>
            </div>
            <p className="text-sm text-gray-400">
              Enter the IP address of your TF-Rack. Default port is 49280.
            </p>
          </div>
        )}
      </div>

      {/* Dante Devices */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Radio size={20} />
            Dante Network Devices
          </h2>
          <button
            onClick={() => refreshDanteMutation.mutate()}
            className="btn btn-secondary flex items-center gap-2"
            disabled={refreshDanteMutation.isPending}
          >
            <RefreshCw size={16} className={refreshDanteMutation.isPending ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {danteLoading ? (
          <div className="text-gray-400">Discovering devices...</div>
        ) : danteDevices && danteDevices.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {danteDevices.map((device) => (
              <div
                key={device.name}
                className={clsx(
                  'p-4 rounded-lg border',
                  device.is_online
                    ? 'bg-gray-800 border-green-600'
                    : 'bg-gray-900 border-gray-700'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">{device.name}</span>
                  <div className={clsx(
                    'w-3 h-3 rounded-full',
                    device.is_online ? 'bg-green-500' : 'bg-red-500'
                  )} />
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <div><span className="text-gray-500">Model:</span> {device.model}</div>
                  <div><span className="text-gray-500">IP:</span> {device.ip_address}</div>
                  <div><span className="text-gray-500">Channels:</span> {device.input_channels} in / {device.output_channels} out</div>
                  <div><span className="text-gray-500">Sample Rate:</span> {device.sample_rate} Hz</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-400">
            No Dante devices discovered. Make sure devices are on the same network.
          </div>
        )}
      </div>

      {/* TIO Stage Boxes */}
      {tioDevices && tioDevices.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">TIO Stage Boxes</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tioDevices.map((tio) => (
              <div
                key={tio.name}
                className="p-4 rounded-lg bg-gray-800 border border-blue-600"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-lg">{tio.name}</span>
                  <span className={clsx(
                    'px-2 py-1 rounded text-xs',
                    tio.is_online ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                  )}>
                    {tio.is_online ? 'Online' : 'Offline'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-400">Model:</span>
                    <div>{tio.model}</div>
                  </div>
                  <div>
                    <span className="text-gray-400">IP Address:</span>
                    <div>{tio.ip_address}</div>
                  </div>
                  <div>
                    <span className="text-gray-400">Inputs:</span>
                    <div>{tio.input_channels}</div>
                  </div>
                  <div>
                    <span className="text-gray-400">Outputs:</span>
                    <div>{tio.output_channels}</div>
                  </div>
                </div>

                {/* Input/Output Visual */}
                <div className="mt-4">
                  <div className="text-xs text-gray-400 mb-1">Inputs</div>
                  <div className="flex flex-wrap gap-1">
                    {Array.from({ length: tio.input_channels }, (_, i) => (
                      <div
                        key={i}
                        className="w-6 h-6 bg-gray-700 rounded text-xs flex items-center justify-center"
                      >
                        {i + 1}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Network Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Network Information</h2>
        <div className="text-sm text-gray-400 space-y-2">
          <p>
            Dante devices are discovered using mDNS (Bonjour). Ensure all devices
            are on the same network subnet for automatic discovery.
          </p>
          <p>
            TF-Rack uses OSC protocol on port 49280 for remote control.
          </p>
        </div>
      </div>
    </div>
  )
}
