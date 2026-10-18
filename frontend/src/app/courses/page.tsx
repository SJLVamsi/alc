'use client'

import { useEffect, useState } from 'react'
import Layout from '@/components/Layout'
import { api } from '@/lib/api'
import { Course } from '@/lib/types'
import { Plus, ExternalLink, Trash2 } from 'lucide-react'

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [platform, setPlatform] = useState('')

  useEffect(() => { api.courses.list().then(setCourses).catch(() => {}) }, [])

  const addCourse = async () => {
    await api.courses.create({ name, url, platform }).catch(() => {})
    setShowAdd(false)
    setName('')
    setUrl('')
    setPlatform('')
    api.courses.list().then(setCourses)
  }

  const deleteCourse = async (id: number) => {
    await api.courses.delete(id).catch(() => {})
    api.courses.list().then(setCourses)
  }

  return (
    <Layout>
      <div className="space-y-4 max-w-3xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Courses</h1>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary hover:bg-primary-dark text-white text-sm"
          >
            <Plus className="w-4 h-4" /> Add Course
          </button>
        </div>

        {showAdd && (
          <div className="p-4 rounded-lg bg-surface border border-slate-700 space-y-3">
            <input
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm"
              placeholder="Course name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm"
              placeholder="URL (optional)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <input
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-600 text-sm"
              placeholder="Platform (e.g., udemy)"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            />
            <div className="flex gap-2">
              <button onClick={addCourse} className="px-3 py-1.5 rounded bg-primary text-white text-sm">Save</button>
              <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 rounded bg-slate-700 text-sm">Cancel</button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {courses.map((c) => (
            <div key={c.id} className="p-4 rounded-lg bg-surface border border-slate-700 flex items-center justify-between">
              <div>
                <div className="font-medium">{c.name}</div>
                <div className="text-xs text-slate-500">
                  {c.platform || 'Unknown platform'} {c.url && <ExternalLink className="w-3 h-3 inline" />}
                </div>
              </div>
              <button onClick={() => deleteCourse(c.id)} className="text-red-400 hover:text-red-300">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          {courses.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-8">No courses added yet</p>
          )}
        </div>
      </div>
    </Layout>
  )
}
