export default function Header({ onUploadFile }) {
  const handleUploadClick = () => {
    document.getElementById('pdf-file-input')?.click()
  }

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <div className="logo-icon-wrap">
            <span className="logo-icon">VM</span>
          </div>
          <div className="logo-text">
            <h1>VertexMind</h1>
            <p>Agentic Enterprise Knowledge Assistant</p>
          </div>
        </div>

        <div className="header-actions">
          <button className="upload-btn" onClick={handleUploadClick} title="Upload a PDF to index">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z"/>
              <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z"/>
            </svg>
            Upload PDF
          </button>

          <div className="status-badge">
            <span className="status-dot" />
            Online
          </div>
        </div>
      </div>
    </header>
  )
}
