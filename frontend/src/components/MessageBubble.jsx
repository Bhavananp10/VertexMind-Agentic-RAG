import CitationList from './CitationList.jsx'

const ROUTE_LABELS = {
  vectordb: { label: 'Documents', cls: 'route-docs' },
  websearch: { label: 'Web Search', cls: 'route-web' },
  both:     { label: 'Documents + Web', cls: 'route-both' },
  direct:   null,
}

const ROUTE_STATUS = {
  vectordb: 'Searching documents…',
  websearch: 'Searching the web…',
  both:     'Searching documents & web…',
  direct:   'Thinking…',
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MessageBubble({ message }) {
  const isUser    = message.role === 'user'
  const routeInfo = message.route ? ROUTE_LABELS[message.route] : null
  const isEmpty   = !message.content && message.streaming

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="avatar assistant-avatar">VM</div>}

      <div className="bubble-column">
        <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>

          {/* Status line while waiting for first token */}
          {isEmpty && message.route && (
            <p className="stream-status">{ROUTE_STATUS[message.route]}</p>
          )}
          {isEmpty && !message.route && (
            <p className="stream-status">Thinking…</p>
          )}

          {/* Message content + blinking cursor while streaming */}
          {message.content && (
            <p className="message-content">
              {message.content}
              {message.streaming && <span className="stream-cursor" />}
            </p>
          )}

          {/* Meta row — time + route badge */}
          {!isEmpty && (
            <div className="message-meta">
              <span className="message-time">{formatTime(message.timestamp)}</span>
              {routeInfo && (
                <span className={`route-badge ${routeInfo.cls}`}>{routeInfo.label}</span>
              )}
            </div>
          )}
        </div>

        {/* Citations — shown below the bubble for assistant messages */}
        {!isUser && !message.streaming && (
          <CitationList citations={message.citations} />
        )}
      </div>

      {isUser && <div className="avatar user-avatar">You</div>}
    </div>
  )
}
