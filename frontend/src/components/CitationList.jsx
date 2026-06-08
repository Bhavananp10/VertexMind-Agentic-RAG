export default function CitationList({ citations }) {
  if (!citations?.length) return null

  return (
    <div className="citation-list">
      <p className="citation-label">Sources</p>
      {citations.map((c, i) => (
        <div key={i} className="citation-card">
          <div className="citation-header">
            <span className="citation-icon">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/>
              </svg>
            </span>
            <span className="citation-source">{c.source}</span>
            {c.page !== '?' && c.page !== undefined && (
              <span className="citation-page">p. {c.page}</span>
            )}
          </div>
          {c.snippet && (
            <p className="citation-snippet">"{c.snippet}"</p>
          )}
        </div>
      ))}
    </div>
  )
}
