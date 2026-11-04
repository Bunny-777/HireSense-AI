import React, { useState, useRef } from 'react'
import { UploadCloud, FileText, X, ArrowRight, Loader2 } from 'lucide-react'
import { uploadJD, startInterview } from '../api'

interface StartScreenProps {
  onStart: (jdText: string, initialMessage: string) => void
}

export const StartScreen: React.FC<StartScreenProps> = ({ onStart }) => {
  const [file, setFile] = useState<File | null>(null)
  const [pastedText, setPastedText] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0]
      if (isValidFileType(selected)) {
        setFile(selected)
        setError(null)
      } else {
        setError('Please upload a PDF or DOCX file.')
      }
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0]
      if (isValidFileType(selected)) {
        setFile(selected)
        setError(null)
      } else {
        setError('Please upload a PDF or DOCX file.')
      }
    }
  }

  const isValidFileType = (f: File) => {
    const ext = f.name.split('.').pop()?.toLowerCase()
    return ext === 'pdf' || ext === 'docx' || ext === 'txt' || ext === 'md'
  }

  const handleStart = async () => {
    if (!file && !pastedText.trim()) {
      setError('Please provide a job description by uploading a document or pasting text.')
      return
    }

    try {
      setLoading(true)
      setError(null)

      // 1. Upload & extract JD
      const jdText = await uploadJD(file, pastedText)

      // 2. Fetch initial interview greeting
      const init = await startInterview()

      onStart(jdText, init.message)
    } catch (err: any) {
      setError(err.message || 'Failed to start interview. Please check your backend connection.')
    } finally {
      setLoading(false)
    }
  }

  const hasContent = Boolean(file || pastedText.trim())

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-zinc-50 dark:bg-zinc-950">
      <main className="w-full max-w-xl">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium tracking-wide uppercase bg-zinc-200/70 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 mb-3">
            HireSense AI
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Technical Mock Interview
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Upload the job description to begin a tailored mock interview.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 sm:p-8 space-y-6">
          {/* File Upload Area */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2">
              Job Description Document
            </label>

            {!file ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center p-6 sm:p-8 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20'
                    : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50/60 dark:bg-zinc-950/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={handleFileInput}
                  className="hidden"
                  aria-label="Upload job description file"
                />
                <UploadCloud className="w-8 h-8 text-zinc-400 mb-3" />
                <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 text-center">
                  Drag and drop your JD, or <span className="text-indigo-600 dark:text-indigo-400">browse</span>
                </p>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  Supports PDF, DOCX, or TXT
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3.5 bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700/60 rounded-xl">
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
                  <div className="truncate">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                  }}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 transition-colors"
                  aria-label="Remove uploaded file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="relative flex items-center justify-center">
            <div className="border-t border-zinc-200 dark:border-zinc-800 w-full" />
            <span className="bg-white dark:bg-zinc-900 px-3 text-xs uppercase tracking-wider text-zinc-400">
              or paste text
            </span>
          </div>

          {/* Textarea */}
          <div>
            <label
              htmlFor="jd-text"
              className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2"
            >
              Paste Job Description
            </label>
            <textarea
              id="jd-text"
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste job title, responsibilities, and requirements here..."
              className="w-full p-3.5 text-sm bg-zinc-50/60 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800 rounded-xl resize-none text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 p-3 rounded-lg border border-rose-200 dark:border-rose-900">
              {error}
            </div>
          )}

          {/* Primary Action Button */}
          <button
            type="button"
            onClick={handleStart}
            disabled={!hasContent || loading}
            className="w-full py-3.5 px-4 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Preparing interview...
              </>
            ) : (
              <>
                Start interview
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </main>
    </div>
  )
}
