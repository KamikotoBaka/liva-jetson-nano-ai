import { useEffect, useRef, useState } from 'react'
import AIChat from './components/AIChat.jsx'
import CustomCommands from './components/CustomCommands.jsx'
import ErrorEvents from './components/error_events.jsx'
import VoiceCommands from './components/VoiceCommands.jsx'

import { loadAssistantSettings } from './settingsStore.js'

const COMMANDS_STORAGE_KEY = 'voice-assistant-saved-commands'
const CATEGORIES_STORAGE_KEY = 'voice-assistant-command-categories'
const WAKE_WORD = 'liva'
const DEFAULT_CATEGORIES = ['General']
const DEFAULT_RECORDING_PROFILE = {
  silenceMs: 900,
  maxMs: 7000,
  vadThreshold: 0.03,
  intervalMs: 120,
  minRecordingMs: 1400,
}
const FAST_NO_AUTH_RECORDING_PROFILE = {
  silenceMs: 420,
  maxMs: 3500,
  vadThreshold: 0.02,
  intervalMs: 70,
  minRecordingMs: 900,
}
const CHAT_TAP_RECORD_PROFILE = {
  silenceMs: 60000,
  maxMs: 120000,
  vadThreshold: 0.02,
  intervalMs: 100,
  minRecordingMs: 300,
}
const AUTH_SESSION_SAFETY_MS = 1500
const DEFAULT_COMMANDS = [
  {
    trigger: 'Identify error',
    category: 'General',
    actionType: 'REST',
    actionTarget: '/api/devices/status',
    responseTemplate: 'Device {device_name} reports: {status}',
  },
]

const SYSTEM_VOICE_COMMANDS = [
  { phrase: 'Good Morning', action: 'Greeting + time + recent error summary' },
  { phrase: 'Identify error', action: 'REST+MQTT status check' },
  { phrase: 'Open Spotify', action: 'Launch Spotify app' },
  { phrase: 'Open Outlook', action: 'Launch Outlook Classic' },
  { phrase: 'Open Teams', action: 'Launch Teams app' },
  { phrase: 'Check time', action: 'Read current system time' },
  { phrase: 'Check date', action: 'Read current system date' },
  { phrase: 'Show me the last 5 errors', action: 'SQLite recent error query' },
  { phrase: 'What happened today?', action: 'SQLite daily summary query' },
  { phrase: 'How many commands were executed today?', action: 'SQLite command counter' },
  { phrase: 'Download the Datalog', action: 'Download CSV error log export' },
  { phrase: 'Wake word: LIVA', action: 'Hands-free command activation' },
]

const DASHBOARD_PANELS = [
  { id: 'type', label: 'Type Command' },
  { id: 'voice', label: 'Voice Commands' },
  { id: 'custom', label: 'Custom Commands' },
  { id: 'errors', label: 'Error Events' },
  { id: 'chat', label: 'AI Chat' },
]

const normalizePhrase = (value) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[.,!?;:]+$/g, '')
    .replace(/\s+/g, ' ')

const normalizeSavedCommand = (item) => {
  const legacyAction = typeof item?.action === 'string' ? item.action : ''
  return {
    trigger: typeof item?.trigger === 'string' ? item.trigger : '',
    category: typeof item?.category === 'string' && item.category.trim() ? item.category.trim() : 'General',
    actionType: item?.actionType === 'MQTT' ? 'MQTT' : 'REST',
    actionTarget:
      typeof item?.actionTarget === 'string'
        ? item.actionTarget
        : legacyAction,
    responseTemplate:
      typeof item?.responseTemplate === 'string'
        ? item.responseTemplate
        : 'Device {device_name} reports: {status}',
  }
}

function App() {
  const [activePanel, setActivePanel] = useState('type')
  const [assistantSettings, setAssistantSettings] = useState(() => loadAssistantSettings())
  const [typedCommand, setTypedCommand] = useState('')
  const [newCategoryName, setNewCategoryName] = useState('')
  const [categories, setCategories] = useState(() => {
    const stored = localStorage.getItem(CATEGORIES_STORAGE_KEY)
    if (!stored) {
      return DEFAULT_CATEGORIES
    }

    try {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return Array.from(new Set(parsed.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())))
      }
      return DEFAULT_CATEGORIES
    } catch {
      return DEFAULT_CATEGORIES
    }
  })
  const [selectedCategory, setSelectedCategory] = useState('General')
  const [newTrigger, setNewTrigger] = useState('')
  const [newActionType, setNewActionType] = useState('REST')
  const [newActionTarget, setNewActionTarget] = useState('')
  const [newResponseTemplate, setNewResponseTemplate] = useState('Device {device_name} reports: {status}')
  const [savedCommands, setSavedCommands] = useState(() => {
    const stored = localStorage.getItem(COMMANDS_STORAGE_KEY)
    if (!stored) {
      return DEFAULT_COMMANDS
    }

    try {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed)) {
        return parsed.map(normalizeSavedCommand)
      }
      return DEFAULT_COMMANDS
    } catch {
      return DEFAULT_COMMANDS
    }
  })
  const [sttText, setSttText] = useState('')
  const [commandText, setCommandText] = useState('')
  const [ttsText, setTtsText] = useState('')
  const [intent, setIntent] = useState('')
  const [speakerInfo, setSpeakerInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isRecordingAudio, setIsRecordingAudio] = useState(false)
  const [isWakeModeEnabled, setIsWakeModeEnabled] = useState(false)
  const [wakewordBackendAvailable, setWakewordBackendAvailable] = useState(false)
  const [wakewordBackendReason, setWakewordBackendReason] = useState('')
  const [wakeStatus, setWakeStatus] = useState('Wake mode is off')
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [error, setError] = useState('')
  const [errorEvents, setErrorEvents] = useState([])
  const wakeModeRef = useRef(false)
  const wakeRecognitionRef = useRef(null)
  const commandRecognitionRef = useRef(null)
  const commandMediaRecorderRef = useRef(null)
  const commandMediaStreamRef = useRef(null)
  const commandChunksRef = useRef([])
  const commandAudioContextRef = useRef(null)
  const commandAudioSourceRef = useRef(null)
  const commandAnalyserRef = useRef(null)
  const commandSilenceTimerRef = useRef(null)
  const commandMaxTimerRef = useRef(null)
  const commandVoiceDetectedRef = useRef(false)
  const wakeAudioContextRef = useRef(null)
  const wakeMediaStreamRef = useRef(null)
  const wakeProcessorRef = useRef(null)
  const wakeSourceRef = useRef(null)
  const wakeBusyRef = useRef(false)
  const customCommandsSyncedRef = useRef(false)

  const normalizeBackendCommand = (item) => {
    if (!item || typeof item !== 'object') {
      return null
    }

    const normalized = normalizeSavedCommand(item)
    if (!normalized.trigger || !normalized.actionTarget) {
      return null
    }

    return normalized
  }

  const saveCustomCommandsToBackend = async (commands) => {
    await fetch('/api/custom-commands', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(commands),
    })
  }

  useEffect(() => {
    localStorage.setItem(COMMANDS_STORAGE_KEY, JSON.stringify(savedCommands))

    if (!customCommandsSyncedRef.current) {
      return
    }

    void saveCustomCommandsToBackend(savedCommands)
  }, [savedCommands])

  useEffect(() => {
    let cancelled = false

    const syncFromBackend = async () => {
      try {
        const response = await fetch('/api/custom-commands')
        if (!response.ok) {
          customCommandsSyncedRef.current = true
          return
        }

        const backendCommands = await response.json()
        if (!Array.isArray(backendCommands)) {
          customCommandsSyncedRef.current = true
          return
        }

        const normalized = backendCommands.map(normalizeBackendCommand).filter(Boolean)

        if (cancelled) {
          return
        }

        if (normalized.length > 0) {
          setSavedCommands(normalized)
          customCommandsSyncedRef.current = true
          return
        }

        await saveCustomCommandsToBackend(savedCommands)
      } catch {
        // Keep local mode functional even if backend sync is temporarily unavailable.
      } finally {
        customCommandsSyncedRef.current = true
      }
    }

    void syncFromBackend()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const normalized = categories.length > 0 ? categories : DEFAULT_CATEGORIES
    localStorage.setItem(CATEGORIES_STORAGE_KEY, JSON.stringify(normalized))
    if (!normalized.includes(selectedCategory)) {
      setSelectedCategory(normalized[0])
    }
  }, [categories, selectedCategory])

  useEffect(() => {
    const syncSettings = () => {
      setAssistantSettings(loadAssistantSettings())
    }

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
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }

      if (wakeRecognitionRef.current) {
        wakeRecognitionRef.current.stop()
      }

      if (commandRecognitionRef.current) {
        commandRecognitionRef.current.stop()
      }

      stopCommandAudioRecording()

      stopWakeAudioListener()
    }
  }, [])

  useEffect(() => {
    wakeModeRef.current = isWakeModeEnabled
  }, [isWakeModeEnabled])

  useEffect(() => {
    void fetchErrorEvents()
    void fetchWakewordStatus()
  }, [])

  const fetchWakewordStatus = async () => {
    try {
      const response = await fetch('/api/wakeword/status')
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }

      const data = await response.json()
      setWakewordBackendAvailable(Boolean(data.available))
      setWakewordBackendReason(data.reason || '')
    } catch {
      setWakewordBackendAvailable(false)
      setWakewordBackendReason('Wakeword backend unavailable')
    }
  }

  const fetchErrorEvents = async () => {
    try {
      const response = await fetch('/api/errors')
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }
      const events = await response.json()
      setErrorEvents(Array.isArray(events) ? events : [])
    } catch {
      setErrorEvents([])
    }
  }

  const deleteErrorEvent = async (eventId) => {
    try {
      const response = await fetch(`/api/errors/${eventId}`, { method: 'DELETE' })
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }
      setErrorEvents((current) => current.filter((item) => item.id !== eventId))
    } catch {
      setError('Could not delete error event.')
    }
  }

  const downloadLogs = async () => {
    try {
      const response = await fetch('/api/errors/export')
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }

      const blob = await response.blob()
      const fileUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = fileUrl
      link.download = `error_events_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(fileUrl)
      return true
    } catch {
      setError('Could not download logs.')
      return false
    }
  }

  const addCommand = () => {
    const trigger = newTrigger.trim()
    const category = selectedCategory.trim()
    const actionTarget = newActionTarget.trim()
    const responseTemplate = newResponseTemplate.trim()

    if (!trigger || !category || !actionTarget || !responseTemplate) {
      setError('Please fill command phrase, action command, and response template.')
      return
    }

    const exists = savedCommands.some((item) => normalizePhrase(item.trigger) === normalizePhrase(trigger))
    const collidesWithSystem = SYSTEM_VOICE_COMMANDS.some(
      (item) => normalizePhrase(item.phrase) === normalizePhrase(trigger),
    )
    if (exists) {
      setError('This command phrase already exists.')
      return
    }
    if (collidesWithSystem) {
      setError('This phrase is reserved by a system command.')
      return
    }

    setSavedCommands((current) => [
      ...current,
      {
        trigger,
        category,
        actionType: newActionType,
        actionTarget,
        responseTemplate,
      },
    ])
    setNewTrigger('')
    setNewActionType('REST')
    setNewActionTarget('')
    setNewResponseTemplate('Device {device_name} reports: {status}')
    setError('')
  }

  const addCategory = () => {
    const trimmed = newCategoryName.trim()
    if (!trimmed) {
      setError('Please enter a category name.')
      return
    }

    const exists = categories.some((item) => item.toLowerCase() === trimmed.toLowerCase())
    if (exists) {
      setError('This category already exists.')
      return
    }

    const updated = [...categories, trimmed]
    setCategories(updated)
    setSelectedCategory(trimmed)
    setNewCategoryName('')
    setError('')
  }

  const deleteCommand = (trigger) => {
    setSavedCommands((current) => current.filter((item) => item.trigger !== trigger))
  }

  const importCommands = (imported) => {
    const normalized = (text) => text.toLowerCase().trim().replace(/\s+/g, ' ')
    const existingTriggers = new Set(savedCommands.map((cmd) => normalized(cmd.trigger)))

    const newCommands = imported.filter((cmd) => {
      const trigger = cmd.trigger || ''
      return trigger.trim() && !existingTriggers.has(normalized(trigger))
    })

    if (newCommands.length === 0) {
      alert('No new commands to import (all commands already exist).')
      return
    }

    setSavedCommands((current) => [...current, ...newCommands])
    alert(`Successfully imported ${newCommands.length} command(s)!`)
  }

  const speakText = (text) => {
    const trimmed = text.trim()
    if (!trimmed) {
      return
    }

    if (!window.speechSynthesis) {
      setError('Audio speech is not supported in this browser.')
      return
    }

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(trimmed)
    utterance.lang = 'en-US'
    utterance.rate = 1
    utterance.volume = Math.max(0, Math.min(1, assistantSettings.voiceVolume / 100))
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }

  const stopSpeaking = () => {
    if (!window.speechSynthesis) {
      return
    }
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }

  const getSpeechRecognitionCtor = () => window.SpeechRecognition || window.webkitSpeechRecognition

  const stopCommandListener = () => {
    if (commandRecognitionRef.current) {
      commandRecognitionRef.current.onresult = null
      commandRecognitionRef.current.onerror = null
      commandRecognitionRef.current.onend = null
      commandRecognitionRef.current.stop()
      commandRecognitionRef.current = null
    }
    setIsListening(false)
  }

  const stopWakeListener = () => {
    if (wakeRecognitionRef.current) {
      wakeRecognitionRef.current.onresult = null
      wakeRecognitionRef.current.onerror = null
      wakeRecognitionRef.current.onend = null
      wakeRecognitionRef.current.stop()
      wakeRecognitionRef.current = null
    }
  }

  const stopWakeAudioListener = () => {
    if (wakeProcessorRef.current) {
      wakeProcessorRef.current.onaudioprocess = null
      wakeProcessorRef.current.disconnect()
      wakeProcessorRef.current = null
    }

    if (wakeSourceRef.current) {
      wakeSourceRef.current.disconnect()
      wakeSourceRef.current = null
    }

    if (wakeMediaStreamRef.current) {
      wakeMediaStreamRef.current.getTracks().forEach((track) => track.stop())
      wakeMediaStreamRef.current = null
    }

    if (wakeAudioContextRef.current) {
      void wakeAudioContextRef.current.close()
      wakeAudioContextRef.current = null
    }

    wakeBusyRef.current = false
  }

  const stopCommandAudioRecording = () => {
    const recorder = commandMediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }

    if (commandSilenceTimerRef.current) {
      window.clearInterval(commandSilenceTimerRef.current)
      commandSilenceTimerRef.current = null
    }

    if (commandMaxTimerRef.current) {
      window.clearTimeout(commandMaxTimerRef.current)
      commandMaxTimerRef.current = null
    }

    if (commandAudioSourceRef.current) {
      commandAudioSourceRef.current.disconnect()
      commandAudioSourceRef.current = null
    }

    if (commandAnalyserRef.current) {
      commandAnalyserRef.current.disconnect()
      commandAnalyserRef.current = null
    }

    if (commandAudioContextRef.current) {
      void commandAudioContextRef.current.close()
      commandAudioContextRef.current = null
    }

    commandVoiceDetectedRef.current = false

    if (commandMediaStreamRef.current) {
      commandMediaStreamRef.current.getTracks().forEach((track) => track.stop())
      commandMediaStreamRef.current = null
    }

    commandMediaRecorderRef.current = null
    commandChunksRef.current = []
    setIsRecordingAudio(false)
    setIsListening(false)
  }

  const sendChatTurn = async (text) => {
    const response = await fetch('/api/chat/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`)
    }

    return response.json()
  }

  const processCommand = async (inputText) => {
    const trimmedInput = inputText.trim()
    if (!trimmedInput) {
      setError('Please type a voice command first.')
      return
    }

    setLoading(true)
    setError('')
    setSpeakerInfo(null)

    try {
      const data = await sendChatTurn(trimmedInput)
      setSttText(data.sttText ?? '')
      setCommandText(data.commandText ?? '')
      setTtsText(data.ttsText ?? '')
      speakText(data.ttsText ?? '')
      setIntent(data.intent ?? '')

      if (data.intent === 'identify_error') {
        void fetchErrorEvents()
      }

      if (data.intent === 'download_logs') {
        await downloadLogs()
      }
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to process command.')
      setSttText('')
      setCommandText('')
      setTtsText('')
      setIntent('')
    } finally {
      setLoading(false)
    }
  }

  const sendAIChatMessage = async (chatText) => {
    setLoading(true)
    setError('')

    try {
      const data = await sendChatTurn(chatText)
      setSttText(data.sttText ?? '')
      setCommandText(data.commandText ?? '')
      setTtsText(data.ttsText ?? '')
      setIntent(data.intent ?? '')
      return data
    } finally {
      setLoading(false)
    }
  }

  const sendAIChatAudio = async (audioBlob) => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'chat.webm')

    const sttResponse = await fetch('/api/process-audio', {
      method: 'POST',
      body: formData,
    })

    if (!sttResponse.ok) {
      const payload = await sttResponse.json().catch(() => ({}))
      throw new Error(payload.detail || `Request failed ${sttResponse.status}`)
    }

    const sttPayload = await sttResponse.json()
    const transcript = (sttPayload.sttText || '').trim()
    if (!transcript) {
      throw new Error('No speech detected in chat audio.')
    }

    return sendAIChatMessage(transcript)
  }

  const toggleAIChatMicrophone = async () => {
    if (isRecordingAudio) {
      stopCommandAudioRecording()
      return null
    }

    return new Promise((resolve, reject) => {
      const onAudioReady = async (audioBlob) => {
        try {
          const result = await sendAIChatAudio(audioBlob)
          resolve(result)
        } catch (error) {
          reject(error)
        }
      }

      void startCommandAudioRecording(onAudioReady, CHAT_TAP_RECORD_PROFILE).catch((error) => {
        reject(error)
      })
    })
  }

  const runPipeline = async () => {
    await processCommand(typedCommand)
  }

  const [authToken, setAuthToken] = useState(null)
  const [authExpiry, setAuthExpiry] = useState(null)
  const [authSpeaker, setAuthSpeaker] = useState(null)

  const clearAuthSession = () => {
    setAuthToken(null)
    setAuthExpiry(null)
    setAuthSpeaker(null)
  }

  const isAuthSessionFresh = () => {
    if (!authToken || !authExpiry) {
      return false
    }

    return Date.now() < authExpiry - AUTH_SESSION_SAFETY_MS
  }

  const ensureValidAuthSession = () => {
    if (isAuthSessionFresh()) {
      return true
    }

    if (authToken || authExpiry || authSpeaker) {
      clearAuthSession()
    }
    return false
  }

  const rememberAuthSession = (data) => {
    const token = typeof data?.authToken === 'string' ? data.authToken : ''
    const expiresInSeconds = Number(data?.expiresInSeconds ?? 0)

    if (!token || !Number.isFinite(expiresInSeconds) || expiresInSeconds <= 0) {
      return
    }

    setAuthToken(token)
    setAuthExpiry(Date.now() + expiresInSeconds * 1000)
    setAuthSpeaker({
      name: data.speakerName ?? 'Unknown',
      role: data.speakerRole ?? 'guest',
    })
  }

  const processAudioCommand = async (audioBlob) => {
  setLoading(true)
  setError('')
  setSpeakerInfo(null)

  try {
    let audioRes
    let usedCachedSession = false

    if (ensureValidAuthSession()) {
      const sessionFormData = new FormData()
      sessionFormData.append('audio', audioBlob, 'command.webm')
      sessionFormData.append('authToken', authToken)

      audioRes = await fetch('/api/process-audio-session', {
        method: 'POST',
        body: sessionFormData,
      })

      if (audioRes.ok) {
        usedCachedSession = true
      } else if (audioRes.status === 401) {
        clearAuthSession()
        audioRes = undefined
      }
    }

    if (!audioRes) {
      const secureFormData = new FormData()
      secureFormData.append('audio', audioBlob, 'command.webm')
      audioRes = await fetch('/api/process-audio-secure', {
        method: 'POST',
        body: secureFormData,
      })
    }

    if (!audioRes.ok) {
      const payload = await audioRes.json().catch(() => ({}))
      throw new Error(payload.detail || `Request failed ${audioRes.status}`)
    }

    const data = await audioRes.json()
    rememberAuthSession(data)

    setTypedCommand(data.sttText ?? '')
    setSttText(data.sttText ?? '')
    setCommandText(data.commandText ?? '')
    setTtsText(data.ttsText ?? '')
    setIntent(data.intent ?? '')
    setSpeakerInfo({
      name: data.speakerName ?? 'Unknown',
      role: data.speakerRole ?? 'guest',
      confidence: data.speakerConfidence ?? 0,
      accessGranted: Boolean(data.accessGranted),
      denialReason: usedCachedSession
        ? 'Authenticated via cached secure session.'
        : (data.denialReason ?? ''),
    })
    speakText(data.ttsText ?? '')

    if (!data.accessGranted) {
      setError(data.denialReason || 'Access denied.')
      return
    }

    if (data.intent === 'identify_error') {
      void fetchErrorEvents()
    }

    if (data.intent === 'download_logs') {
      await downloadLogs()
    }

  } catch (fetchError) {
    setError(fetchError.message || 'Failed to process audio command.')
    setSttText('')
    setCommandText('')
    setTtsText('')
    setIntent('')
  } finally {
    setLoading(false)
  }
  }

  const processAudioCommandWithoutAuth = async (audioBlob) => {
    setLoading(true)
    setError('')
    setSpeakerInfo(null)

    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'command.webm')

      const response = await fetch('/api/process-audio', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail || `Request failed ${response.status}`)
      }

      const data = await response.json()
      setTypedCommand(data.sttText ?? '')
      setSttText(data.sttText ?? '')
      setCommandText(data.commandText ?? '')
      setTtsText(data.ttsText ?? '')
      setIntent(data.intent ?? '')
      speakText(data.ttsText ?? '')

      if (data.intent === 'identify_error') {
        void fetchErrorEvents()
      }

      if (data.intent === 'download_logs') {
        await downloadLogs()
      }
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to process audio command.')
      setSttText('')
      setCommandText('')
      setTtsText('')
      setIntent('')
    } finally {
      setLoading(false)
    }
  }

  const startCommandAudioRecording = async (
    onAudioReady = processAudioCommand,
    profile = DEFAULT_RECORDING_PROFILE,
  ) => {
    if (isRecordingAudio) {
      return
    }

    if (!window.MediaRecorder) {
      setError('Audio recording is not supported in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContextCtor()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      const audioData = new Uint8Array(analyser.fftSize)
      const recordingStartedAt = Date.now()
      let silenceStartedAt = null

      commandMediaStreamRef.current = stream
      commandMediaRecorderRef.current = mediaRecorder
      commandChunksRef.current = []
      commandAudioContextRef.current = audioContext
      commandAudioSourceRef.current = source
      commandAnalyserRef.current = analyser
      commandVoiceDetectedRef.current = false
      setError('')
      setIsRecordingAudio(true)
      setIsListening(true)

      source.connect(analyser)

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          commandChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onerror = () => {
        setError('Microphone recording failed. Please try again.')
        stopCommandAudioRecording()
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(commandChunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm',
        })

        if (commandSilenceTimerRef.current) {
          window.clearInterval(commandSilenceTimerRef.current)
          commandSilenceTimerRef.current = null
        }

        if (commandMaxTimerRef.current) {
          window.clearTimeout(commandMaxTimerRef.current)
          commandMaxTimerRef.current = null
        }

        if (commandAudioSourceRef.current) {
          commandAudioSourceRef.current.disconnect()
          commandAudioSourceRef.current = null
        }

        if (commandAnalyserRef.current) {
          commandAnalyserRef.current.disconnect()
          commandAnalyserRef.current = null
        }

        if (commandAudioContextRef.current) {
          void commandAudioContextRef.current.close()
          commandAudioContextRef.current = null
        }

        commandVoiceDetectedRef.current = false

        if (commandMediaStreamRef.current) {
          commandMediaStreamRef.current.getTracks().forEach((track) => track.stop())
          commandMediaStreamRef.current = null
        }

        commandMediaRecorderRef.current = null
        commandChunksRef.current = []
        setIsRecordingAudio(false)
        setIsListening(false)

        if (audioBlob.size > 0) {
          await onAudioReady(audioBlob)
        } else {
          setError('No speech captured. Please try again.')
        }
      }

      mediaRecorder.start()

      commandSilenceTimerRef.current = window.setInterval(() => {
        if (!commandAnalyserRef.current || !commandMediaRecorderRef.current) {
          return
        }

        if (Date.now() - recordingStartedAt < profile.minRecordingMs) {
          return
        }

        commandAnalyserRef.current.getByteTimeDomainData(audioData)
        let sum = 0
        for (let index = 0; index < audioData.length; index += 1) {
          const centered = (audioData[index] - 128) / 128
          sum += centered * centered
        }

        const rms = Math.sqrt(sum / audioData.length)
        const isSpeech = rms > profile.vadThreshold

        if (isSpeech) {
          commandVoiceDetectedRef.current = true
          silenceStartedAt = null
          return
        }

        if (!commandVoiceDetectedRef.current) {
          return
        }

        if (silenceStartedAt === null) {
          silenceStartedAt = Date.now()
          return
        }

        if (Date.now() - silenceStartedAt >= profile.silenceMs && commandMediaRecorderRef.current.state !== 'inactive') {
          commandMediaRecorderRef.current.stop()
        }
      }, profile.intervalMs)

      commandMaxTimerRef.current = window.setTimeout(() => {
        if (commandMediaRecorderRef.current && commandMediaRecorderRef.current.state !== 'inactive') {
          commandMediaRecorderRef.current.stop()
        }
      }, profile.maxMs)
    } catch {
      setError('Microphone access is required for backend STT recording.')
      stopCommandAudioRecording()
    }
  }

  const listenForCommand = (restartWakeAfter = false) => {
    const SpeechRecognition = getSpeechRecognitionCtor()
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser.')
      return
    }

    if (commandRecognitionRef.current) {
      stopCommandListener()
    }

    const recognition = new SpeechRecognition()
    commandRecognitionRef.current = recognition
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    setError('')
    setIsListening(true)

    recognition.onresult = async (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim() ?? ''
      setTypedCommand(transcript)
      await processCommand(transcript)
    }

    recognition.onerror = () => {
      setError('Microphone recognition failed. Please try again.')
    }

    recognition.onend = () => {
      commandRecognitionRef.current = null
      setIsListening(false)
      if (restartWakeAfter && wakeModeRef.current) {
        setWakeStatus(`Listening for wake word: ${WAKE_WORD.toUpperCase()}`)
        void startWakeModeListener()
      }
    }

    recognition.start()
  }

  const startWakeListener = () => {
    const SpeechRecognition = getSpeechRecognitionCtor()
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser.')
      setIsWakeModeEnabled(false)
      setWakeStatus('Wake mode unavailable in this browser')
      return
    }

    if (wakeRecognitionRef.current || isListening) {
      return
    }

    const recognition = new SpeechRecognition()
    wakeRecognitionRef.current = recognition
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    setWakeStatus(`Listening for wake word: ${WAKE_WORD.toUpperCase()}`)

    recognition.onresult = (event) => {
      const transcript = event.results?.[event.results.length - 1]?.[0]?.transcript ?? ''
      const normalizedTranscript = normalizePhrase(transcript)

      if (!normalizedTranscript.includes(WAKE_WORD)) {
        return
      }

      setWakeStatus('Wake word detected. Listening for command...')
      stopWakeListener()
      listenForCommand(true)
    }

    recognition.onerror = () => {
      if (wakeModeRef.current) {
        setWakeStatus('Wake listener error. Restarting...')
      }
    }

    recognition.onend = () => {
      wakeRecognitionRef.current = null
      if (wakeModeRef.current && !isListening) {
        startWakeListener()
      }
    }

    recognition.start()
  }

  const startWakeAudioListener = async () => {
    if (isListening || wakeProcessorRef.current) {
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContextCtor()
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(2048, 1, 1)
      const gain = audioContext.createGain()
      gain.gain.value = 0

      wakeMediaStreamRef.current = stream
      wakeAudioContextRef.current = audioContext
      wakeSourceRef.current = source
      wakeProcessorRef.current = processor

      source.connect(processor)
      processor.connect(gain)
      gain.connect(audioContext.destination)

      setWakeStatus(`Listening for wake word: ${WAKE_WORD.toUpperCase()} (openWakeWord)`)

      processor.onaudioprocess = async (event) => {
        if (!wakeModeRef.current || isListening || wakeBusyRef.current) {
          return
        }

        wakeBusyRef.current = true
        const samples = Array.from(event.inputBuffer.getChannelData(0))

        try {
          const response = await fetch('/api/wakeword/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              samples,
              sampleRate: audioContext.sampleRate,
            }),
          })

          if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`)
          }

          const data = await response.json()
          if (data.detected) {
            setWakeStatus('Wake word detected. Listening for command...')
            stopWakeAudioListener()
            listenForCommand(true)
          }
        } catch {
          setWakeStatus('openWakeWord detection error. Falling back to speech wake mode.')
          stopWakeAudioListener()
          startWakeListener()
        } finally {
          wakeBusyRef.current = false
        }
      }
    } catch {
      setWakeStatus('Microphone access denied for wake mode.')
      setError('Microphone access is required for wake word mode.')
    }
  }

  const startWakeModeListener = async () => {
    if (wakewordBackendAvailable) {
      await startWakeAudioListener()
      return
    }

    startWakeListener()
  }

  const toggleWakeMode = () => {
    if (isWakeModeEnabled) {
      setIsWakeModeEnabled(false)
      wakeModeRef.current = false
      stopWakeListener()
      stopWakeAudioListener()
      setWakeStatus('Wake mode is off')
      return
    }

    setError('')
    setIsWakeModeEnabled(true)
    wakeModeRef.current = true
    void startWakeModeListener()
  }

  const listenFromMicrophone = () => {
    stopWakeListener()
    stopWakeAudioListener()

    if (isRecordingAudio) {
      stopCommandAudioRecording()
      return
    }

    void startCommandAudioRecording(processAudioCommand)
  }

  const listenFromMicrophoneWithoutAuth = () => {
    stopWakeListener()
    stopWakeAudioListener()

    if (isRecordingAudio) {
      stopCommandAudioRecording()
      return
    }

    void startCommandAudioRecording(processAudioCommandWithoutAuth, FAST_NO_AUTH_RECORDING_PROFILE)
  }

  const isNoAuthRecognitionActive = Boolean(commandRecognitionRef.current) && isListening && !isRecordingAudio
  const authSessionSecondsLeft = authExpiry ? Math.max(0, Math.floor((authExpiry - Date.now()) / 1000)) : 0

  return (
    <main className="app-container">
      <div className="content-column">
        <header className="title-row">
          <div>
            <h1>Voice Assistant Control Panel</h1>
            <p className="settings-note">Backend-first orchestration with routed AI chat and modular UI panels.</p>
          </div>
        </header>

        <section className="card">
          <div className="dashboard-menu-bar" role="tablist" aria-label="Dashboard panels">
            {DASHBOARD_PANELS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`menu-button ${activePanel === item.id ? 'menu-button-active' : 'secondary-button'}`}
                onClick={() => setActivePanel(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </section>

        {activePanel === 'type' && (
          <section className="card">
        <label htmlFor="typed-command">Type voice command</label>
        <textarea
          id="typed-command"
          value={typedCommand}
          onChange={(event) => setTypedCommand(event.target.value)}
          placeholder='Example: "Identify error"'
          rows={3}
        />
        <div className="action-row">
          <button onClick={runPipeline} disabled={loading || isListening}>
            {loading ? 'Processing...' : 'Run STT → NLU → TTS'}
          </button>
          <button className="secondary-button" onClick={listenFromMicrophone} disabled={loading || (isListening && !isRecordingAudio)}>
            {isRecordingAudio ? 'Listening...' : 'Speak secure command'}
          </button>
          <button className="secondary-button" onClick={listenFromMicrophoneWithoutAuth} disabled={loading}>
            {isNoAuthRecognitionActive ? 'Listening (fast)...' : isRecordingAudio ? 'Listening...' : 'Speak command (no auth)'}
          </button>
          <button className="secondary-button" onClick={toggleWakeMode} disabled={loading}>
            {isWakeModeEnabled ? 'Disable wake word' : 'Enable wake word'}
          </button>
        </div>
        <p className="wake-status">{wakeStatus}</p>
        {wakewordBackendReason && <p className="wake-status">Wake backend: {wakewordBackendReason}</p>}
        {speakerInfo && (
          <p className="wake-status">
            Speaker: {speakerInfo.name} ({speakerInfo.role}) | confidence: {speakerInfo.confidence} | access:{' '}
            {speakerInfo.accessGranted ? 'granted' : 'denied'}
          </p>
        )}
        {isAuthSessionFresh() && authSpeaker && (
          <p className="wake-status">
            Secure session cache active for {authSpeaker.name} ({authSpeaker.role}) | expires in ~{authSessionSecondsLeft}s
          </p>
        )}
        {intent && <p className="intent-badge">Detected intent: {intent}</p>}
        {error && <p className="error-text">{error}</p>}
          </section>
        )}

        {activePanel === 'voice' && (
          <VoiceCommands
            systemVoiceCommands={SYSTEM_VOICE_COMMANDS}
            wakeStatus={wakeStatus}
            wakewordBackendReason={wakewordBackendReason}
            speakerInfo={speakerInfo}
            authSpeaker={authSpeaker}
            authSessionSecondsLeft={authSessionSecondsLeft}
            isAuthSessionFresh={isAuthSessionFresh}
            loading={loading}
            isRecordingAudio={isRecordingAudio}
            isListening={isListening}
            isNoAuthRecognitionActive={isNoAuthRecognitionActive}
            toggleWakeMode={toggleWakeMode}
            isWakeModeEnabled={isWakeModeEnabled}
            listenFromMicrophone={listenFromMicrophone}
            listenFromMicrophoneWithoutAuth={listenFromMicrophoneWithoutAuth}
            error={error}
          />
        )}

        {activePanel === 'custom' && (
          <CustomCommands
            categories={categories}
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
            newCategoryName={newCategoryName}
            setNewCategoryName={setNewCategoryName}
            newTrigger={newTrigger}
            setNewTrigger={setNewTrigger}
            newActionType={newActionType}
            setNewActionType={setNewActionType}
            newActionTarget={newActionTarget}
            setNewActionTarget={setNewActionTarget}
            newResponseTemplate={newResponseTemplate}
            setNewResponseTemplate={setNewResponseTemplate}
            addCategory={addCategory}
            addCommand={addCommand}
            savedCommands={savedCommands}
            deleteCommand={deleteCommand}
            onImportCommands={importCommands}
          />
        )}

        {activePanel === 'errors' && (
          <ErrorEvents
            errorEvents={errorEvents}
            downloadLogs={downloadLogs}
            deleteErrorEvent={deleteErrorEvent}
            loading={loading}
          />
        )}

        {activePanel === 'chat' && (
          <AIChat
            onSendMessage={sendAIChatMessage}
            onToggleMicrophone={toggleAIChatMicrophone}
            onSpeakText={speakText}
            isRecordingAudio={isRecordingAudio}
            loading={loading}
          />
        )}

        <section className="card results-grid">
        <div className="field">
          <label htmlFor="stt-output">STT result</label>
          <textarea id="stt-output" value={sttText} readOnly rows={3} />
        </div>

        <div className="field">
          <label htmlFor="command-output">Action command (NLU / adapter)</label>
          <textarea id="command-output" value={commandText} readOnly rows={4} />
        </div>

        <div className="field">
          <label htmlFor="tts-output">TTS response text</label>
          <textarea id="tts-output" value={ttsText} readOnly rows={3} />
          <div className="action-row">
            <button className="secondary-button" onClick={() => speakText(ttsText)} disabled={!ttsText.trim()}>
              Speak response
            </button>
            <button className="danger-button" onClick={stopSpeaking} disabled={!isSpeaking}>
              Stop TTS
            </button>
          </div>
        </div>
        </section>
        </div>
    </main>
  )
}

export default App
