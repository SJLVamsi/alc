'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, BookOpen, Brain, Code, ClipboardList,
  BarChart3, Zap,
} from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/courses', label: 'Courses', icon: BookOpen },
  { href: '/flashcards', label: 'Flashcards', icon: Brain },
  { href: '/coding', label: 'Coding', icon: Code },
  { href: '/mcq', label: 'MCQ Help', icon: ClipboardList },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-surface border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <Link href="/dashboard" className="flex items-center gap-2 text-lg font-bold text-primary-light">
            <Zap className="w-5 h-5" />
            <span>ALC</span>
          </Link>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? 'bg-primary/20 text-primary-light'
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            )
          })}
        </nav>
        <div className="p-4 border-t border-slate-700">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300"
          >
            <BarChart3 className="w-3 h-3" />
            AI Learning Copilot v1.0
          </Link>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
