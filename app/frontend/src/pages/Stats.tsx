import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

interface Stats {
  total_words: number
  learned: number
  mastered: number
  streak_days: number
  due_today: number
  weak_words: { word_id: string; word: string; lapses: number }[]
}

export default function Stats() {
  const [s, setS] = useState<Stats | null>(null)
  useEffect(() => {
    api.get<Stats>('/stats').then((r) => setS(r.data))
  }, [])
  if (!s) return <div className="min-h-screen bg-slate-50 flex items-center justify-center">加载中…</div>
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-xl font-bold text-slate-800">📊 学习统计</h1>

        {/* 主行动区：今日任务入口 */}
        <Link
          to="/today"
          className="block bg-blue-500 hover:bg-blue-600 text-white rounded-2xl px-6 py-4 text-center font-semibold shadow transition"
        >
          开始今日任务
          {s.due_today > 0 && (
            <span className="ml-2 inline-block bg-white/20 rounded-full px-2 text-sm">{s.due_today} 词待复习</span>
          )}
        </Link>

        <div className="grid grid-cols-2 gap-3">
          <Card label="已学" value={s.learned} sub={`/ 全词库 ${s.total_words} 词`} />
          <Card label="已掌握" value={s.mastered} sub="连续复习、间隔≥7天即算掌握" />
          <Card label="连续天数" value={s.streak_days} sub="天" />
          <Card label="今日待复习" value={s.due_today} sub="词" />
        </div>

        {s.weak_words.length > 0 && (
          <div className="bg-white rounded-2xl shadow p-4">
            <p className="font-semibold text-slate-700 mb-2">⚠️ 薄弱词 TOP</p>
            {s.weak_words.map((w) => (
              <p key={w.word_id} className="text-sm text-slate-600 py-1">
                {w.word} <span className="text-red-400">错 {w.lapses} 次</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Card({ label, value, sub }: { label: string; value: number; sub: string }) {
  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-3xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-400">{sub}</p>
    </div>
  )
}
