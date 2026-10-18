'use client'

import { useEffect, useState } from 'react'
import Layout from '@/components/Layout'
import { api } from '@/lib/api'
import { Flashcard } from '@/lib/types'

export default function FlashcardsPage() {
  const [flashcards, setFlashcards] = useState<Flashcard[]>([])
  const [current, setCurrent] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    api.flashcards.list().then(setFlashcards).catch(() => {})
    api.flashcards.stats().then(setStats).catch(() => {})
  }, [])

  const review = async (score: number) => {
    if (flashcards[current]) {
      await api.flashcards.review(flashcards[current].id, score).catch(() => {})
    }
    setFlipped(false)
    const next = (current + 1) % Math.max(flashcards.length, 1)
    setCurrent(next)
    api.flashcards.stats().then(setStats).catch(() => {})
  }

  if (flashcards.length === 0) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold mb-2">Flashcards</h1>
          <p className="text-slate-500">No flashcards yet. Generate them from lessons.</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Flashcards</h1>
          {stats && (
            <div className="text-xs text-slate-500">
              {stats.reviewed}/{stats.total} reviewed &middot; {stats.due_for_review} due
            </div>
          )}
        </div>

        <div
          className="p-8 rounded-lg bg-surface border border-slate-700 cursor-pointer min-h-[200px] flex items-center justify-center text-center"
          onClick={() => setFlipped(!flipped)}
        >
          <div>
            <div className="text-xs text-slate-500 mb-3">
              {flipped ? 'ANSWER' : 'QUESTION'} &middot; {current + 1}/{flashcards.length}
            </div>
            <div className="text-xl">
              {flipped ? flashcards[current]?.back : flashcards[current]?.front}
            </div>
            <div className="text-xs text-slate-600 mt-4">Click to flip</div>
          </div>
        </div>

        {flipped && (
          <div className="space-y-2">
            <div className="text-sm text-slate-500 text-center">How well did you know this?</div>
            <div className="flex justify-center gap-2">
              {[
                { label: 'Again', score: 1 },
                { label: 'Hard', score: 2 },
                { label: 'Good', score: 3 },
                { label: 'Easy', score: 4 },
                { label: 'Perfect', score: 5 },
              ].map(({ label, score }) => (
                <button
                  key={score}
                  onClick={() => review(score)}
                  className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
