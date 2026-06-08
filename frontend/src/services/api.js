import axios from 'axios'

const BASE = 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Original endpoint (kept for reference / fallback) ─────────
export async function sendMessage(question, history = []) {
  const res = await client.post('/chat', { question, history })
  return res.data
}

// ── Streaming endpoint — yields tokens via SSE ────────────────
export async function streamMessage(question, history = [], callbacks = {}) {
  const { onRoute, onToken, onCitations, onDone, onError } = callbacks

  try {
    const response = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete last line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'route')     onRoute?.(event.route)
          if (event.type === 'token')     onToken?.(event.content)
          if (event.type === 'citations') onCitations?.(event.citations)
          if (event.type === 'done')      onDone?.()
          if (event.type === 'error')     onError?.(new Error(event.message))
        } catch {
          // ignore malformed SSE line
        }
      }
    }
  } catch (err) {
    onError?.(err)
  }
}

// ── PDF upload ────────────────────────────────────────────────
export async function uploadPdf(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await axios.post(`${BASE}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30_000,
  })
  return res.data
}
