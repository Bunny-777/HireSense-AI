import type { ChatMessage, InterviewStage, VerdictData } from './types'

export async function uploadJD(file: File | null, text: string): Promise<string> {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  if (text.trim()) {
    formData.append('text', text.trim())
  }

  const res = await fetch('/api/upload-jd', {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to upload job description' }))
    throw new Error(errorData.detail || 'Failed to upload job description')
  }

  const data = await res.json()
  return data.jd_text
}

export async function startInterview(): Promise<{ message: string; stage: InterviewStage }> {
  const res = await fetch('/api/start', {
    method: 'POST',
  })
  if (!res.ok) {
    throw new Error('Failed to start interview')
  }
  return res.json()
}

export async function streamChatMessage(
  messages: ChatMessage[],
  stage: InterviewStage,
  jobDescription: string,
  turnsInStage: number,
  onToken: (token: string) => void,
  onComplete: (nextStage: InterviewStage, isComplete: boolean) => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonPayload(messages, stage, jobDescription, turnsInStage),
    })

    if (!res.ok || !res.body) {
      throw new Error(`Server returned ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          try {
            const data = JSON.parse(trimmed.slice(6))
            if (data.type === 'token') {
              onToken(data.text)
            } else if (data.type === 'done') {
              onComplete(data.stage, data.is_complete)
            }
          } catch {
            // Ignore malformed chunks
          }
        }
      }
    }
  } catch (err: any) {
    onError(err.message || 'Error communicating with interviewer')
  }
}

export async function getVerdict(
  conversation: { question: string; answer: string }[],
  jobDescription: string,
  intro: string
): Promise<VerdictData> {
  const res = await fetch('/api/verdict', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      conversation,
      job_description: jobDescription,
      intro,
    }),
  })

  if (!res.ok) {
    throw new Error('Failed to generate interview verdict')
  }

  return res.json()
}

function jsonPayload(
  messages: ChatMessage[],
  stage: InterviewStage,
  jobDescription: string,
  turnsInStage: number
) {
  return JSON.stringify({
    messages: messages.map((m) => ({
      role: m.role,
      content: m.content,
    })),
    stage,
    job_description: jobDescription,
    turns_in_stage: turnsInStage,
  })
}
