import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 min — LLM + vector search can be slow
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function sendMessage(question) {
  const response = await client.post('/chat', { question })
  return response.data
}
