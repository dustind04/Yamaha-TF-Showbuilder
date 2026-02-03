import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import MixerPage from './pages/MixerPage'
import PatchPage from './pages/PatchPage'
import ScenesPage from './pages/ScenesPage'
import DevicesPage from './pages/DevicesPage'
import EInkPage from './pages/EInkPage'
import ShowsPage from './pages/ShowsPage'
import ArtistsPage from './pages/ArtistsPage'
import BackstagePage from './pages/BackstagePage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="mixer" element={<MixerPage />} />
          <Route path="patch" element={<PatchPage />} />
          <Route path="scenes" element={<ScenesPage />} />
          <Route path="shows" element={<ShowsPage />} />
          <Route path="artists" element={<ArtistsPage />} />
          <Route path="backstage" element={<BackstagePage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="eink" element={<EInkPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
