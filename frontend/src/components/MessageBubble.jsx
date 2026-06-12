import { useState, useRef } from 'react'
import CitationList from './CitationList.jsx'
import { synthesizeSpeech } from '../services/api.js'

const ROUTE_LABELS = {
  vectordb: { label: 'Documents',        cls: 'route-docs' },
  websearch: { label: 'Web Search',      cls: 'route-web'  },
  both:      { label: 'Documents + Web', cls: 'route-both' },
  direct:    null,
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

  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef   = useRef(null)

  const handleSpeak = async () => {
    // If already playing — stop it
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
      setIsPlaying(false)
      return
    }

    try {
      setIsPlaying(true)
      const url   = await synthesizeSpeech(message.content)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setIsPlaying(false); URL.revokeObjectURL(url) }
      audio.onerror = () => { setIsPlaying(false) }
      audio.play()
    } catch (err) {
      console.error('[tts] Speak failed:', err)
      setIsPlaying(false)
    }
  }

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

        {/* Citations below bubble */}
        {!isUser && !message.streaming && (
          <CitationList citations={message.citations} />
        )}

        {/* Speaker button — only for completed assistant messages */}
        {!isUser && !message.streaming && message.content && (
          <div className="speak-row">
            <button
              className={`speak-btn ${isPlaying ? 'playing' : ''}`}
              onClick={handleSpeak}
              title={isPlaying ? 'Stop' : 'Listen to response'}
              aria-label={isPlaying ? 'Stop audio' : 'Read response aloud'}
            >
              {isPlaying ? (
                /* Stop icon */
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              ) : (
                /* Speaker icon */
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              )}
              <span>{isPlaying ? 'Stop' : 'Listen'}</span>
            </button>
          </div>
        )}
      </div>

      {isUser && <div className="avatar user-avatar">You</div>}
    </div>
  )
}
