import { useState, useRef } from 'react'
import { transcribeAudio } from '../services/api'

export default function ChatInput({ onSend, disabled }) {
  const [value,          setValue]          = useState('')
  const [isRecording,    setIsRecording]    = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const textareaRef      = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef        = useRef([])

  // ── Text send ───────────────────────────────────────────────
  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleInput = (e) => {
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
    setValue(el.value)
  }

  // ── Voice recording ─────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      chunksRef.current = []

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setIsTranscribing(true)
        try {
          const transcript = await transcribeAudio(blob)
          if (transcript) onSend(transcript)
        } catch (err) {
          console.error('[stt] Transcription failed:', err)
        } finally {
          setIsTranscribing(false)
        }
      }

      recorder.start()
      mediaRecorderRef.current = recorder
      setIsRecording(true)
    } catch (err) {
      console.error('[stt] Microphone access denied:', err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
  }

  const handleMicClick = () => {
    if (isRecording) stopRecording()
    else startRecording()
  }

  const micDisabled = disabled || isTranscribing

  return (
    <div className="input-area">
      <div className="input-container">

        {/* ── Textarea ── */}
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={value}
          onInput={handleInput}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isRecording    ? 'Listening...' :
            isTranscribing ? 'Transcribing...' :
            'Ask anything about your documents or the web...'
          }
          disabled={disabled || isRecording || isTranscribing}
          rows={1}
        />

        {/* ── Send button ── */}
        <button
          className="send-button"
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>

        {/* ── Mic button (right corner) ── */}
        <button
          className={`mic-button ${isRecording ? 'recording' : ''} ${isTranscribing ? 'processing' : ''}`}
          onClick={handleMicClick}
          disabled={micDisabled}
          aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
          title={isRecording ? 'Click to stop' : 'Click to speak'}
        >
          {isTranscribing ? (
            <span className="mic-spinner" />
          ) : isRecording ? (
            /* Stop icon */
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            /* Mic icon */
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8"  y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>

      </div>
      <p className="input-hint">
        Enter to send · Shift+Enter for new line · 🎤 speak · 🔊 listen per message
      </p>
    </div>
  )
}
