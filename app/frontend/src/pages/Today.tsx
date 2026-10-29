import { useEffect, useMemo, useRef, useState } from 'react'
import { api, type WordRecord, type ReviewOut } from '../lib/api'
import { sfxCombo, sfxCorrect, sfxDone, sfxFlip, sfxWrong, toggleMuted } from '../lib/sfx'

type Stage = 'card' | 'choice' | 'spell'
type WordBrief = { word_id: string; word: string; phonetic: string }
type SpellLevel = 'perfect' | 'hinted' | 'wrong'

const STAGES: Stage[] = ['card', 'choice', 'spell']
const STAGE_LABEL: Record<Stage, string> = { card: '🃏 翻卡', choice: '✅ 选择', spell: '⌨️ 拼写' }
const NEXT: Record<Stage, Stage> = { card: 'choice', choice: 'spell', spell: 'card' }

export default function Today() {
  const [queue, setQueue] = useState<WordBrief[]>([])
  const [stage, setStage] = useState<Stage>('card')
  const [idx, setIdx] = useState(0)
  const [over, setOver] = useState<null | 'stage' | 'all'>(null) // 阶段完成/全部完成遮罩
  const [detail, setDetail] = useState<WordRecord | null>(null)
  const [flipped, setFlipped] = useState(false)
  const [combo, setCombo] = useState(0)
  const [maxCombo, setMaxCombo] = useState(0)
  const [muted, setMuted] = useState(false)
  const [answered, setAnswered] = useState<null | { ok: boolean; correct: string }>(null)
  const [spellInput, setSpellInput] = useState('')
  const [hintLevel, setHintLevel] = useState(0)
  const [spellResult, setSpellResult] = useState<null | { level: SpellLevel; answer: string }>(null)
  const [subQs, setSubQs] = useState<SpellQ[]>([])
  const [subIdx, setSubIdx] = useState(0)
  const [subResults, setSubResults] = useState<boolean[]>([])
  const comboRef = useRef(0)

  const current = queue[idx]
  const q = subQs[subIdx]

  useEffect(() => {
    api.get<{ due: WordBrief[]; new: WordBrief[] }>('/deck/today').then((r) => {
      const q = [...r.data.due, ...r.data.new]
      setQueue(q)
      if (q.length) loadDetail(q[0].word_id)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 单词一出现立即朗读（每阶段每题）
  useEffect(() => {
    if (current && !over) speak(current.word)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, idx])

  // 进入拼写阶段后，为当前词生成小题（单词/时态/搭配）
  useEffect(() => {
    if (stage === 'spell' && detail) {
      setSubQs(buildSpellQuestions(detail))
      setSubIdx(0)
      setSubResults([])
    }
  }, [stage, idx, detail])

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
    setFlipped(false)
    setSubQs([])
    setSubIdx(0)
    setSubResults([])
  }

  const advance = async (quality: 1 | 2 | 3 | 5, wrong = '') => {
    if (!current) return
    await api.post<ReviewOut>('/review', {
      word_id: current.word_id, mode: stage, quality, wrong_answer: wrong || undefined,
    })
    if (quality >= 3) {
      comboRef.current += 1
      setCombo(comboRef.current)
      setMaxCombo((m) => Math.max(m, comboRef.current))
      sfxCorrect()
      if (comboRef.current >= 3) sfxCombo(comboRef.current)
    } else {
      comboRef.current = 0
      setCombo(0)
      sfxWrong()
    }
    if (idx + 1 >= queue.length) {
      // 本阶段完成；拼写是最后一关 → 烟花
      sfxDone()
      setOver(stage === 'spell' ? 'all' : 'stage')
    } else {
      setIdx(idx + 1)
      resetItemState()
      loadDetail(queue[idx + 1].word_id)
    }
  }

  const gotoNextStage = () => {
    const next = NEXT[stage]
    setOver(null) // 先清遮罩，再切阶段
    setStage(next)
    setIdx(0)
    resetItemState()
    loadDetail(queue[0].word_id)
  }

  const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ')

  const checkSpell = () => {
    if (!q) return
    const ok = norm(spellInput) === norm(q.answer)
    setSubResults((r) => { const n = [...r]; n[subIdx] = ok; return n })
    setSpellResult({ level: ok ? (hintLevel > 0 ? 'hinted' : 'perfect') : 'wrong', answer: spellInput })
  }

  const nextSpellQ = () => {
    if (subIdx + 1 < subQs.length) {
      setSubIdx(subIdx + 1)
      setSpellInput('')
      setHintLevel(0)
      setSpellResult(null)
    } else {
      // 本词全部小题完成 → 一次 SM-2 提交（全对5 / 有对3 / 全错1）
      const allOk = subResults.length > 0 && subResults.every(Boolean)
      const anyOk = subResults.some(Boolean)
      const quality = (allOk ? 5 : anyOk ? 3 : 1) as 1 | 3 | 5
      const wrongQ = subQs.find((_, i) => subResults[i] === false)
      advance(quality, wrongQ ? spellResult?.answer ?? '' : '')
    }
  }

  // ---------- 遮罩视图 ----------
  if (over === 'stage')
    return (
      <Center>
        <Confetti />
        <div className="bg-white rounded-2xl shadow p-10 text-center space-y-3 relative z-10">
          <p className="text-6xl anim-bounce-in">{stage === 'card' ? '🃏' : stage === 'choice' ? '✅' : '⌨️'}</p>
          <p className="text-2xl font-bold text-slate-800 anim-slide-up">{STAGE_LABEL[stage].slice(2)}阶段完成！</p>
          <p className="text-slate-400 text-sm anim-slide-up">即将进入{STAGE_LABEL[NEXT[stage]].slice(2)}阶段…</p>
        </div>
        <AutoAdvance onDone={gotoNextStage} ms={2200} />
      </Center>
    )

  if (over === 'all')
    return (
      <Center>
        <Fireworks />
        <div className="bg-white rounded-2xl shadow p-10 text-center space-y-3 relative z-10">
          <p className="text-6xl anim-bounce-in">🎆</p>
          <p className="text-2xl font-bold text-slate-800 anim-slide-up">三阶段全部完成！</p>
          <p className="text-slate-500 anim-slide-up">
            共 {queue.length} 词 · 最高连击 <span className="text-orange-500 font-bold">🔥×{maxCombo}</span>
          </p>
          <p className="text-slate-400 text-sm anim-slide-up">明天记得回来复习哦～</p>
        </div>
        <AutoAdvance onDone={() => setOver(null)} ms={6000} />
      </Center>
    )

  if (!queue.length)
    return <Center><p className="text-slate-400">今天没有待学习的单词，休息一下吧 🌿</p></Center>


  return (
    <div className="max-w-md mx-auto px-4 py-6">
      {/* 顶栏：阶段指示 + 连击 + 静音 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1">
          {STAGES.map((s) => {
            const done = STAGES.indexOf(s) < STAGES.indexOf(stage)
            const active = s === stage
            return (
              <span key={s}
                className={`text-xs px-2 py-1 rounded-full ${
                  active ? 'bg-blue-500 text-white' :
                  done ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                {done ? '✓ ' : ''}{STAGE_LABEL[s]}
              </span>
            )
          })}
        </div>
        <div className="flex items-center gap-2">
          <div className="h-6">
            {combo >= 2 && <span className="anim-flame inline-block text-orange-500 font-bold">🔥×{combo}</span>}
          </div>
          <button onClick={() => setMuted(toggleMuted())} className="text-lg px-1" title="音效开关">
            {muted ? '🔇' : '🔈'}
          </button>
        </div>
      </div>

      {/* 阶段内进度 */}
      <div className="flex items-center gap-2 mb-6">
        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-300"
               style={{ width: `${(idx / queue.length) * 100}%` }} />
        </div>
        <span className="text-sm text-slate-400">{idx + 1}/{queue.length}</span>
      </div>

      {/* ======== 阶段一：翻卡 ======== */}
      {stage === 'card' && (
        <>
          <Card key={`c-${idx}`} className="anim-slide-up">
            {!flipped ? (
              <div className="text-center">
                <p className="text-6xl font-bold text-slate-800 mb-1">{current.word}</p>
                {current.phonetic && <p className="text-slate-400 mb-3">/{current.phonetic}/</p>}
                <button onClick={() => speak(current.word)} className="text-2xl anim-pop" title="再听一次">🔊</button>
                <p className="mt-6 text-slate-400 text-sm">
                  {(detail?.exam_level ?? 0) > 0 ? `★${detail?.exam_level} 高频词` : '大纲词'}
                  {detail?.textbook[0] && ` · ${detail.textbook[0].grade}${detail.textbook[0].semester}U${detail.textbook[0].unit}`}
                </p>
              </div>
            ) : (
              <div className="text-left w-full anim-slide-up">
                {detail && <BackDetail detail={detail} word={current.word} />}
              </div>
            )}
          </Card>
          {!flipped ? (
            <button onClick={() => { sfxFlip(); setFlipped(true) }}
              className="mt-6 w-full rounded-lg border border-slate-300 bg-white px-6 py-2 text-slate-600 hover:bg-slate-50 transition">
              翻转卡片
            </button>
          ) : (
            <div className="mt-6 grid grid-cols-3 gap-3">
              <GradeBtn color="red" label="😵 不认识" onClick={() => advance(1)} />
              <GradeBtn color="amber" label="🤔 模糊" onClick={() => advance(3)} />
              <GradeBtn color="emerald" label="😄 认识" onClick={() => advance(5)} />
            </div>
          )}
        </>
      )}

      {/* ======== 阶段二：选择 ======== */}
      {stage === 'choice' && (
        <Card key={`q-${idx}`} className="anim-slide-up">
          <p className="text-5xl font-bold text-slate-800 mb-1">{current.word}</p>
          {current.phonetic && <p className="text-slate-400 mb-2">/{current.phonetic}/</p>}
          <button onClick={() => speak(current.word)} className="text-xl mb-2" title="再听一次">🔊</button>
          <p className="text-slate-400 mb-4">选出正确释义</p>
          <ChoiceOptions wordId={current.word_id} answered={answered} onPick={(opt, correct) => {
            setAnswered({ ok: opt === correct, correct })
            setTimeout(() => advance(opt === correct ? 5 : 2), 700)
          }} />
          {answered && !answered.ok && (
            <p className="mt-4 text-center text-sm text-slate-600 anim-slide-up">
              正确答案：<b className="text-emerald-600">{answered.correct}</b>
            </p>
          )}
        </Card>
      )}

      {/* ======== 阶段三：拼写（一词多题：单词/时态/搭配） ======== */}
      {stage === 'spell' && !spellResult && (
        <Card key={`s-${idx}-${subIdx}`} className="anim-slide-up">
          <p className="text-xs text-slate-400 mb-2">
            {q?.kind === 'word' ? '① 单词拼写' : q?.kind === 'form' ? '② 词形变化' : '③ 常用搭配'}
          </p>
          {q?.kind === 'form' && (
            <p className="text-2xl font-bold text-slate-800 mb-1">「{q.base}」的{q.formCn}</p>
          )}
          {q?.kind === 'phrase' && (
            <p className="text-xl font-semibold text-slate-800 mb-1">
              词组：{q.prompt}
              <span className="text-sm text-slate-400 ml-2">（{q.answer.split(/\s+/).length} 个单词）</span>
            </p>
          )}
          {q?.kind === 'word' && (
            <>
              <p className="text-lg text-slate-700 mb-1">{q.prompt}</p>
              {q.pos && <p className="text-sm text-slate-400 mb-3">{q.pos}</p>}
            </>
          )}
          {q?.sentence && (
            <div className="bg-slate-50 rounded-lg p-3 text-sm mb-3">
              <p className="text-slate-700">{q.sentence}</p>
              {q.sentenceZh && <p className="text-slate-400">{q.sentenceZh}</p>}
            </div>
          )}
          {q?.kind === 'word' && (
            <p className="text-slate-400 text-sm mb-2">
              例句中已出现 <b className="text-slate-600">{q.tenseHint}</b> 形式，请按句子时态拼写
            </p>
          )}
          {hintLevel > 0 && q && <p className="text-slate-500 font-mono anim-slide-up">{hintWord(q.answer, hintLevel)}</p>}
          <input
            autoFocus
            className="w-full mt-3 rounded-lg border border-slate-200 px-4 py-3 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="输入英文"
            value={spellInput}
            onChange={(e) => setSpellInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') checkSpell() }}
          />
          {q?.kind === 'word' && subIdx === 0 && (
            <p className="text-xs text-slate-300 mt-2">随后还有词形变化 / 常用搭配小题</p>
          )}
        </Card>
      )}
      {stage === 'spell' && spellResult && q && (
        <>
          <Card key={`sr-${idx}-${subIdx}`} className={`anim-slide-up ${spellResult.level === 'wrong' ? 'anim-shake' : ''}`}>
            {spellResult.level === 'wrong' && <p className="text-red-500 mb-2">你写的：<s>{spellResult.answer}</s></p>}
            <p className={`text-3xl font-bold mb-2 ${spellResult.level === 'wrong' ? 'text-slate-700' : 'text-emerald-600 anim-bounce-in'}`}>
              {q.answer}
            </p>
            {q.kind === 'form' && <p className="text-sm text-slate-400 mb-2">「{q.base}」的{q.formCn}</p>}
            {q.kind === 'word' && detail && <BackDetail detail={detail} word={current.word} />}
          </Card>
          <button onClick={nextSpellQ}
            className="mt-6 w-full rounded-xl bg-blue-500 text-white font-semibold py-4 hover:bg-blue-600 transition">
            {subIdx + 1 < subQs.length ? '下一小题 →' : '完成本词 →'}
          </button>
        </>
      )}

      {/* ======== 拼写操作 ======== */}
      {stage === 'spell' && !spellResult && q && (
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button onClick={() => { sfxFlip(); setHintLevel((h) => Math.min(h + 1, 2)) }}
            className="rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 font-semibold py-4 transition">
            💡 提示
          </button>
          <button onClick={checkSpell} disabled={!spellInput.trim()}
            className="rounded-xl bg-blue-500 text-white font-semibold py-4 disabled:opacity-50 hover:bg-blue-600 transition">
            提交
          </button>
        </div>
      )}
    </div>
  )
}

/** 阶段遮罩自动跳转 */
function AutoAdvance({ onDone, ms }: { onDone: () => void; ms: number }) {
  useEffect(() => {
    const t = setTimeout(onDone, ms)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

/** 彩带雨（阶段完成） */
function Confetti() {
  const pieces = useMemo(
    () => Array.from({ length: 24 }, (_, i) => ({
      left: `${(i * 37) % 100}%`,
      delay: `${(i % 8) * 0.12}s`,
      dur: `${1.4 + (i % 5) * 0.25}s`,
      emoji: ['🎉', '⭐', '✨', '🎊', '🌟'][i % 5],
      size: `${16 + (i % 3) * 8}px`,
    })),
    [],
  )
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {pieces.map((p, i) => (
        <span key={i} className="absolute anim-fall"
              style={{ left: p.left, animationDelay: p.delay, animationDuration: p.dur, fontSize: p.size }}>
          {p.emoji}
        </span>
      ))}
    </div>
  )
}

/** 烟花（全部完成）：多点径向绽放，循环 */
function Fireworks() {
  const bursts = useMemo(
    () => Array.from({ length: 10 }, (_, i) => ({
      left: `${8 + ((i * 23) % 84)}%`,
      top: `${10 + ((i * 37) % 55)}%`,
      delay: `${(i % 5) * 0.45}s`,
      emoji: ['🎆', '💥', '✨', '🎇'][i % 4],
      size: `${30 + (i % 4) * 12}px`,
    })),
    [],
  )
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {bursts.map((b, i) => (
        <span key={i} className="absolute anim-burst"
              style={{ left: b.left, top: b.top, animationDelay: b.delay, fontSize: b.size }}>
          {b.emoji}
        </span>
      ))}
    </div>
  )
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
      {quiz.options.map((opt, i) => {
        let cls = 'border-slate-200 bg-white hover:border-blue-400 hover:shadow-sm'
        if (answered) {
          if (opt === quiz.correct) cls = 'border-emerald-400 bg-emerald-50 text-emerald-700 anim-pop'
          else cls = 'border-slate-200 bg-white opacity-50'
        }
        return (
          <button key={opt} disabled={!!answered} onClick={() => onPick(opt, quiz.correct)}
            className={`w-full rounded-lg border px-4 py-3 text-left text-slate-700 transition anim-slide-up ${cls}`}
            style={{ animationDelay: `${i * 0.06}s` }}>
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function BackDetail({ detail, word }: { detail: WordRecord; word: string }) {
  return (
    <div className="space-y-3 max-h-[50vh] overflow-y-auto">
      <p className="text-3xl font-bold text-slate-800">{word}</p>
      {detail.phonetic && <p className="text-slate-400 mb-2">/{detail.phonetic}/</p>}
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

function hintWord(word: string, level: number) {
  if (level >= 2) return word[0] + ' ' + '_ '.repeat(word.length - 1) + `（共${word.length}字母）`
  return word[0] + '_'.repeat(word.length - 1) + `（共${word.length}字母）`
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-2xl shadow-lg p-8 flex flex-col items-center justify-center min-h-[320px] ${className}`}>
      {children}
    </div>
  )
}

function GradeBtn({ color, label, onClick }: { color: 'red' | 'amber' | 'emerald'; label: string; onClick: () => void }) {
  const cls = {
    red: 'bg-red-100 hover:bg-red-200 text-red-700 active:scale-95',
    amber: 'bg-amber-100 hover:bg-amber-200 text-amber-700 active:scale-95',
    emerald: 'bg-emerald-100 hover:bg-emerald-200 text-emerald-700 active:scale-95',
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


// ==================== 拼写小题生成（单词/时态/搭配） ====================

type SpellQ = {
  kind: 'word' | 'form' | 'phrase'
  prompt: string
  pos?: string
  sentence?: string
  sentenceZh?: string
  tenseHint?: string
  answer: string
  base?: string
  formCn?: string
}

const FORM_CN: Record<string, string> = {
  plural: '复数', third_person: '第三人称单数', past: '过去式',
  past_participle: '过去分词', present_participle: '现在分词',
  comparative: '比较级', superlative: '最高级',
}

/** 在例句里找单词的某个时态/词形变体，返回 {blanked, form}；找不到返回 null。 */
function findOccurrence(en: string, word: string, forms: string[]): { blanked: string; form: string } | null {
  const cands = [
    word,
    ...forms.filter((f) => /^[A-Za-z'-]+$/.test(f)),
    word + 's', word + 'es', word + 'ed', word + 'd', word + 'ing',
  ]
  for (const c of cands) {
    if (c.length < 2) continue
    const re = new RegExp(`\\b${c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i')
    const m = en.match(re)
    if (m) {
      return { blanked: en.replace(re, '______'), form: m[0] }
    }
  }
  return null
}

function buildSpellQuestions(rec: WordRecord): SpellQ[] {
  const qs: SpellQ[] = []
  const meaning = rec.meanings.map((m) => `${m.pos} ${m.meaning}`.trim()).join('；')
  // ① 单词拼写：例句挖空（优先匹配时态形式）
  let wordQ: SpellQ = { kind: 'word', prompt: meaning || rec.word, answer: rec.word }
  for (const ex of rec.examples) {
    const hit = findOccurrence(ex.en, rec.word, rec.word_forms.map((f) => f.form))
    if (hit) {
      wordQ = {
        kind: 'word', prompt: meaning || rec.word,
        pos: rec.meanings[0]?.pos,
        sentence: hit.blanked, sentenceZh: ex.zh,
        tenseHint: hit.form.toLowerCase() === rec.word.toLowerCase() ? '原形' : '时态变化',
        answer: hit.form,
      }
      break
    }
  }
  qs.push(wordQ)
  // ②③ 各随机挑一：词形变化 / 常用搭配
  const cleanForms = rec.word_forms.filter((f) => /^[A-Za-z'-]+$/.test(f.form) && f.form.toLowerCase() !== rec.word.toLowerCase())
  const extras: SpellQ[] = []
  if (cleanForms.length) {
    const f = cleanForms[Math.floor(Math.random() * cleanForms.length)]
    extras.push({ kind: 'form', prompt: '', base: rec.word, formCn: FORM_CN[f.type] ?? f.type, answer: f.form })
  }
  if (rec.phrases.length) {
    const ph = rec.phrases[Math.floor(Math.random() * rec.phrases.length)]
    extras.push({
      kind: 'phrase',
      prompt: ph.meaning || `与 "${rec.word}" 搭配的常用词组`,
      answer: ph.text,
    })
  }
  if (extras.length) qs.push(extras[Math.floor(Math.random() * extras.length)])
  return qs
}
