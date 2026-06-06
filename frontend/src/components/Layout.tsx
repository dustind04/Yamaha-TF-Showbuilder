import { useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Home,
  SlidersHorizontal,
  GitBranch,
  Film,
  Wifi,
  Monitor,
  Settings,
  Activity,
  Calendar,
  Users,
  Tv,
  Music
} from 'lucide-react'
import { healthCheck } from '../services/api'
import { useWebSocket } from '../services/websocket'
import clsx from 'clsx'

const navItems = [
  { path: '/', label: 'Home', icon: Home },
  { path: '/mixer', label: 'Mixer', icon: SlidersHorizontal },
  { path: '/patch', label: 'Patch', icon: GitBranch },
  { path: '/scenes', label: 'Scenes', icon: Film },
  { path: '/shows', label: 'Shows', icon: Calendar },
  { path: '/artists', label: 'Artists', icon: Users },
  { path: '/songs', label: 'Songs', icon: Music },
  { path: '/backstage', label: 'Monitor', icon: Tv },
  { path: '/devices', label: 'Devices', icon: Wifi },
  { path: '/eink', label: 'E-Ink', icon: Monitor },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const { connect, connected } = useWebSocket()

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 10000,
  })

  useEffect(() => {
    connect()
  }, [connect])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-mixer-panel border-b border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold text-white">TF Showbuilder</h1>
            <span className="text-sm text-gray-400">Yamaha TF-Rack Control</span>
          </div>

          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <Activity size={16} className={health?.tf_rack_connected ? 'text-green-500' : 'text-red-500'} />
              <span className="text-sm">
                TF-Rack: {health?.tf_rack_connected ? 'Connected' : 'Offline'}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <div className={clsx(
                'w-2 h-2 rounded-full',
                connected ? 'bg-green-500' : 'bg-red-500'
              )} />
              <span className="text-sm text-gray-400">
                {connected ? 'Live' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar Navigation */}
        <nav className="w-16 bg-mixer-panel border-r border-gray-700 flex flex-col items-center py-4 space-y-2">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => clsx(
                'w-12 h-12 flex flex-col items-center justify-center rounded-lg transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              )}
              title={label}
            >
              <Icon size={20} />
              <span className="text-xs mt-1">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-4 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
