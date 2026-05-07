function CustomCommands({
  categories,
  selectedCategory,
  setSelectedCategory,
  newCategoryName,
  setNewCategoryName,
  newTrigger,
  setNewTrigger,
  newActionType,
  setNewActionType,
  newActionTarget,
  setNewActionTarget,
  newResponseTemplate,
  setNewResponseTemplate,
  addCategory,
  addCommand,
  savedCommands,
  deleteCommand,
  onImportCommands,
}) {
  const handleExport = () => {
    const dataStr = JSON.stringify(savedCommands, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(dataBlob)
    link.download = `custom-commands-${new Date().toISOString().split('T')[0]}.json`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const handleImport = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result)
        if (Array.isArray(imported)) {
          onImportCommands(imported)
        } else {
          alert('Invalid format: JSON must be an array of commands')
        }
      } catch (err) {
        alert(`Error importing file: ${err.message}`)
      }
    }
    reader.readAsText(file)
    event.target.value = ''
  }

  return (
    <section className="card">
      <h2>Create custom command</h2>
      <div className="field">
        <label htmlFor="new-category-name">Create category</label>
        <div className="action-row">
          <input
            id="new-category-name"
            value={newCategoryName}
            onChange={(event) => setNewCategoryName(event.target.value)}
            placeholder="Example: Kitchen"
          />
          <button type="button" className="secondary-button" onClick={addCategory}>
            Add category
          </button>
        </div>
      </div>

      <div className="field">
        <label htmlFor="new-command-category">Command category</label>
        <select
          id="new-command-category"
          value={selectedCategory}
          onChange={(event) => setSelectedCategory(event.target.value)}
        >
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="new-trigger">Command phrase</label>
        <input
          id="new-trigger"
          value={newTrigger}
          onChange={(event) => setNewTrigger(event.target.value)}
          placeholder="Example: Check factory status"
        />
      </div>

      <div className="field">
        <label htmlFor="new-action-type">Action type</label>
        <select
          id="new-action-type"
          value={newActionType}
          onChange={(event) => setNewActionType(event.target.value)}
        >
          <option value="REST">REST</option>
          <option value="MQTT">MQTT</option>
        </select>
      </div>

      <div className="field">
        <label htmlFor="new-action-target">Action command</label>
        <textarea
          id="new-action-target"
          value={newActionTarget}
          onChange={(event) => setNewActionTarget(event.target.value)}
          placeholder={newActionType === 'REST' ? 'Example: GET /api/devices/status' : 'Example: factory/conveyor/cmd'}
          rows={2}
        />
      </div>

      <div className="field">
        <label htmlFor="new-response-template">Response template</label>
        <textarea
          id="new-response-template"
          value={newResponseTemplate}
          onChange={(event) => setNewResponseTemplate(event.target.value)}
          placeholder="Example: Device {device_name} reports: {status}"
          rows={2}
        />
      </div>

      <div className="custom-command-actions">
        <button onClick={addCommand}>Save command</button>
        <div className="custom-command-actions-right">
          <button onClick={handleExport} className="secondary-button" title="Download commands as JSON">
            Export commands
          </button>
          <button
            type="button"
            onClick={() => document.getElementById('import-custom-commands')?.click()}
            className="secondary-button"
          >
            Import commands
          </button>
          <input
            id="import-custom-commands"
            type="file"
            accept=".json"
            onChange={handleImport}
            className="visually-hidden-file-input"
          />
        </div>
      </div>

      <h2>My custom commands</h2>
      {savedCommands.length === 0 ? (
        <p className="empty-note">No custom commands yet.</p>
      ) : (
        <div className="command-list">
          {savedCommands.map((item) => (
            <div className="command-item" key={item.trigger}>
              <div>
                <p className="command-trigger">{item.trigger}</p>
                <p className="command-action">Category: {item.category}</p>
                <p className="command-action">{item.actionType}: {item.actionTarget}</p>
                <p className="command-action">Response: {item.responseTemplate}</p>
              </div>
              <button className="danger-button" onClick={() => deleteCommand(item.trigger)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default CustomCommands
