import { useState } from 'react'
import Header from './components/Header.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ChatInput from './components/ChatInput.jsx'
import { sendMessage } from './services/api.js'
import './styles/app.css'

const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hello! I'm VertexMind. Ask me anything about your indexed documents or current web information.",
  timestamp: Date.now(),
  route: null,
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [loading, setLoading] = useState(false)

  const handleSend = async (question) => {
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: Date.now(),
      route: null,
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const data = await sendMessage(question)
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.answer,
        timestamp: Date.now(),
        route: data.route || null,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: "Sorry, I couldn't reach the AI service. Please try again.",
        timestamp: Date.now(),
        route: null,
        isError: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <Header />
      <main className="main">
        <ChatWindow messages={messages} loading={loading} />
      </main>
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  )
}
