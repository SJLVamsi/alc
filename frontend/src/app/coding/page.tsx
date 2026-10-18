'use client'

import { useState } from 'react'
import Layout from '@/components/Layout'
import { api } from '@/lib/api'
import { Lightbulb, Send, RefreshCw } from 'lucide-react'

export default function CodingPage() {
  const [problem, setProblem] = useState('')
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [explanation, setExplanation] = useState<any>(null)
  const [review, setReview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const explain = async () => {
    if (!problem.trim()) return
    setLoading(true)
    const result = await api.coding.explain(problem).catch(() => ({}))
    setExplanation(result)
    setLoading(false)
  }

  const doReview = async () => {
    if (!problem.trim() || !code.trim()) return
    setLoading(true)
    const fakeId = 1
    const result = await api.coding.review(fakeId, code, language).catch(() => ({}))
    setReview(result)
    setLoading(false)
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">Coding Assistant</h1>

        <div className="space-y-3">
          <textarea
            className="w-full h-24 px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm font-mono resize-none"
            placeholder="Paste the coding problem statement here..."
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
          />
          <button
            onClick={explain}
            disabled={loading || !problem.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded bg-primary hover:bg-primary-dark disabled:opacity-50 text-sm"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4" />}
            Explain Problem
          </button>
        </div>

        {explanation?.explanation && (
          <div className="p-4 rounded-lg bg-surface border border-slate-700 space-y-3">
            <div>
              <div className="text-xs text-slate-500 mb-1">Explanation</div>
              <div className="text-sm">{explanation.explanation}</div>
            </div>
            {explanation.algorithms && (
              <div>
                <div className="text-xs text-slate-500 mb-1">Algorithms</div>
                <div className="flex flex-wrap gap-1">
                  {explanation.algorithms.map((a: string) => (
                    <span key={a} className="px-2 py-0.5 rounded bg-slate-700 text-xs">{a}</span>
                  ))}
                </div>
              </div>
            )}
            {explanation.data_structures && (
              <div>
                <div className="text-xs text-slate-500 mb-1">Data Structures</div>
                <div className="flex flex-wrap gap-1">
                  {explanation.data_structures.map((d: string) => (
                    <span key={d} className="px-2 py-0.5 rounded bg-slate-700 text-xs">{d}</span>
                  ))}
                </div>
              </div>
            )}
            {explanation.approach && (
              <div>
                <div className="text-xs text-slate-500 mb-1">Approach</div>
                <div className="text-sm">{explanation.approach}</div>
              </div>
            )}
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-600 text-sm"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
            </select>
            <span className="text-xs text-slate-500">Write your solution</span>
          </div>
          <textarea
            className="w-full h-36 px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm font-mono resize-none"
            placeholder="# Write your code here..."
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button
            onClick={doReview}
            disabled={loading || !code.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded bg-secondary hover:bg-secondary-dark disabled:opacity-50 text-sm"
          >
            <Send className="w-4 h-4" />
            Review Solution
          </button>
        </div>

        {review && (
          <div className="p-4 rounded-lg bg-surface border border-slate-700 space-y-2">
            <div className="flex gap-4 text-sm">
              <span>Time: <strong className="text-primary-light">{review.time_complexity || 'N/A'}</strong></span>
              <span>Space: <strong className="text-primary-light">{review.space_complexity || 'N/A'}</strong></span>
              <span>Optimal: <strong className={review.is_optimal ? 'text-green-400' : 'text-yellow-400'}>
                {review.is_optimal ? 'Yes' : 'No'}
              </strong></span>
            </div>
            {review.feedback && <div className="text-sm">{review.feedback}</div>}
          </div>
        )}
      </div>
    </Layout>
  )
}
