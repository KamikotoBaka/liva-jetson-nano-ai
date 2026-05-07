import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'

import './App.css'
import { loadAssistantSettings, pullAssistantSettingsFromBackend } from './settingsStore.js'

function AppLayout() {
  const location = useLocation()
  const [assistantSettings, setAssistantSettings] = useState(() => loadAssistantSettings())
  const activePage = location.pathname === '/settings' ? 'Settings' : 'Dashboard'

  useEffect(() => {
    const syncSettings = () => {
      setAssistantSettings(loadAssistantSettings())
    }

    const syncFromBackend = async () => {
      try {
        const merged = await pullAssistantSettingsFromBackend()
        setAssistantSettings(merged)
      } catch {
        syncSettings()
      }
    }

    syncSettings()
    void syncFromBackend()
    window.addEventListener('focus', syncSettings)
    window.addEventListener('storage', syncSettings)
    window.addEventListener('assistant-settings-changed', syncSettings)

    return () => {
      window.removeEventListener('focus', syncSettings)
      window.removeEventListener('storage', syncSettings)
      window.removeEventListener('assistant-settings-changed', syncSettings)
    }
  }, [])

  useEffect(() => {
    document.body.setAttribute('data-theme', assistantSettings.theme)
  }, [assistantSettings.theme])

  return (
    <div className={`app-shell theme-${assistantSettings.theme}`}>
      <div className="app-container app-shell-inner">
        <header className="card app-nav">
          <div>
            <p className="app-nav-kicker">LIVA</p>
            <h1 className="app-nav-title">Local Intelligent Voice Assistant</h1>
            <p className="app-nav-page">Home / {activePage}</p>
          </div>

          <nav className="app-nav-links" aria-label="Main navigation">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`.trim()}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/settings"
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`.trim()}
            >
              Settings
            </NavLink>
          </nav>
        </header>
      </div>

      <Outlet />
    </div>
  )
}

export default AppLayout