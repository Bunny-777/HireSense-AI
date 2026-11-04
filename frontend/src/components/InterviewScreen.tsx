import { useState, useEffect, useRef, type KeyboardEvent } from 'react'
import { Send, AlertCircle, Loader2, LogOut } from 'lucide-react'
import type { ChatMessage, InterviewStage, VerdictData } from '../types'
import { streamChatMessage, getVerdict } from '../api'

interface InterviewScreenProps {
  initialMessage: string
  jobDescription: string
  onComplete: (verdict: VerdictData) => void
  onExit: () => void
}

const STAGES: { key: InterviewStage; label: string }[] = [
  { key: 'intro', label: 'Intro' },
  { key: 'questions', label: 'Questions' },
  { key: 'projects', label: 'Projects' },
  { key: 'verdict', label: 'Verdict' },
]

export const InterviewScreen = ({
  initialMessage,
  jobDescription,
  onComplete,
  onExit,
}: InterviewScreenProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content: initialMessage,
      timestamp: Date.now(),
    },
  ])
  const [stage, setStage] = useState<InterviewStage>('intro')
  const [turnsInStage, setTurnsInStage] = useState(0)
  const [input, setInput] = useState('')
  const [isAiResponding, setIsAiResponding] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages, isAiResponding])

  // Focus textarea on load
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isAiResponding || evaluating) return

    const candidateMsg: ChatMessage = {
      id: `c-${Date.now()}`,
      role: 'candidate',
      content: text,
      timestamp: Date.now(),
    }

    const updatedMessages = [...messages, candidateMsg]
    setMessages(updatedMessages)
    setInput('')
    setIsAiResponding(true)
    setError(null)

    // Temporary placeholder for streaming AI message
    const aiMsgId = `a-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      {
        id: aiMsgId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      },
    ])

    await streamChatMessage(
      updatedMessages,
      stage,
      jobDescription,
      turnsInStage,
      // onToken
      (token) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m))
        )
      },
      // onComplete
      async (nextStage, isComplete) => {
        setIsAiResponding(false)
        if (nextStage !== stage) {
          setStage(nextStage)
          setTurnsInStage(0)
        } else {
          setTurnsInStage((prev) => prev + 1)
        }

        if (isComplete || nextStage === 'verdict') {
          await triggerVerdict(updatedMessages)
        }
      },
      // onError
      (errMsg) => {
        setIsAiResponding(false)
        setError(errMsg)
      }
    )
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const triggerVerdict = async (msgs: ChatMessage[]) => {
    setEvaluating(true)
    setStage('verdict')

    // Prepare Q&A pairs
    const conversation: { question: string; answer: string }[] = []
    let introText = ''

    for (let i = 0; i < msgs.length; i++) {
      if (msgs[i].role === 'assistant') {
        const question = msgs[i].content
        const answer = msgs[i + 1]?.role === 'candidate' ? msgs[i + 1].content : ''
        if (i === 0) {
          introText = answer
        }
        if (answer) {
          conversation.push({ question, answer })
        }
      }
    }

    try {
      const verdictData = await getVerdict(conversation, jobDescription, introText)
      onComplete(verdictData)
    } catch {
      setError('Failed to generate interview verdict. Please try again.')
      setEvaluating(false)
    }
  }

  const handleEndEarly = async () => {
    if (window.confirm('Are you sure you want to end the interview and generate your feedback now?')) {
      await triggerVerdict(messages)
    }
  }

  const handleLeave = () => {
    if (window.confirm('Leave the interview without saving results?')) {
      onExit()
    }
  }

  const activeIndex = STAGES.findIndex((s) => s.key === stage)

  return (
    <div className="flex flex-col h-screen max-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md px-4 sm:px-6 py-3.5 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              HireSense Interview
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleLeave}
              className="text-xs font-medium text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 p-1.5 rounded-lg transition-colors"
              title="Leave interview"
            >
              <LogOut className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleEndEarly}
              disabled={evaluating}
              className="text-xs font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-zinc-100 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 transition-colors"
            >
              End interview
            </button>
          </div>
        </div>

        {/* Thin Progress Indicator */}
        <div className="max-w-3xl mx-auto mt-3">
          <div className="flex items-center justify-between text-[11px] font-medium text-zinc-400 dark:text-zinc-500 mb-1.5 px-0.5">
            {STAGES.map((s, idx) => (
              <span
                key={s.key}
                className={`transition-colors ${
                  idx === activeIndex
                    ? 'text-indigo-600 dark:text-indigo-400 font-semibold'
                    : idx < activeIndex
                    ? 'text-zinc-700 dark:text-zinc-300'
                    : ''
                }`}
              >
                {s.label}
              </span>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {STAGES.map((s, idx) => (
              <div
                key={s.key}
                className={`h-1 rounded-full transition-all duration-300 ${
                  idx < activeIndex
                    ? 'bg-indigo-600 dark:bg-indigo-500'
                    : idx === activeIndex
                    ? 'bg-indigo-600 dark:bg-indigo-400 ring-2 ring-indigo-400/20'
                    : 'bg-zinc-200 dark:bg-zinc-800'
                }`}
              />
            ))}
          </div>
        </div>
      </header>

      {/* Chat Area (Single Column, Centered) */}
      <main
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto px-4 py-6 sm:px-6"
      >
        <div className="max-w-2xl mx-auto space-y-6">
          {messages.map((m) => {
            const isAi = m.role === 'assistant'
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isAi ? 'items-start' : 'items-end'}`}
              >
                {/* Sender badge */}
                <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500 mb-1 px-1">
                  {isAi ? 'AI Interviewer' : 'You'}
                </span>

                {/* Message bubble */}
                <div
                  className={`max-w-[85%] sm:max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isAi
                      ? 'bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-sm'
                      : 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-tr-sm font-normal'
                  }`}
                >
                  {m.content ? (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  ) : (
                    /* Typing indicator within bubble */
                    <div className="flex items-center gap-1.5 py-1 px-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" />
                      <div className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0.2s]" />
                      <div className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0.4s]" />
                    </div>
                  )}
                </div>
              </div>
            )
          })}

          {evaluating && (
            <div className="flex items-center justify-center p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm">
              <div className="flex items-center gap-3 text-sm text-zinc-600 dark:text-zinc-300">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-600 dark:text-indigo-400" />
                <span>Compiling final evaluation and verdict...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 p-3 text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 rounded-xl">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      </main>

      {/* Pinned Bottom Input */}
      <footer className="flex-shrink-0 border-t border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md p-4 sm:p-5">
        <div className="max-w-2xl mx-auto">
          <div className="relative flex items-center bg-zinc-100 dark:bg-zinc-800/70 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/10 transition-all">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isAiResponding || evaluating}
              placeholder={evaluating ? "Evaluating interview..." : "Type your response... (Enter to send, Shift+Enter for newline)"}
              className="w-full py-3.5 pl-4 pr-12 text-sm bg-transparent text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 resize-none focus:outline-none max-h-32 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim() || isAiResponding || evaluating}
              className="absolute right-2.5 p-2 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mt-1.5 px-1">
            <span>Press Enter to send, Shift+Enter for new line</span>
            {isAiResponding && <span className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400">Interviewer is replying...</span>}
          </div>
        </div>
      </footer>
    </div>
  )
}
