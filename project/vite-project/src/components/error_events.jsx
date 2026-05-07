function ErrorEvents({ errorEvents, downloadLogs, deleteErrorEvent, loading }) {
  return (
    <section className="card">
      <h2>Error events</h2>
      <p className="settings-note">Backlog from the backend error store.</p>
      <button className="secondary-button" onClick={downloadLogs} disabled={loading}>
        Download logs (CSV)
      </button>

      {errorEvents.length === 0 ? (
        <p className="empty-note">No saved errors.</p>
      ) : (
        <div className="event-list">
          {errorEvents.map((eventItem) => (
            <div className="event-item" key={eventItem.id}>
              <div>
                <p className="event-title">{eventItem.device}</p>
                <p className="event-meta">{eventItem.reason}</p>
                <p className="event-meta">{new Date(eventItem.timestamp).toLocaleString()}</p>
              </div>
              <button className="danger-button" onClick={() => deleteErrorEvent(eventItem.id)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default ErrorEvents
