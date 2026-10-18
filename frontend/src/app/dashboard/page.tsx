'use client'

import { useEffect, useState } from 'react'
import Layout from '@/components/Layout'
import DashboardStats from '@/components/DashboardStats'
import { api } from '@/lib/api'
import { Flashcard } from '@/lib/types'

export default function DashboardPage() {
  const [flashcards, setFlashcards] = useState<Flashcard[]>([])
  const [currentCard, setCurrentCard] = useState(0)
  const [flipped, setFlipped] = useState(false)

  useEffect(() => {
    api.flashcards.list().then(setFlashcards).catch(() => {})
  }, [])

  const handleReview = async (score: number) => {
    if (flashcards[currentCard]) {
      await api.flashcards.review(flashcards[currentCard].id, score).catch(() => {})
    }
    setFlipped(false)
    setCurrentCard((c) => (c + 1) % Math.max(flashcards.length, 1))
  }

  return (
    <Layout>
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <DashboardStats />

        {flashcards.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Flashcard Review</h2>
            <div
              className="p-6 rounded-lg bg-surface border border-slate-700 cursor-pointer min-h-[120px] flex items-center justify-center text-center"
              onClick={() => setFlipped(!flipped)}
            >
              <div>
                <div className="text-xs text-slate-500 mb-2">
                  {flipped ? 'Answer' : 'Question'} ({currentCard + 1}/{flashcards.length})
                </div>
                <div className="text-lg">
                  {flipped ? flashcards[currentCard]?.back : flashcards[currentCard]?.front}
                </div>
                <div className="text-xs text-slate-600 mt-2">Click to flip</div>
              </div>
            </div>
            {flipped && (
              <div className="flex gap-2 justify-center">
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    onClick={() => handleReview(score)}
                    className="px-3 py-1 rounded bg-slate-700 hover:bg-slate-600 text-sm"
                  >
                    {score}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="p-4 rounded-lg bg-surface border border-slate-700">
          <h2 className="font-semibold mb-2">Weak Areas</h2>
          <WeakAreaList />
        </div>
      </div>
    </Layout>
  )
}

function WeakAreaList() {
  const [areas, setAreas] = useState<any[]>([])
  useEffect(() => {
    api.analytics.weakAreas().then(setAreas).catch(() => {})
  }, [])
  if (areas.length === 0) return <p className="text-sm text-slate-500">No weak areas identified yet</p>
  return (
    <ul className="space-y-1">
      {areas.map((a) => (
        <li key={a.id} className="flex justify-between text-sm">
          <span>{a.concept}</span>
          <span className="text-slate-500">{Math.round(a.confidence * 100)}%</span>
        </li>
      ))}
    </ul>
  )
}
