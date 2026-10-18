'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function HomePage() {
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    api.health().then(() => setHealthy(true)).catch(() => setHealthy(false))
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl text-center space-y-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-primary-light">AI Learning Copilot</h1>
          <p className="text-slate-400">
            Your local-first AI assistant for online learning
          </p>
        </div>

        {healthy !== null && (
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
            healthy ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
          }`}>
            <span className={`w-2 h-2 rounded-full ${healthy ? 'bg-green-400' : 'bg-red-400'}`} />
            {healthy ? 'Backend connected' : 'Backend offline'}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
          <Link href="/dashboard" className="p-4 rounded-lg bg-surface border border-slate-700 hover:border-primary/50 transition-colors text-left">
            <div className="font-medium">Dashboard</div>
            <div className="text-xs text-slate-500">Progress & stats</div>
          </Link>
          <Link href="/courses" className="p-4 rounded-lg bg-surface border border-slate-700 hover:border-primary/50 transition-colors text-left">
            <div className="font-medium">Courses</div>
            <div className="text-xs text-slate-500">Manage courses</div>
          </Link>
          <Link href="/flashcards" className="p-4 rounded-lg bg-surface border border-slate-700 hover:border-primary/50 transition-colors text-left">
            <div className="font-medium">Flashcards</div>
            <div className="text-xs text-slate-500">Review & study</div>
          </Link>
          <Link href="/coding" className="p-4 rounded-lg bg-surface border border-slate-700 hover:border-primary/50 transition-colors text-left">
            <div className="font-medium">Coding</div>
            <div className="text-xs text-slate-500">Problem assistant</div>
          </Link>
        </div>
      </div>
    </div>
  )
}
