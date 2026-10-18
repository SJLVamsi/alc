'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { DashboardStats as Stats } from '@/lib/types'
import { BookOpen, Clock, Brain, AlertTriangle } from 'lucide-react'

export default function DashboardStats() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.analytics.dashboard()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-slate-500 text-sm">Loading...</div>
  if (!stats) return <div className="text-red-400 text-sm">Failed to load stats</div>

  const cards = [
    { label: 'Lessons Completed', value: `${stats.lessons_completed}/${stats.total_lessons}`, icon: BookOpen },
    { label: 'Study Time', value: `${stats.study_time_minutes}m`, icon: Clock },
    { label: 'Concepts Learned', value: stats.concepts_learned, icon: Brain },
    { label: 'Weak Areas', value: stats.weak_areas.length, icon: AlertTriangle },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(({ label, value, icon: Icon }) => (
        <div key={label} className="p-4 rounded-lg bg-surface border border-slate-700">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
            <Icon className="w-3 h-3" />
            {label}
          </div>
          <div className="text-2xl font-bold text-primary-light">{value}</div>
        </div>
      ))}
    </div>
  )
}
