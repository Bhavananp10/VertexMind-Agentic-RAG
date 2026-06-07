const ROUTE_LABELS = {
  vectordb: { label: 'Documents', cls: 'route-docs' },
  websearch: { label: 'Web Search', cls: 'route-web' },
  both: { label: 'Documents + Web', cls: 'route-both' },
  direct: null,
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const routeInfo = message.route ? ROUTE_LABELS[message.route] : null

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="avatar assistant-avatar">VM</div>}

      <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
        <p className="message-content">{message.content}</p>
        <div className="message-meta">
          <span className="message-time">{formatTime(message.timestamp)}</span>
          {routeInfo && (
            <span className={`route-badge ${routeInfo.cls}`}>
              {routeInfo.label}
            </span>
          )}
        </div>
      </div>

      {isUser && <div className="avatar user-avatar">You</div>}
    </div>
  )
}
