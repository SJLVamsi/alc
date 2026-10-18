export interface Course {
  id: number
  name: string
  platform?: string
  url?: string
  created_at: string
  updated_at?: string
  modules?: Module[]
}

export interface Module {
  id: number
  course_id: number
  name: string
  order: number
  url?: string
  lessons?: Lesson[]
}

export interface Lesson {
  id: number
  module_id: number
  title: string
  order: number
  url?: string
  content_text?: string
  is_coding: boolean
  is_mcq: boolean
  progress?: LessonProgress
}

export interface LessonProgress {
  id: number
  lesson_id: number
  completed: boolean
  started_at: string
  completed_at?: string
  study_time_seconds: number
}

export interface Note {
  id: number
  lesson_id: number
  summary?: string
  detailed_notes?: string
  key_concepts?: string
  created_at: string
}

export interface Flashcard {
  id: number
  lesson_id: number
  front: string
  back: string
  difficulty: number
  created_at: string
}

export interface CodingProblem {
  id: number
  lesson_id: number
  title: string
  description: string
  solution_template?: string
}

export interface CodingSolution {
  id: number
  problem_id: number
  user_code: string
  language: string
  time_complexity?: string
  space_complexity?: string
  feedback?: string
  is_optimal: boolean
}

export interface DashboardStats {
  lessons_completed: number
  total_lessons: number
  study_time_minutes: number
  concepts_learned: number
  weak_areas: string[]
  flashcards_due: number
  next_revision?: string
}

export interface GenerationResult {
  summary: string
  detailed_notes: string
  key_concepts: string
  flashcards: { front: string; back: string }[]
  revision_questions: { question: string; answer: string }[]
}

export interface MCQExplanation {
  question_text: string
  options: { label: string; text: string; is_correct: boolean; explanation: string }[]
  suggested_answer: string
  overall_reasoning: string
}
