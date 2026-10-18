const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),

  courses: {
    list: () => request<any[]>('/api/courses/'),
    get: (id: number) => request<any>(`/api/courses/${id}`),
    create: (data: any) => request<any>('/api/courses/', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: number) => request<any>(`/api/courses/${id}`, { method: 'DELETE' }),
  },

  lessons: {
    list: (moduleId?: number) =>
      request<any[]>(`/api/lessons/${moduleId ? `?module_id=${moduleId}` : ''}`),
    get: (id: number) => request<any>(`/api/lessons/${id}`),
    updateProgress: (id: number, completed: boolean) =>
      request<any>(`/api/lessons/${id}/progress?completed=${completed}`, { method: 'POST' }),
  },

  notes: {
    generate: (lessonId: number) =>
      request<any>('/api/notes/generate', {
        method: 'POST',
        body: JSON.stringify({ lesson_id: lessonId }),
      }),
    list: (lessonId?: number) =>
      request<any[]>(`/api/notes/${lessonId ? `?lesson_id=${lessonId}` : ''}`),
  },

  flashcards: {
    list: (lessonId?: number) =>
      request<any[]>(`/api/flashcards/${lessonId ? `?lesson_id=${lessonId}` : ''}`),
    stats: () => request<any>('/api/flashcards/stats'),
    create: (data: any) => request<any>('/api/flashcards/', { method: 'POST', body: JSON.stringify(data) }),
    review: (id: number, score: number) =>
      request<any>(`/api/flashcards/${id}/review`, {
        method: 'POST',
        body: JSON.stringify({ score }),
      }),
  },

  coding: {
    problems: (lessonId?: number) =>
      request<any[]>(`/api/coding/problems${lessonId ? `?lesson_id=${lessonId}` : ''}`),
    explain: (problem: string) =>
      request<any>(`/api/coding/explain?problem_statement=${encodeURIComponent(problem)}`),
    review: (problemId: number, code: string, lang = 'python') =>
      request<any>(`/api/coding/problems/${problemId}/review`, {
        method: 'POST',
        body: JSON.stringify({ problem_id: problemId, user_code: code, language: lang }),
      }),
    generateHint: (problemId: number, level = 1) =>
      request<any>(`/api/coding/problems/${problemId}/hints/generate?level=${level}`, { method: 'POST' }),
  },

  mcq: {
    extract: (pageText: string) =>
      request<any>(`/api/mcq/extract?page_text=${encodeURIComponent(pageText)}`, { method: 'POST' }),
    explain: (questionText: string, optionsJson: string) =>
      request<any>(
        `/api/mcq/explain?question_text=${encodeURIComponent(questionText)}&options_json=${encodeURIComponent(optionsJson)}`,
        { method: 'POST' }
      ),
  },

  analytics: {
    dashboard: () => request<any>('/api/analytics/dashboard'),
    sessions: () => request<any[]>('/api/analytics/sessions'),
    weakAreas: () => request<any[]>('/api/analytics/weak-areas'),
  },

  automation: {
    start: () => request<any>('/api/automation/start', { method: 'POST' }),
    stop: () => request<any>('/api/automation/stop', { method: 'POST' }),
    navigate: (url: string) =>
      request<any>('/api/automation/navigate', { method: 'POST', body: JSON.stringify({ url }) }),
    content: () => request<any>('/api/automation/content'),
    detectCompletion: () => request<any>('/api/automation/detect-completion'),
    nextLesson: () => request<any>('/api/automation/next-lesson', { method: 'POST' }),
    modules: () => request<any>('/api/automation/modules'),
  },
}
