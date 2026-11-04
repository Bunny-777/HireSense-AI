import { CheckCircle2, AlertTriangle, RefreshCw, Check, ArrowRight } from 'lucide-react'
import type { VerdictData } from '../types'

interface ResultScreenProps {
  verdict: VerdictData
  onRestart: () => void
}

export const ResultScreen = ({ verdict, onRestart }: ResultScreenProps) => {
  const isRecommended = verdict.verdict === 'Recommend'

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-zinc-50 dark:bg-zinc-950">
      <main className="w-full max-w-2xl py-8">
        {/* Main Card */}
        <div className="bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 p-6 sm:p-10 space-y-8">
          {/* Verdict Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-100 dark:border-zinc-800">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 block mb-2">
                Interview Verdict
              </span>
              <div className="flex items-center gap-2.5">
                {isRecommended ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/60">
                    <CheckCircle2 className="w-4 h-4" />
                    Recommend
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/60">
                    <AlertTriangle className="w-4 h-4" />
                    Don't recommend
                  </span>
                )}
                <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  Rating: <span className="text-zinc-900 dark:text-zinc-100 font-semibold">{verdict.rating}/10</span>
                </span>
              </div>
            </div>

            {/* Quick Score Metric */}
            <div className="flex items-center gap-1 sm:self-center">
              {[...Array(10)].map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-6 rounded-full transition-all ${
                    i < verdict.rating
                      ? isRecommended
                        ? 'bg-emerald-500 dark:bg-emerald-400'
                        : 'bg-amber-500 dark:bg-amber-400'
                      : 'bg-zinc-100 dark:bg-zinc-800'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Executive Summary */}
          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Evaluation Summary
            </h2>
            <p className="text-sm sm:text-base leading-relaxed text-zinc-800 dark:text-zinc-200">
              {verdict.summary}
            </p>
            {verdict.reasoning && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400 italic pt-1">
                "{verdict.reasoning}"
              </p>
            )}
          </div>

          {/* Strengths & Gaps (Two Columns) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            {/* Strengths */}
            <div className="bg-zinc-50/70 dark:bg-zinc-950/40 border border-zinc-200/70 dark:border-zinc-800/70 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                  <Check className="w-3 h-3 stroke-[3]" />
                </div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                  Key Strengths
                </h3>
              </div>
              <ul className="space-y-2.5">
                {verdict.strengths.length > 0 ? (
                  verdict.strengths.map((item, idx) => (
                    <li key={idx} className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed flex items-start gap-2">
                      <span className="text-emerald-500 mt-1 select-none">•</span>
                      <span>{item}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-xs text-zinc-400">No specific strengths noted.</li>
                )}
              </ul>
            </div>

            {/* Gaps */}
            <div className="bg-zinc-50/70 dark:bg-zinc-950/40 border border-zinc-200/70 dark:border-zinc-800/70 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-950/80 flex items-center justify-center text-amber-600 dark:text-amber-400">
                  <ArrowRight className="w-3 h-3 stroke-[3]" />
                </div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                  Areas for Growth
                </h3>
              </div>
              <ul className="space-y-2.5">
                {verdict.gaps.length > 0 ? (
                  verdict.gaps.map((item, idx) => (
                    <li key={idx} className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed flex items-start gap-2">
                      <span className="text-amber-500 mt-1 select-none">•</span>
                      <span>{item}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-xs text-zinc-400">No major gaps identified.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Action */}
          <div className="pt-4">
            <button
              type="button"
              onClick={onRestart}
              className="w-full py-3.5 px-4 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Start new interview
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
