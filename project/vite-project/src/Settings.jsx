import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  DEFAULT_ASSISTANT_SETTINGS,
  loadAssistantSettings,
  persistAssistantSettings,
  pullEffectiveSettingsFromBackend,
  pullAssistantSettingsFromBackend,
  pushAssistantSettingsToBackend,
} from './settingsStore.js'

function Settings() {
  const navigate = useNavigate()
  const [draftSettings, setDraftSettings] = useState(() => loadAssistantSettings())
  const [settingsError, setSettingsError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const latestDraftRef = useRef(draftSettings)
  const [effectiveSettings, setEffectiveSettings] = useState(null)
  const [effectiveError, setEffectiveError] = useState('')

  const refreshEffectiveSettings = async () => {
    try {
      const effective = await pullEffectiveSettingsFromBackend()
      setEffectiveSettings(effective)
      setEffectiveError('')
    } catch {
      setEffectiveSettings(null)
      setEffectiveError('Could not load backend runtime status.')
    }
  }

  useEffect(() => {
    const loadSettings = async () => {
      setSettingsError('')
      try {
        const merged = await pullAssistantSettingsFromBackend()
        setDraftSettings(merged)
      } catch {
        setDraftSettings(loadAssistantSettings())
        setSettingsError('Backend settings unavailable. Using local fallback.')
      }

      await refreshEffectiveSettings()
    }

    void loadSettings()
  }, [])

  useEffect(() => {
    latestDraftRef.current = draftSettings
  }, [draftSettings])

  const updateDraftSetting = (key, value) => {
    setDraftSettings((current) => {
      const next = {
        ...current,
        [key]: value,
      }
      latestDraftRef.current = next

      if (key === 'theme' && typeof document !== 'undefined') {
        document.body.setAttribute('data-theme', value === 'black' ? 'black' : 'white')
      }

      return next
    })
  }

  const handleSave = () => {
    const saveSettings = async () => {
      setIsSaving(true)
      setSettingsError('')
      try {
        await pushAssistantSettingsToBackend(latestDraftRef.current)
        await refreshEffectiveSettings()
        navigate('/')
      } catch {
        persistAssistantSettings(latestDraftRef.current)
        setSettingsError('Could not reach backend. Saved locally only.')
      } finally {
        setIsSaving(false)
      }
    }

    void saveSettings()
  }

  const handleReset = () => {
    const resetSettings = async () => {
      setIsSaving(true)
      setSettingsError('')
      try {
        const merged = await pushAssistantSettingsToBackend(DEFAULT_ASSISTANT_SETTINGS)
        setDraftSettings(merged)
        await refreshEffectiveSettings()
      } catch {
        setDraftSettings(DEFAULT_ASSISTANT_SETTINGS)
        persistAssistantSettings(DEFAULT_ASSISTANT_SETTINGS)
        setSettingsError('Could not reach backend. Reset applied locally only.')
      } finally {
        setIsSaving(false)
      }
    }

    void resetSettings()
  }

  return (
    <main className="app-container">
      <div className="settings-route-shell">
        <header className="title-row">
          <div>
            <h1>LIVA Settings</h1>
            <p className="settings-note">Configure appearance, speech recognition, response mode, and voice output for this client.</p>
          </div>
        </header>

        {settingsError && <p className="error-text">{settingsError}</p>}

        <section className="card">
          <h2>Backend runtime status</h2>
          {effectiveError && <p className="error-text">{effectiveError}</p>}
          {effectiveSettings ? (
            <div className="runtime-grid">
              <p className="wake-status">Theme: {effectiveSettings.theme}</p>
              <p className="wake-status">Response mode: {effectiveSettings.responseMode}</p>
              <p className="wake-status">Configured STT: {effectiveSettings.speechModel} on {effectiveSettings.computeDevice}</p>
              <p className="wake-status">Active STT: {effectiveSettings.activeSttModel} on {effectiveSettings.activeSttDevice}</p>
              <p className="wake-status">Voice volume: {effectiveSettings.voiceVolume}</p>
            </div>
          ) : (
            !effectiveError && <p className="wake-status">Loading backend runtime status...</p>
          )}
        </section>

        <section className="card settings-panel">
          <div className="settings-header">
            <div>
              <h2>Website UI Settings</h2>
              <p className="settings-note">These values are stored in the backend settings service.</p>
            </div>
            <p className="settings-summary">
              {draftSettings.speechModel} on {draftSettings.computeDevice.toUpperCase()} • {draftSettings.responseMode === 'template' ? 'Template mode' : 'LLM mode'} • Vol {draftSettings.voiceVolume}
            </p>
          </div>

          <div className="settings-grid">
            <div className="settings-block">
              <p className="settings-block-title">Appearance</p>
              <div className="response-mode-grid">
                <button
                  type="button"
                  className={`mode-card ${draftSettings.theme === 'white' ? 'mode-card-active' : 'secondary-button'}`}
                  onClick={() => updateDraftSetting('theme', 'white')}
                >
                  <span className="mode-card-title">White mode</span>
                  <span className="mode-card-copy">Bright workspace for high-contrast daylight use.</span>
                </button>

                <button
                  type="button"
                  className={`mode-card ${draftSettings.theme === 'black' ? 'mode-card-active' : 'secondary-button'}`}
                  onClick={() => updateDraftSetting('theme', 'black')}
                >
                  <span className="mode-card-title">Black mode</span>
                  <span className="mode-card-copy">Low-glare workspace for darker rooms and focused sessions.</span>
                </button>
              </div>
            </div>

            <div className="settings-block">
              <p className="settings-block-title">Speech recognition</p>
              <div className="field">
                <label htmlFor="speech-model">Model</label>
                <select
                  id="speech-model"
                  value={draftSettings.speechModel}
                  onChange={(event) => updateDraftSetting('speechModel', event.target.value)}
                >
                  <option value="tiny">Tiny</option>
                  <option value="base">Base</option>
                  <option value="medium">Medium</option>
                </select>
              </div>

              <div className="field">
                <label htmlFor="compute-device">Device</label>
                <select
                  id="compute-device"
                  value={draftSettings.computeDevice}
                  onChange={(event) => updateDraftSetting('computeDevice', event.target.value)}
                >
                  <option value="cpu">CPU</option>
                  <option value="cuda">CUDA</option>
                </select>
              </div>
            </div>

            <div className="settings-block">
              <p className="settings-block-title">Response mode</p>
              <div className="response-mode-grid">
                <button
                  type="button"
                  className={`mode-card ${draftSettings.responseMode === 'template' ? 'mode-card-active' : 'secondary-button'}`}
                  onClick={() => updateDraftSetting('responseMode', 'template')}
                >
                  <span className="mode-card-title">Template</span>
                  <span className="mode-card-copy">Shell-oriented replies for Raspberry class devices.</span>
                </button>

                <button
                  type="button"
                  className={`mode-card ${draftSettings.responseMode === 'llm' ? 'mode-card-active' : 'secondary-button'}`}
                  onClick={() => updateDraftSetting('responseMode', 'llm')}
                >
                  <span className="mode-card-title">LLM</span>
                  <span className="mode-card-copy">More intelligent responses for Jetson class hardware.</span>
                </button>
              </div>
            </div>
          </div>

          <div className="settings-block settings-block-full">
            <p className="settings-block-title">Voice output</p>
            <div className="field">
              <label htmlFor="voice-volume">Volume: {draftSettings.voiceVolume}</label>
              <input
                id="voice-volume"
                type="range"
                min="0"
                max="100"
                step="1"
                value={draftSettings.voiceVolume}
                onChange={(event) => updateDraftSetting('voiceVolume', Number(event.target.value))}
              />
            </div>
          </div>

          <div className="settings-actions">
            <button type="button" onClick={handleSave} disabled={isSaving}>{isSaving ? 'Saving...' : 'Save settings'}</button>
            <button type="button" className="secondary-button" onClick={handleReset} disabled={isSaving}>Reset</button>
          </div>
        </section>
      </div>
    </main>
  )
}

export default Settings