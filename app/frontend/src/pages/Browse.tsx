import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type WordRecord } from '../lib/api'

interface Unit { grade: string; semester: string; unit: string }

const GRADES = ['六', '七', '八']

export default function Browse() {
  const [units, setUnits] = useState<Unit[]>([])
  const [grade, setGrade] = useState('六')
  const [sel, setSel] = useState<Unit | null>(null)
  const [words, setWords] = useState<WordRecord[]>([])

  useEffect(() => {
    api.get<Unit[]>('/units').then((r) => setUnits(r.data))
  }, [])

  const gradeUnits = useMemo(
    () => units.filter((u) => u.grade === grade),
    [units, grade],
  )

  const open = async (u: Unit) => {
    setSel(u)
    const r = await api.get<WordRecord[]>(`/units/${u.grade}/${u.semester}/${u.unit}`)
    setWords(r.data)
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-xl font-bold text-slate-800">📖 教材单元词表</h1>

        {/* 年级分组（折叠：只展开当前年级） */}
        <div className="flex gap-2">
          {GRADES.map((g) => (
            <button
              key={g}
              onClick={() => setGrade(g)}
              className={`rounded-full px-5 py-2 text-sm font-medium transition ${
                grade === g ? 'bg-slate-800 text-white' : 'bg-white text-slate-500 border border-slate-200'
              }`}
            >
              {g}年级
            </button>
          ))}
        </div>

        {/* 当前年级的学期/单元 */}
        <div className="flex flex-wrap gap-2">
          {gradeUnits.map((u, i) => (
            <button
              key={i}
              onClick={() => open(u)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                sel === u ? 'bg-blue-500 text-white' : 'bg-white text-slate-600 border border-slate-200'
              }`}
            >
              {u.semester} U{u.unit}
            </button>
          ))}
        </div>

        {sel && (
          <div className="bg-white rounded-2xl shadow p-4 divide-y divide-slate-100">
            <p className="text-sm text-slate-400 pb-2">{sel.grade}年级{sel.semester}册 Unit {sel.unit} · {words.length} 词</p>
            {words.map((w) => (
              <div key={w.id} className="py-3">
                <p className="font-semibold text-slate-800">
                  {w.word}
                  {w.phonetic && <span className="ml-2 font-normal text-slate-400">/{w.phonetic}/</span>}
                  <span className="text-amber-500">{"★".repeat(w.exam_level)}</span>
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
