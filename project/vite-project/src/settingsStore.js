export const ASSISTANT_SETTINGS_STORAGE_KEY = 'voice-assistant-ui-settings'
const SETTINGS_API_PATH = '/api/settings'
const SETTINGS_EFFECTIVE_API_PATH = '/api/settings/effective'

export const DEFAULT_ASSISTANT_SETTINGS = {
  theme: 'white',
  speechModel: 'base',
  computeDevice: 'cpu',
  responseMode: 'template',
  voiceVolume: 75,
}

function applyTheme(theme) {
  if (typeof document === 'undefined') {
    return
  }

  const normalizedTheme = theme === 'black' ? 'black' : 'white'
  document.body.setAttribute('data-theme', normalizedTheme)
}

export function loadAssistantSettings() {
  const stored = localStorage.getItem(ASSISTANT_SETTINGS_STORAGE_KEY)
  let merged

  if (!stored) {
    merged = DEFAULT_ASSISTANT_SETTINGS
    applyTheme(merged.theme)
    return merged
  }

  try {
    merged = { ...DEFAULT_ASSISTANT_SETTINGS, ...JSON.parse(stored) }
    applyTheme(merged.theme)
    return merged
  } catch {
    merged = DEFAULT_ASSISTANT_SETTINGS
    applyTheme(merged.theme)
    return merged
  }
}

export function persistAssistantSettings(settings) {
  const merged = { ...DEFAULT_ASSISTANT_SETTINGS, ...settings }
  localStorage.setItem(ASSISTANT_SETTINGS_STORAGE_KEY, JSON.stringify(merged))
  applyTheme(merged.theme)
  window.dispatchEvent(new Event('assistant-settings-changed'))
}

export async function pullAssistantSettingsFromBackend() {
  const response = await fetch(SETTINGS_API_PATH)
  if (!response.ok) {
    throw new Error(`Could not fetch settings: ${response.status}`)
  }

  const backendSettings = await response.json()
  const merged = { ...DEFAULT_ASSISTANT_SETTINGS, ...backendSettings }
  persistAssistantSettings(merged)
  return merged
}

export async function pushAssistantSettingsToBackend(settings) {
  const response = await fetch(SETTINGS_API_PATH, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })

  if (!response.ok) {
    throw new Error(`Could not save settings: ${response.status}`)
  }

  const backendSettings = await response.json()
  const merged = { ...DEFAULT_ASSISTANT_SETTINGS, ...backendSettings }
  persistAssistantSettings(merged)
  return merged
}

export async function pullEffectiveSettingsFromBackend() {
  const response = await fetch(SETTINGS_EFFECTIVE_API_PATH)
  if (!response.ok) {
    throw new Error(`Could not fetch effective settings: ${response.status}`)
  }

  return response.json()
}