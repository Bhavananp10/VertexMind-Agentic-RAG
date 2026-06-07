export default function Header() {
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
        <div className="status-badge">
          <span className="status-dot" />
          Online
        </div>
      </div>
    </header>
  )
}
