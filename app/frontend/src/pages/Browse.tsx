import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type WordRecord } from '../lib/api'

interface Unit { grade: string; semester: string; unit: string }

export default function Browse() {
  const [units, setUnits] = useState<Unit[]>([])
  const [sel, setSel] = useState<Unit | null>(null)
  const [words, setWords] = useState<WordRecord[]>([])

  useEffect(() => {
    api.get<Unit[]>('/units').then((r) => setUnits(r.data))
  }, [])

  const open = async (u: Unit) => {
    setSel(u)
    const r = await api.get<WordRecord[]>(`/units/${u.grade}/${u.semester}/${u.unit}`)
    setWords(r.data)
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-xl font-bold text-slate-800">📖 教材单元词表</h1>
        <div className="flex flex-wrap gap-2">
          {units.map((u, i) => (
            <button
              key={i}
              onClick={() => open(u)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                sel === u ? 'bg-blue-500 text-white' : 'bg-white text-slate-600 border border-slate-200'
              }`}
            >
              {u.grade}{u.semester} U{u.unit}
            </button>
          ))}
        </div>
        {sel && (
          <div className="bg-white rounded-2xl shadow p-4 divide-y divide-slate-100">
            {words.map((w) => (
              <div key={w.id} className="py-3">
                <p className="font-semibold text-slate-800">
                  {w.word} <span className="text-amber-500">{"★".repeat(w.exam_level)}</span>
                </p>
                <p className="text-sm text-slate-500">
                  {w.meanings.map((m) => `${m.pos} ${m.meaning}`).join('；')}
                </p>
              </div>
            ))}
          </div>
        )}
        <Link to="/today" className="block text-center text-blue-500">← 回到今日任务</Link>
      </div>
    </div>
  )
}
