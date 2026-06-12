import { useState, useEffect, useCallback } from 'react'
import Header     from './components/Header.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ChatInput  from './components/ChatInput.jsx'
import PdfUpload  from './components/PdfUpload.jsx'
import { streamMessage, uploadPdf } from './services/api.js'
import './styles/app.css'

const WELCOME = {
  id:        'welcome',
  role:      'assistant',
  content:   "Hello! I'm VertexMind. Ask me anything about your indexed documents or current web information.",
  timestamp: Date.now(),
  route:     null,
  citations: [],
  streaming: false,
}

export default function App() {
  const [messages,     setMessages]     = useState([WELCOME])
  const [loading,      setLoading]      = useState(false)
  const [history,      setHistory]      = useState([])      // conversation memory
  const [isDragging,   setIsDragging]   = useState(false)   // PDF drag overlay
  const [uploadStatus, setUploadStatus] = useState(null)    // { type, message }

  // ── PDF drag-and-drop (window-level) ───────────────────────
  useEffect(() => {
    const onDragOver = (e) => {
      e.preventDefault()
      if ([...e.dataTransfer.types].includes('Files')) setIsDragging(true)
    }
    const onDragLeave = (e) => {
      if (!e.relatedTarget) setIsDragging(false)
    }
    const onDrop = (e) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file?.type === 'application/pdf') handleUpload(file)
    }

    window.addEventListener('dragover',   onDragOver)
    window.addEventListener('dragleave',  onDragLeave)
    window.addEventListener('drop',       onDrop)
    return () => {
      window.removeEventListener('dragover',  onDragOver)
      window.removeEventListener('dragleave', onDragLeave)
      window.removeEventListener('drop',      onDrop)
    }
  }, [])

  // ── PDF upload handler ──────────────────────────────────────
  const handleUpload = useCallback(async (file) => {
    setUploadStatus({ type: 'loading', message: `Uploading ${file.name}…` })
    try {
      const result = await uploadPdf(file)
      setUploadStatus({ type: 'success', message: result.message })
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Upload failed.'
      setUploadStatus({ type: 'error', message: detail })
    } finally {
      setTimeout(() => setUploadStatus(null), 6000)
    }
  }, [])

  // ── Send message with streaming ─────────────────────────────
  const handleSend = useCallback(async (question) => {
    const userId = `user-${Date.now()}`
    const asstId = `asst-${Date.now()}`

    // Add user bubble immediately
    setMessages(prev => [...prev, {
      id: userId, role: 'user', content: question,
      timestamp: Date.now(), route: null, citations: [], streaming: false,
    }])

    // Add empty assistant bubble (streaming placeholder)
    setMessages(prev => [...prev, {
      id: asstId, role: 'assistant', content: '',
      timestamp: Date.now(), route: null, citations: [], streaming: true,
    }])

    setLoading(true)
    let fullContent = ''

    await streamMessage(question, history, {
      onRoute: (route) => {
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, route } : m
        ))
      },
      onToken: (token) => {
        fullContent += token
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, content: fullContent } : m
        ))
      },
      onCitations: (citations) => {
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, citations } : m
        ))
      },
      onDone: async () => {
        setMessages(prev => prev.map(m =>
          m.id === asstId ? { ...m, streaming: false } : m
        ))
        setLoading(false)
        // Keep last 6 exchanges (12 messages) for memory
        setHistory(prev => [
          ...prev,
          { role: 'user',      content: question     },
          { role: 'assistant', content: fullContent   },
        ].slice(-12))

      },
      onError: () => {
        setMessages(prev => prev.map(m =>
          m.id === asstId
            ? { ...m, content: "Sorry, I couldn't reach the AI service. Please try again.", streaming: false }
            : m
        ))
        setLoading(false)
      },
    })
  }, [history])

  return (
    <div className="app">
      <Header onUploadFile={handleUpload} />

      {/* PDF drag-drop overlay */}
      <PdfUpload
        isDragging={isDragging}
        onFileDrop={handleUpload}
        onFileSelect={handleUpload}
      />

      {/* Upload status toast */}
      {uploadStatus && (
        <div className={`upload-toast upload-toast--${uploadStatus.type}`}>
          {uploadStatus.type === 'loading' && <span className="toast-spinner" />}
          {uploadStatus.message}
        </div>
      )}

      <main className="main">
        <ChatWindow messages={messages} loading={false} />
      </main>

      <ChatInput
        onSend={handleSend}
        disabled={loading}
      />
    </div>
  )
}
