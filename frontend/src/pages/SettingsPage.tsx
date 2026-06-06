import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Settings, Save, RefreshCw, Database, Wifi, Monitor } from 'lucide-react'
import { healthCheck } from '../services/api'

export default function SettingsPage() {
  const [tfRackIp, setTfRackIp] = useState('192.168.1.100')
  const [tfRackPort, setTfRackPort] = useState('49280')
  const [danteEnabled, setDanteEnabled] = useState(true)
  const [einkEnabled, setEinkEnabled] = useState(true)
  const [einkRefreshInterval, setEinkRefreshInterval] = useState('300')

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
  })

  const handleSave = () => {
    // In a real app, this would save to the backend
    console.log('Saving settings:', {
      tfRackIp,
      tfRackPort,
      danteEnabled,
      einkEnabled,
      einkRefreshInterval,
    })
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings size={24} />
          Settings
        </h1>
      </div>

      {/* TF-Rack Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Wifi size={20} />
          TF-Rack Connection
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">IP Address</label>
            <input
              type="text"
              value={tfRackIp}
              onChange={(e) => setTfRackIp(e.target.value)}
              className="input"
              placeholder="192.168.1.100"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">OSC Port</label>
            <input
              type="text"
              value={tfRackPort}
              onChange={(e) => setTfRackPort(e.target.value)}
              className="input w-32"
              placeholder="49280"
            />
          </div>
          <p className="text-sm text-gray-400">
            Default OSC port for Yamaha TF series is 49280
          </p>
        </div>
      </div>

      {/* Dante Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Database size={20} />
          Dante Network
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Enable Dante Discovery</div>
              <div className="text-sm text-gray-400">
                Automatically discover Dante devices on the network
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={danteEnabled}
                onChange={(e) => setDanteEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* E-Ink Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Monitor size={20} />
          E-Ink Displays
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Enable E-Ink Displays</div>
              <div className="text-sm text-gray-400">
                Control e-ink labels for physical inputs
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={einkEnabled}
                onChange={(e) => setEinkEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Refresh Interval (seconds)
            </label>
            <input
              type="number"
              value={einkRefreshInterval}
              onChange={(e) => setEinkRefreshInterval(e.target.value)}
              className="input w-32"
              min="60"
              max="3600"
            />
            <p className="text-sm text-gray-400 mt-1">
              How often to refresh e-ink displays (minimum 60 seconds)
            </p>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">System Information</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Application Version</span>
            <span>1.0.0</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">API Status</span>
            <span className={health ? 'text-green-400' : 'text-red-400'}>
              {health ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">TF-Rack Connected</span>
            <span className={health?.tf_rack_connected ? 'text-green-400' : 'text-red-400'}>
              {health?.tf_rack_connected ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Dante Discovery</span>
            <span className={health?.dante_enabled ? 'text-green-400' : 'text-yellow-400'}>
              {health?.dante_enabled ? 'Active' : 'Disabled'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">E-Ink Module</span>
            <span className={health?.eink_enabled ? 'text-green-400' : 'text-yellow-400'}>
              {health?.eink_enabled ? 'Active' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end space-x-2">
        <button className="btn btn-secondary flex items-center gap-2">
          <RefreshCw size={16} />
          Reset to Defaults
        </button>
        <button
          onClick={handleSave}
          className="btn btn-primary flex items-center gap-2"
        >
          <Save size={16} />
          Save Settings
        </button>
      </div>
    </div>
  )
}
