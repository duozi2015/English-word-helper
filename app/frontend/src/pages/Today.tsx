import { useEffect, useState } from 'react'
import { api, type Deck, type WordRecord, type ReviewOut } from '../lib/api'

type Phase = 'loading' | 'done' | 'front' | 'back'

export default function Today() {
  const [deck, setDeck] = useState<Deck | null>(null)
  const [queue, setQueue] = useState<WordBriefList>([])
  const [idx, setIdx] = useState(0)
  const [phase, setPhase] = useState<Phase>('loading')
  const [detail, setDetail] = useState<WordRecord | null>(null)
  const [lastResult, setLastResult] = useState<ReviewOut | null>(null)
  const [doneCount, setDoneCount] = useState(0)

  useEffect(() => {
    api.get<Deck>('/deck/today').then((r) => {
      const q = [...r.data.due, ...r.data.new]
      setDeck(r.data)
      setQueue(q)
      setPhase(q.length ? 'front' : 'done')
    })
  }, [])

  const current = queue[idx]

  const grade = async (q: 1 | 3 | 5) => {
    const r = await api.post<ReviewOut>('/review', {
      word_id: current.word_id,
      mode: 'card',
      quality: q,
    })
    setLastResult(r.data)
    setDoneCount((c) => c + 1)
    speak(current.word)
    next()
  }

  const next = () => {
    if (idx + 1 >= queue.length) setPhase('done')
    else {
      setIdx(idx + 1)
      setPhase('front')
      setDetail(null)
      const nid = queue[idx + 1].word_id
      api.get<WordRecord>(`/words/${nid}`).then((r) => setDetail(r.data))
    }
  }

  const speak = (word: string) => {
    new Audio(`/words/api/tts/${encodeURIComponent(word)}.mp3`).play().catch(() => {})
  }

  if (phase === 'loading')
    return <Center><p className="text-slate-400">加载中…</p></Center>

  if (phase === 'done')
    return (
      <Center>
        <div className="bg-white rounded-2xl shadow p-10 text-center space-y-3">
          <p className="text-5xl">🎉</p>
          <p className="text-xl font-semibold text-slate-800">今日任务完成！</p>
          <p className="text-slate-500">复习 {deck?.due.length ?? 0} + 新学 {deck?.new.length ?? 0} = {doneCount || (deck?.due.length ?? 0) + (deck?.new.length ?? 0)} 词</p>
          {lastResult && (
            <p className="text-sm text-slate-400">最后复习：{lastResult.word_id} → 下次 {lastResult.next_review_date}</p>
          )}
        </div>
      </Center>
    )

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center px-4 py-8">
      {/* 进度 */}
      <div className="w-full max-w-md flex items-center gap-2 mb-6">
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${(idx / queue.length) * 100}%` }}
          />
        </div>
        <span className="text-sm text-slate-400">{idx + 1}/{queue.length}</span>
      </div>

      {phase === 'front' && (
        <Card>
          <p className="text-6xl font-bold text-slate-800 mb-4">{current.word}</p>
          <SpeakButton onClick={() => speak(current.word)} />
          <p className="mt-6 text-slate-400">点击卡片看释义</p>
        </Card>
      )}

      {phase === 'front' && (
        <button
          className="mt-6 rounded-lg border border-slate-300 bg-white px-6 py-2 text-slate-600"
          onClick={() => setPhase('back')}
        >
          翻转卡片
        </button>
      )}

      {phase === 'back' && detail && (
        <>
          <Card>
            <div className="text-left w-full space-y-3 max-h-[50vh] overflow-y-auto">
              <p className="text-3xl font-bold text-slate-800">{current.word}</p>
              {detail.meanings.map((m, i) => (
                <p key={i} className="text-lg text-slate-700">
                  <span className="text-slate-400 mr-2">{m.pos}</span>{m.meaning}
                </p>
              ))}
              {detail.word_forms.length > 0 && (
                <p className="text-sm text-slate-500">
                  词形：{detail.word_forms.map((f) => `${f.type}=${f.form}`).join('，')}
                </p>
              )}
              {detail.examples.slice(0, 2).map((ex, i) => (
                <div key={i} className="bg-slate-50 rounded-lg p-3">
                  <p className="text-slate-700">{ex.en}</p>
                  <p className="text-slate-400 text-sm">{ex.zh}</p>
                </div>
              ))}
              {detail.phrases.length > 0 && (
                <p className="text-sm text-slate-500">
                  词组：{detail.phrases.map((p) => p.text).join('，')}
                </p>
              )}
              {detail.teaching_notes.map((t, i) => (
                <div key={i} className="bg-amber-50 rounded-lg p-3">
                  <p className="text-sm font-semibold text-amber-700">👨‍🏫 名师点拨</p>
                  <p className="text-sm text-amber-900 whitespace-pre-wrap">{t.content}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* 三档自评 */}
          <div className="mt-6 w-full max-w-md grid grid-cols-3 gap-3">
            <button onClick={() => grade(1)} className="rounded-xl bg-red-100 hover:bg-red-200 text-red-700 font-semibold py-4 transition">
              😵 不认识
            </button>
            <button onClick={() => grade(3)} className="rounded-xl bg-amber-100 hover:bg-amber-200 text-amber-700 font-semibold py-4 transition">
              🤔 模糊
            </button>
            <button onClick={() => grade(5)} className="rounded-xl bg-emerald-100 hover:bg-emerald-200 text-emerald-700 font-semibold py-4 transition">
              😄 认识
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8 flex flex-col items-center justify-center min-h-[320px]">
      {children}
    </div>
  )
}

function SpeakButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-2xl" title="发音">
      🔊
    </button>
  )
}

function Center({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-slate-50 flex items-center justify-center">{children}</div>
}

type WordBriefList = { word_id: string; word: string }[]
