import { useEffect } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './stores/auth'
import Login from './pages/Login'
import Today from './pages/Today'
import Browse from './pages/Browse'
import Stats from './pages/Stats'

function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-slate-100">
        <div className="max-w-2xl mx-auto flex items-center gap-1 px-4 h-12">
          <span className="font-bold text-slate-700 mr-3">📚 背单词</span>
          {[
            ['今日', '/today'],
            ['词表', '/browse'],
            ['统计', '/stats'],
          ].map(([label, to]) => (
            <button key={to} onClick={() => nav(to)}
              className="px-3 py-1 rounded-lg text-sm text-slate-600 hover:bg-slate-100">
              {label}
            </button>
          ))}
          <span className="flex-1" />
          <span className="text-sm text-slate-400">{user?.display_name || user?.username}</span>
          <button onClick={logout} className="text-sm text-slate-400 hover:text-red-400 px-2">退出</button>
        </div>
      </nav>
      {children}
    </div>
  )
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading, fetchMe } = useAuth()
  useEffect(() => {
    fetchMe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-400">…</div>
  if (!user) return <Navigate to="/login" replace />
  return <Shell>{children}</Shell>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/today" element={<Protected><Today /></Protected>} />
      <Route path="/browse" element={<Protected><Browse /></Protected>} />
      <Route path="/stats" element={<Protected><Stats /></Protected>} />
      <Route path="*" element={<Navigate to="/today" replace />} />
    </Routes>
  )
}
