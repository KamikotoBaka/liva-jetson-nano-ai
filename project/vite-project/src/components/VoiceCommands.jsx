function VoiceCommands({
  systemVoiceCommands,
  wakeStatus,
  wakewordBackendReason,
  speakerInfo,
  authSpeaker,
  authSessionSecondsLeft,
  isAuthSessionFresh,
  loading,
  isRecordingAudio,
  isListening,
  isNoAuthRecognitionActive,
  toggleWakeMode,
  isWakeModeEnabled,
  listenFromMicrophone,
  listenFromMicrophoneWithoutAuth,
  error,
}) {
  return (
    <section className="card">
      <h2>Voice commands</h2>
      <p className="settings-note">System phrases and live voice controls.</p>

      <div className="command-list">
        {systemVoiceCommands.map((item) => (
          <div className="command-item" key={item.phrase}>
            <div>
              <p className="command-trigger">{item.phrase}</p>
              <p className="command-action">{item.action}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="action-row">
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
          Speaker: {speakerInfo.name} ({speakerInfo.role}) | confidence: {speakerInfo.confidence} | access: {speakerInfo.accessGranted ? 'granted' : 'denied'}
        </p>
      )}
      {isAuthSessionFresh() && authSpeaker && (
        <p className="wake-status">
          Secure session cache active for {authSpeaker.name} ({authSpeaker.role}) | expires in ~{authSessionSecondsLeft}s
        </p>
      )}
      {error && <p className="error-text">{error}</p>}
    </section>
  )
}

export default VoiceCommands
