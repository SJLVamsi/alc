import type { Metadata } from 'next'
import '@/styles/globals.css'

export const metadata: Metadata = {
  title: 'AI Learning Copilot',
  description: 'Local-first AI assistant for online learning',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-alt text-slate-100">
        {children}
      </body>
    </html>
  )
}
