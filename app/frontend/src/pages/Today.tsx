import { useEffect, useState } from 'react'
import { api, type Deck, type WordRecord, type ReviewOut } from '../lib/api'

type Mode = 'card' | 'choice' | 'spell'
type Phase = 'loading' | 'done' | 'front' | 'back'
type WordBrief = { word_id: string; word: string }

export default function Today() {
  const [deck, setDeck] = useState<Deck | null>(null)
  const [queue, setQueue] = useState<WordBrief[]>([])
  const [idx, setIdx] = useState(0)
  const [mode, setMode] = useState<Mode>('card')
  const [phase, setPhase] = useState<Phase>('loading')
  const [detail, setDetail] = useState<WordRecord | null>(null)
  const [doneCount, setDoneCount] = useState(0)
  const [answered, setAnswered] = useState<null | { ok: boolean; correct: string }>(null)
  const [spellInput, setSpellInput] = useState('')
  const [hintLevel, setHintLevel] = useState(0)
  const [spellResult, setSpellResult] = useState<null | { level: 'perfect' | 'hinted' | 'wrong'; answer: string }>(null)

  const current = queue[idx]

  useEffect(() => {
    api.get<Deck>('/deck/today').then((r) => {
      const q = [...r.data.due, ...r.data.new]
      setDeck(r.data)
      setQueue(q)
      setPhase(q.length ? 'front' : 'done')
      if (q.length) loadDetail(q[0].word_id)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadDetail = (wid: string) => {
    setDetail(null)
    api.get<WordRecord>(`/words/${wid}`).then((r) => setDetail(r.data))
  }

  const speak = (word: string) => {
    new Audio(`/words/api/tts/${encodeURIComponent(word)}.m4a`).play().catch(() => {})
  }

  const resetItemState = () => {
    setAnswered(null)
    setSpellInput('')
    setHintLevel(0)
    setSpellResult(null)
  }

  const submit = async (quality: 1 | 2 | 3 | 5, wrong = '') => {
    await api.post<ReviewOut>('/review', {
      word_id: current.word_id, mode, quality, wrong_answer: wrong || undefined,
    })
    setDoneCount((c) => c + 1)
    if (quality >= 3) speak(current.word)
    if (idx + 1 >= queue.length) setPhase('done')
    else {
      setIdx(idx + 1)
      setPhase('front')
      resetItemState()
      loadDetail(queue[idx + 1].word_id)
    }
  }

  const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ')

  // ---------- 界面 ----------
  if (phase === 'loading')
    return <Center><p className="text-slate-400">加载中…</p></Center>

  if (phase === 'done')
    return (
      <Center>
        <div className="bg-white rounded-2xl shadow p-10 text-center space-y-2">
          <p className="text-5xl">🎉</p>
          <p className="text-xl font-semibold text-slate-800">今日任务完成！</p>
          <p className="text-slate-500">完成 {doneCount} 词（复习 {deck?.due.length ?? 0} + 新学 {deck?.new.length ?? 0}）</p>
        </div>
      </Center>
    )

  const firstPos = detail?.meanings[0]?.pos ?? ''
  const firstMeaning = detail?.meanings[0]?.meaning ?? ''

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      {/* 模式切换 */}
      <div className="flex gap-2 mb-4">
        {([['card', '🃏 认卡'], ['choice', '✅ 选择'], ['spell', '⌨️ 拼写']] as [Mode, string][]).map(([m, label]) => (
          <button key={m} onClick={() => { setMode(m); setPhase('front'); resetItemState() }}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              mode === m ? 'bg-blue-500 text-white' : 'bg-white text-slate-500 border border-slate-200'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* 进度 */}
      <div className="flex items-center gap-2 mb-6">
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${(idx / queue.length) * 100}%` }} />
        </div>
        <span className="text-sm text-slate-400">{idx + 1}/{queue.length}</span>
      </div>

      {/* ======== 认卡模式 ======== */}
      {mode === 'card' && phase === 'front' && (
        <>
          <Card>
            <p className="text-6xl font-bold text-slate-800 mb-4">{current.word}</p>
            <button onClick={() => speak(current.word)} className="text-2xl" title="发音">🔊</button>
            <p className="mt-6 text-slate-400">点击下方翻转看释义</p>
          </Card>
          <button onClick={() => setPhase('back')} className="mt-6 w-full rounded-lg border border-slate-300 bg-white px-6 py-2 text-slate-600">
            翻转卡片
          </button>
        </>
      )}
      {mode === 'card' && phase === 'back' && detail && (
        <>
          <Card>
            <BackDetail detail={detail} word={current.word} />
          </Card>
          <div className="mt-6 grid grid-cols-3 gap-3">
            <GradeBtn color="red" label="😵 不认识" onClick={() => submit(1)} />
            <GradeBtn color="amber" label="🤔 模糊" onClick={() => submit(3)} />
            <GradeBtn color="emerald" label="😄 认识" onClick={() => submit(5)} />
          </div>
        </>
      )}

      {/* ======== 选择题模式 ======== */}
      {mode === 'choice' && detail && (
        <>
          <Card>
            <p className="text-5xl font-bold text-slate-800 mb-2">{current.word}</p>
            <button onClick={() => speak(current.word)} className="text-xl mb-2">🔊</button>
            <p className="text-slate-400 mb-4">选出正确释义</p>
            <ChoiceOptions wordId={current.word_id} answered={answered} onPick={async (opt, correct) => {
              setAnswered({ ok: opt === correct, correct })
              await submit(opt === correct ? 5 : 2)
            }} />
          </Card>
          {answered && !answered.ok && (
            <p className="mt-4 text-center text-sm text-slate-600">
              正确答案：<b className="text-emerald-600">{answered.correct}</b>
            </p>
          )}
        </>
      )}

      {/* ======== 拼写模式 ======== */}
      {mode === 'spell' && detail && !spellResult && (
        <>
          <Card>
            <p className="text-lg text-slate-700 mb-1">{firstMeaning}</p>
            {firstPos && <p className="text-sm text-slate-400 mb-3">{firstPos}</p>}
            {detail.examples[0] && (
              <div className="bg-slate-50 rounded-lg p-3 text-sm mb-3">
                <p className="text-slate-700">{blankWord(detail.examples[0].en, current.word)}</p>
                <p className="text-slate-400">{detail.examples[0].zh}</p>
              </div>
            )}
            {hintLevel > 0 && (
              <p className="text-slate-500 font-mono">
                {hintWord(current.word, hintLevel)}
              </p>
            )}
            <input
              autoFocus
              className="w-full mt-3 rounded-lg border border-slate-200 px-4 py-3 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="拼写单词"
              value={spellInput}
              onChange={(e) => setSpellInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') checkSpell() }}
            />
          </Card>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button onClick={() => setHintLevel((h) => Math.min(h + 1, 2))}
              className="rounded-xl bg-slate-100 text-slate-600 font-semibold py-4">
              💡 提示
            </button>
            <button onClick={checkSpell} disabled={!spellInput.trim()}
              className="rounded-xl bg-blue-500 text-white font-semibold py-4 disabled:opacity-50">
              提交
            </button>
          </div>
        </>
      )}
      {mode === 'spell' && spellResult && (
        <>
          <Card>
            {spellResult.level === 'wrong' && (
              <p className="text-red-500 mb-2">你拼的：<s>{spellResult.answer}</s></p>
            )}
            <p className="text-4xl font-bold text-emerald-600 mb-2">{current.word}</p>
            {detail && <BackDetail detail={detail} word={current.word} />}
          </Card>
          <button onClick={() => submit(spellResult.level === 'perfect' ? 5 : spellResult.level === 'hinted' ? 3 : 1, spellResult.level === 'wrong' ? spellResult.answer : '')}
            className="mt-6 w-full rounded-xl bg-blue-500 text-white font-semibold py-4">
            下一个 →
          </button>
        </>
      )}
    </div>
  )

  function checkSpell() {
    const ok = norm(spellInput) === norm(current.word)
    setSpellResult({ level: ok ? (hintLevel > 0 ? 'hinted' : 'perfect') : 'wrong', answer: spellInput })
  }
}

function ChoiceOptions({ wordId, answered, onPick }: {
  wordId: string
  answered: null | { ok: boolean; correct: string }
  onPick: (opt: string, correct: string) => void
}) {
  const [quiz, setQuiz] = useState<{ options: string[]; correct: string } | null>(null)
  useEffect(() => {
    setQuiz(null)
    api.get(`/quiz/choice/${wordId}`).then((r) => setQuiz(r.data))
  }, [wordId])
  if (!quiz) return <p className="text-slate-400 py-4">出题中…</p>
  return (
    <div className="space-y-2 w-full">
      {quiz.options.map((opt) => {
        let cls = 'border-slate-200 bg-white hover:border-blue-400'
        if (answered) {
          if (opt === quiz.correct) cls = 'border-emerald-400 bg-emerald-50 text-emerald-700'
          else if (opt === answered.correct) cls = 'border-slate-200 bg-white opacity-50'
          else cls = 'border-slate-200 bg-white opacity-50'
        }
        return (
          <button key={opt} disabled={!!answered} onClick={() => onPick(opt, quiz.correct)}
            className={`w-full rounded-lg border px-4 py-3 text-left text-slate-700 transition ${cls}`}>
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function BackDetail({ detail, word }: { detail: WordRecord; word: string }) {
  return (
    <div className="text-left w-full space-y-3 max-h-[50vh] overflow-y-auto">
      <p className="text-3xl font-bold text-slate-800">{word}</p>
      {detail.meanings.map((m, i) => (
        <p key={i} className="text-lg text-slate-700">
          <span className="text-slate-400 mr-2">{m.pos}</span>{m.meaning}
        </p>
      ))}
      {detail.word_forms.length > 0 && (
        <p className="text-sm text-slate-500">词形：{detail.word_forms.map((f) => `${f.type}=${f.form}`).join('，')}</p>
      )}
      {detail.examples.slice(0, 2).map((ex, i) => (
        <div key={i} className="bg-slate-50 rounded-lg p-3">
          <p className="text-slate-700">{ex.en}</p>
          <p className="text-slate-400 text-sm">{ex.zh}</p>
        </div>
      ))}
      {detail.phrases.length > 0 && (
        <p className="text-sm text-slate-500">词组：{detail.phrases.map((p) => p.text).join('，')}</p>
      )}
      {detail.teaching_notes.map((t, i) => (
        <div key={i} className="bg-amber-50 rounded-lg p-3">
          <p className="text-sm font-semibold text-amber-700">👨‍🏫 名师点拨</p>
          <p className="text-sm text-amber-900 whitespace-pre-wrap">{t.content}</p>
        </div>
      ))}
    </div>
  )
}

function blankWord(en: string, word: string) {
  const re = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig')
  return en.replace(re, '______')
}

function hintWord(word: string, level: number) {
  if (level >= 2) return word[0] + ' ' + '_ '.repeat(word.length - 1) + `（共${word.length}字母）`
  return word[0] + '_'.repeat(word.length - 1) + `（共${word.length}字母）`
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 flex flex-col items-center justify-center min-h-[320px]">
      {children}
    </div>
  )
}

function GradeBtn({ color, label, onClick }: { color: 'red' | 'amber' | 'emerald'; label: string; onClick: () => void }) {
  const cls = {
    red: 'bg-red-100 hover:bg-red-200 text-red-700',
    amber: 'bg-amber-100 hover:bg-amber-200 text-amber-700',
    emerald: 'bg-emerald-100 hover:bg-emerald-200 text-emerald-700',
  }[color]
  return (
    <button onClick={onClick} className={`rounded-xl font-semibold py-4 transition ${cls}`}>
      {label}
    </button>
  )
}

function Center({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-slate-50 flex items-center justify-center">{children}</div>
}
