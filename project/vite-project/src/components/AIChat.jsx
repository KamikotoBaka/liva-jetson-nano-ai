import { useRef, useState } from 'react'

function AIChat({ onSendMessage, onToggleMicrophone, onSpeakText, isRecordingAudio, loading }) {
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatError, setChatError] = useState('')
  const pendingVoiceTurnRef = useRef(null)

  const sendMessage = async () => {
    const trimmed = chatInput.trim()
    if (!trimmed) {
      return
    }

    setChatError('')
    setMessages((current) => [...current, { role: 'user', content: trimmed }])
    setChatInput('')

    try {
      const response = await onSendMessage(trimmed)
      if (onSpeakText && response?.ttsText) {
        onSpeakText(response.ttsText)
      }
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.ttsText || 'No answer returned.',
          meta: `route: ${response.route || 'n/a'} | intent: ${response.intent || 'n/a'}`,
        },
      ])
    } catch (error) {
      setChatError(error?.message || 'AI chat request failed.')
    }
  }

  const appendAssistantMessage = (response) => {
    setMessages((current) => [
      ...current,
      {
        role: 'assistant',
        content: response.ttsText || 'No answer returned.',
        meta: `route: ${response.route || 'n/a'} | intent: ${response.intent || 'n/a'}`,
      },
    ])
  }

  const startVoiceCapture = () => {
    if (!onToggleMicrophone) {
      return
    }

    setChatError('')
    const pending = onToggleMicrophone()
    if (pending && typeof pending.then === 'function') {
      pendingVoiceTurnRef.current = pending
    }
  }

  const stopVoiceCaptureAndSend = async () => {
    if (!onToggleMicrophone || !pendingVoiceTurnRef.current) {
      return
    }

    setChatError('')
    const pending = pendingVoiceTurnRef.current
    pendingVoiceTurnRef.current = null
    await onToggleMicrophone()

    try {
      const response = await pending

      if (onSpeakText && response?.ttsText) {
        onSpeakText(response.ttsText)
      }

      const transcript = (response.sttText || '').trim()
      if (transcript) {
        setMessages((current) => [...current, { role: 'user', content: transcript }])
      }

      appendAssistantMessage(response)
    } catch (error) {
      setChatError(error?.message || 'AI voice chat request failed.')
    }
  }

  const handleVoiceButton = async () => {
    if (isRecordingAudio) {
      await stopVoiceCaptureAndSend()
      return
    }

    startVoiceCapture()
  }

  const handleKeyDown = async (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      await sendMessage()
    }
  }

  return (
    <section className="card">
      <h2>AI chat</h2>
      <p className="settings-note">Chat with routed thinking and non-thinking models.</p>

      <div className="chat-thread">
        {messages.length === 0 ? (
          <p className="empty-note">No messages yet. Ask a question or type a command.</p>
        ) : (
          messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`chat-bubble chat-${message.role}`}>
              <p className="chat-role">{message.role === 'user' ? 'You' : 'LIVA'}</p>
              <p className="chat-content">{message.content}</p>
              {message.meta && <p className="chat-meta">{message.meta}</p>}
            </div>
          ))
        )}
      </div>

      <div className="field">
        <label htmlFor="ai-chat-input">Message</label>
        <textarea
          id="ai-chat-input"
          rows={3}
          value={chatInput}
          onChange={(event) => setChatInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question or type an action command"
        />
      </div>
      <div className="action-row">
        <button onClick={sendMessage} disabled={loading || !chatInput.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
        <button type="button" className="secondary-button" onClick={handleVoiceButton} disabled={loading}>
          {isRecordingAudio ? 'Tap to stop and send' : 'Tap to record'}
        </button>
      </div>
      {chatError && <p className="error-text">{chatError}</p>}
    </section>
  )
}

export default AIChat
