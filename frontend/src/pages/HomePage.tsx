import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  SlidersHorizontal,
  GitBranch,
  Film,
  Wifi,
  Monitor,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { healthCheck, deviceApi } from '../services/api'
import clsx from 'clsx'

export default function HomePage() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 5000,
  })

  const { data: tfStatus } = useQuery({
    queryKey: ['tf-rack-status'],
    queryFn: deviceApi.getTFRackStatus,
    refetchInterval: 5000,
  })

  const { data: danteDevices } = useQuery({
    queryKey: ['dante-devices'],
    queryFn: deviceApi.getDanteDevices,
    refetchInterval: 10000,
  })

  const quickLinks = [
    { path: '/mixer', label: 'Open Mixer', icon: SlidersHorizontal, color: 'bg-blue-600' },
    { path: '/patch', label: 'Patch Bay', icon: GitBranch, color: 'bg-green-600' },
    { path: '/scenes', label: 'Scenes', icon: Film, color: 'bg-purple-600' },
    { path: '/devices', label: 'Devices', icon: Wifi, color: 'bg-orange-600' },
    { path: '/eink', label: 'E-Ink Labels', icon: Monitor, color: 'bg-cyan-600' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* TF-Rack Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">TF-Rack</h2>
            {health?.tf_rack_connected ? (
              <CheckCircle className="text-green-500" size={24} />
            ) : (
              <XCircle className="text-red-500" size={24} />
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Status</span>
              <span className={health?.tf_rack_connected ? 'text-green-400' : 'text-red-400'}>
                {health?.tf_rack_connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {tfStatus?.ip_address && (
              <div className="flex justify-between">
                <span className="text-gray-400">IP Address</span>
                <span>{tfStatus.ip_address}</span>
              </div>
            )}
            {tfStatus?.port && (
              <div className="flex justify-between">
                <span className="text-gray-400">Port</span>
                <span>{tfStatus.port}</span>
              </div>
            )}
          </div>
        </div>

        {/* Dante Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Dante Network</h2>
            {health?.dante_enabled ? (
              <CheckCircle className="text-green-500" size={24} />
            ) : (
              <AlertCircle className="text-yellow-500" size={24} />
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Discovery</span>
              <span className={health?.dante_enabled ? 'text-green-400' : 'text-yellow-400'}>
                {health?.dante_enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Devices Found</span>
              <span>{danteDevices?.length || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">TIO Boxes</span>
              <span>{danteDevices?.filter(d => d.model.includes('TIO')).length || 0}</span>
            </div>
          </div>
        </div>

        {/* E-Ink Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">E-Ink Displays</h2>
            {health?.eink_enabled ? (
              <CheckCircle className="text-green-500" size={24} />
            ) : (
              <AlertCircle className="text-yellow-500" size={24} />
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Status</span>
              <span className={health?.eink_enabled ? 'text-green-400' : 'text-yellow-400'}>
                {health?.eink_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Connected</span>
              <span>-</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Access</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {quickLinks.map(({ path, label, icon: Icon, color }) => (
            <Link
              key={path}
              to={path}
              className={clsx(
                'card flex flex-col items-center justify-center py-6 hover:scale-105 transition-transform',
                color
              )}
            >
              <Icon size={32} className="mb-2" />
              <span className="font-medium">{label}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Dante Devices */}
      {danteDevices && danteDevices.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Dante Devices</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {danteDevices.map((device) => (
              <div key={device.name} className="card">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{device.name}</span>
                  <div className={clsx(
                    'w-3 h-3 rounded-full',
                    device.is_online ? 'bg-green-500' : 'bg-red-500'
                  )} />
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <div>{device.model} ({device.manufacturer})</div>
                  <div>{device.ip_address}</div>
                  <div>{device.input_channels} in / {device.output_channels} out</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">System Information</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-gray-400">Version</div>
            <div>1.0.0</div>
          </div>
          <div>
            <div className="text-gray-400">API Status</div>
            <div className={healthLoading ? 'text-yellow-400' : 'text-green-400'}>
              {healthLoading ? 'Checking...' : 'Online'}
            </div>
          </div>
          <div>
            <div className="text-gray-400">TF-Rack Model</div>
            <div>TF-RACK</div>
          </div>
          <div>
            <div className="text-gray-400">Sample Rate</div>
            <div>48 kHz</div>
          </div>
        </div>
      </div>
    </div>
  )
}
