export type InterviewStage = 'intro' | 'questions' | 'projects' | 'verdict'

export interface ChatMessage {
  id: string
  role: 'assistant' | 'candidate'
  content: string
  timestamp: number
}

export interface VerdictData {
  verdict: 'Recommend' | "Don't recommend"
  rating: number
  summary: string
  strengths: string[]
  gaps: string[]
  reasoning: string
}
