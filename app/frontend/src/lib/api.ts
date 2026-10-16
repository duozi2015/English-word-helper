import axios from 'axios'

const TOKEN_KEY = 'word_token'
const REFRESH_KEY = 'word_refresh_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setTokens(access: string, refresh?: string) {
  localStorage.setItem(TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export const api = axios.create({ baseURL: '/words/api' })

api.interceptors.request.use((cfg) => {
  const t = getToken()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearTokens()
      window.location.hash = '#/login'
    }
    return Promise.reject(err)
  },
)

// ---- 类型 ----
export interface WordBrief { word_id: string; word: string }
export interface Deck { due: WordBrief[]; new: WordBrief[] }
export interface Meaning { pos: string; meaning: string }
export interface Example { en: string; zh: string; type: string }
export interface WordForm { type: string; form: string; source: string }
export interface TeachingNote { type: string; title: string; content: string }
export interface WordRecord {
  id: string; word: string; phonetic: string
  meanings: Meaning[]; word_forms: WordForm[]
  related_words: { word: string; pos: string; meaning: string; relation: string }[]
  phrases: { text: string; meaning: string }[]
  proverbs: { text: string; meaning: string }[]
  examples: Example[]; usage_notes: string[]; teaching_notes: TeachingNote[]
  tags: string[]; exam_level: number
  textbook: { grade: string; semester: string; unit: string }[]
}
export interface ReviewOut {
  word_id: string; new_ef: number; new_interval: number
  new_rep_count: number; next_review_date: string
}
