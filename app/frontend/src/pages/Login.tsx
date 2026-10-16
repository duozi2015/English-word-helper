import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../stores/auth'

export default function Login() {
  const login = useAuth((s) => s.login)
  const user = useAuth((s) => s.user)
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (user) nav('/today')
  }, [user, nav])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      await login(username, password)
    } catch (ex: any) {
      setErr(ex.response?.data?.detail || '登录失败，请检查用户名密码')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <form onSubmit={submit} className="w-full max-w-sm bg-white rounded-2xl shadow p-8 space-y-4">
        <h1 className="text-2xl font-bold text-center text-slate-800">背单词 📚</h1>
        <input
          className="w-full rounded-lg border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
        <input
          className="w-full rounded-lg border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {err && <p className="text-sm text-red-500">{err}</p>}
        <button
          disabled={busy || !username || !password}
          className="w-full rounded-lg bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white font-semibold py-3 transition"
        >
          {busy ? '登录中…' : '登录（与错题本同账号）'}
        </button>
      </form>
    </div>
  )
}
