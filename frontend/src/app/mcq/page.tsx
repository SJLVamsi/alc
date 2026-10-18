'use client'

import { useState } from 'react'
import Layout from '@/components/Layout'
import { api } from '@/lib/api'
import { MCQExplanation } from '@/lib/types'
import { RefreshCw } from 'lucide-react'

export default function MCQPage() {
  const [pageText, setPageText] = useState('')
  const [extracted, setExtracted] = useState<any>(null)
  const [explanation, setExplanation] = useState<MCQExplanation | null>(null)
  const [loading, setLoading] = useState(false)

  const extract = async () => {
    if (!pageText.trim()) return
    setLoading(true)
    const result = await api.mcq.extract(pageText).catch(() => ({}))
    setExtracted(result)
    setLoading(false)
  }

  const explain = async () => {
    if (!extracted?.question_text) return
    setLoading(true)
    const result = await api.mcq.explain(
      extracted.question_text,
      JSON.stringify(extracted.options || [])
    ).catch(() => ({}))
    setExplanation(result as MCQExplanation)
    setLoading(false)
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">MCQ Learning Assistant</h1>

        <div className="space-y-3">
          <textarea
            className="w-full h-32 px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm resize-none"
            placeholder="Paste the page content with MCQ questions here..."
            value={pageText}
            onChange={(e) => setPageText(e.target.value)}
          />
          <button
            onClick={extract}
            disabled={loading || !pageText.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded bg-primary hover:bg-primary-dark disabled:opacity-50 text-sm"
          >
            {loading && <RefreshCw className="w-4 h-4 animate-spin" />}
            Extract Question
          </button>
        </div>

        {extracted?.question_text && (
          <div className="p-4 rounded-lg bg-surface border border-slate-700 space-y-3">
            <div>
              <div className="text-xs text-slate-500 mb-1">Question</div>
              <div className="text-sm font-medium">{extracted.question_text}</div>
            </div>
            {extracted.options && (
              <div className="space-y-1">
                {extracted.options.map((o: any, i: number) => (
                  <div key={i} className="text-sm px-2 py-1 rounded bg-slate-800">
                    <span className="font-mono text-primary-light">{o.label}:</span> {o.text}
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={explain}
              disabled={loading}
              className="px-4 py-2 rounded bg-secondary hover:bg-secondary-dark text-sm"
            >
              Explain Options
            </button>
          </div>
        )}

        {explanation && (
          <div className="space-y-4">
            {explanation.options.map((opt, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg border ${
                  opt.is_correct
                    ? 'bg-green-900/20 border-green-700'
                    : 'bg-surface border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-sm text-primary-light">{opt.label}</span>
                  <span className="text-sm">{opt.text}</span>
                  {opt.is_correct && (
                    <span className="text-xs text-green-400">(Correct)</span>
                  )}
                </div>
                <div className="text-sm text-slate-400">{opt.explanation}</div>
              </div>
            ))}

            <div className="p-4 rounded-lg bg-surface border border-slate-700">
              <div className="text-xs text-slate-500 mb-1">Suggested Answer</div>
              <div className="text-lg font-bold text-primary-light mb-2">
                {explanation.suggested_answer}
              </div>
              <div className="text-sm text-slate-400">{explanation.overall_reasoning}</div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
