import { useState, useRef, useEffect } from 'react'
import type { FormEvent } from 'react'
import { Send, Dumbbell } from 'lucide-react'
import { sendMessage } from './api'
import UIComponentRenderer from './components/UIComponentRenderer'
import type { Message } from './types'

const PHONE_KEY = 'apex_phone'

function PhoneSetup({ onDone }: { onDone: (phone: string) => void }) {
  const [phone, setPhone] = useState('+1')
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-6 p-6">
      <div className="flex items-center gap-3">
        <Dumbbell className="text-purple-400" size={32} />
        <h1 className="text-3xl font-bold text-white">Apex</h1>
      </div>
      <p className="text-gray-400 text-sm">Enter your phone number to get started</p>
      <form
        className="flex gap-3 w-full max-w-sm"
        onSubmit={(e) => {
          e.preventDefault()
          if (phone.trim()) {
            localStorage.setItem(PHONE_KEY, phone.trim())
            onDone(phone.trim())
          }
        }}
      >
        <input
          className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
          placeholder="+15551234567"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <button
          type="submit"
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Start
        </button>
      </form>
    </div>
  )
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[80%]">
        {!isUser && (
          <div className="flex items-center gap-2 mb-1">
            <Dumbbell className="text-purple-400" size={14} />
            <span className="text-xs text-purple-400 font-medium">Apex</span>
          </div>
        )}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-purple-600 text-white rounded-br-sm'
              : 'bg-gray-800 text-gray-100 rounded-bl-sm'
          }`}
        >
          {msg.text}
        </div>
        {msg.ui_components.map((c, i) => (
          <UIComponentRenderer key={i} component={c} />
        ))}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-800 px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const savedPhone = localStorage.getItem(PHONE_KEY)
  const [phone, setPhone] = useState<string | null>(savedPhone)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!phone) {
    return <PhoneSetup onDone={setPhone} />
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text,
      ui_components: [],
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await sendMessage(phone!, text)
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: res.text,
        ui_components: res.ui_components ?? [],
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: 'Sorry, something went wrong. Please try again.',
          ui_components: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <Dumbbell className="text-purple-400" size={22} />
          <span className="font-semibold text-white text-lg">Apex</span>
        </div>
        <button
          onClick={() => {
            localStorage.removeItem(PHONE_KEY)
            setPhone(null)
            setMessages([])
          }}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {phone}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <Dumbbell className="text-purple-400 opacity-50" size={48} />
            <p className="text-gray-500 text-sm">
              Hey! I'm Apex, your AI fitness coach.
              <br />
              Tell me about your goals to get started.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatBubble key={msg.id} msg={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="px-4 py-4 border-t border-gray-800 flex gap-3"
      >
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
          placeholder="Message Apex..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-colors"
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  )
}
