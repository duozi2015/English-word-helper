/** WebAudio 合成音效（零外部资源）。 */

let ctx: AudioContext | null = null

function audio(): AudioContext {
  if (!ctx) ctx = new AudioContext()
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

const MUTE_KEY = 'word_sfx_mute'
export function isMuted(): boolean {
  return localStorage.getItem(MUTE_KEY) === '1'
}
export function toggleMuted(): boolean {
  const m = !isMuted()
  localStorage.setItem(MUTE_KEY, m ? '1' : '0')
  return m
}

function tone(freq: number, start: number, dur: number, type: OscillatorType = 'sine', gain = 0.12) {
  const a = audio()
  const osc = a.createOscillator()
  const g = a.createGain()
  osc.type = type
  osc.frequency.value = freq
  g.gain.setValueAtTime(gain, a.currentTime + start)
  g.gain.exponentialRampToValueAtTime(0.001, a.currentTime + start + dur)
  osc.connect(g).connect(a.destination)
  osc.start(a.currentTime + start)
  osc.stop(a.currentTime + start + dur)
}

/** 答对：上行双音 */
export function sfxCorrect() {
  if (isMuted()) return
  tone(523.25, 0, 0.12)
  tone(783.99, 0.1, 0.2)
}

/** 答错：下行短促 */
export function sfxWrong() {
  if (isMuted()) return
  tone(220, 0, 0.15, 'square', 0.06)
  tone(174.61, 0.12, 0.25, 'square', 0.06)
}

/** 翻卡：轻扫 */
export function sfxFlip() {
  if (isMuted()) return
  tone(880, 0, 0.06, 'triangle', 0.05)
  tone(1174.66, 0.05, 0.08, 'triangle', 0.04)
}

/** 连击升级：琶音 */
export function sfxCombo(level: number) {
  if (isMuted()) return
  const base = 523.25 * Math.pow(2, Math.min(level, 5) / 12)
  tone(base, 0, 0.1)
  tone(base * 1.25, 0.08, 0.1)
  tone(base * 1.5, 0.16, 0.18)
}

/** 完成：小 fanfare */
export function sfxDone() {
  if (isMuted()) return
  tone(523.25, 0, 0.15)
  tone(659.25, 0.15, 0.15)
  tone(783.99, 0.3, 0.15)
  tone(1046.5, 0.45, 0.4)
}
