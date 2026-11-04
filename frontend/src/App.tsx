import { useState } from 'react'
import { StartScreen } from './components/StartScreen'
import { InterviewScreen } from './components/InterviewScreen'
import { ResultScreen } from './components/ResultScreen'
import type { VerdictData } from './types'

type ScreenState = 'start' | 'interview' | 'result'

export function App() {
  const [screen, setScreen] = useState<ScreenState>('start')
  const [jobDescription, setJobDescription] = useState('')
  const [initialMessage, setInitialMessage] = useState('')
  const [verdict, setVerdict] = useState<VerdictData | null>(null)

  const handleStart = (jdText: string, message: string) => {
    setJobDescription(jdText)
    setInitialMessage(message)
    setScreen('interview')
  }

  const handleInterviewComplete = (finalVerdict: VerdictData) => {
    setVerdict(finalVerdict)
    setScreen('result')
  }

  const handleRestart = () => {
    setJobDescription('')
    setInitialMessage('')
    setVerdict(null)
    setScreen('start')
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 font-sans selection:bg-indigo-500 selection:text-white">
      {screen === 'start' && <StartScreen onStart={handleStart} />}
      {screen === 'interview' && (
        <InterviewScreen
          initialMessage={initialMessage}
          jobDescription={jobDescription}
          onComplete={handleInterviewComplete}
          onExit={handleRestart}
        />
      )}
      {screen === 'result' && verdict && (
        <ResultScreen verdict={verdict} onRestart={handleRestart} />
      )}
    </div>
  )
}

export default App
