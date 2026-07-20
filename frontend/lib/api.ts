const API_BASE_URL = process.env.API_BASE_URL ?? "/api"

function getBaseUrl(): string {
  // Client-side: relative URLs work because the browser resolves them
  if (typeof window !== "undefined") {
    return API_BASE_URL
  }
  // Server-side with absolute URL: use as-is
  if (API_BASE_URL.startsWith("http")) {
    return API_BASE_URL
  }
  // Server-side with relative URL: construct absolute URL for fetch()
  const host = process.env.HOST ?? "localhost"
  const port = process.env.PORT ?? "3000"
  return `http://${host}:${port}${API_BASE_URL}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, init)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export type MediaListItem = {
  id: string
  original_filename: string
  uploaded_at: string
  status: string
  has_chords: boolean
}

export type MediaIdResponse = {
  id: string
  job_id?: string
}

export type JobResponse = {
  status: string
  progress: number
  media_id: string
  error: string | null
}

export type ChordSegment = {
  start: number
  end: number
  label: string
}

export type MediaDetailResponse = {
  id: string
  original_filename: string
  status: string
  audio: {
    sample_rate: number
    duration: number
    source_path: string
  }
  chords: ChordSegment[]
}

export type JobIdResponse = {
  job_id: string
}

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, body?: BodyInit) =>
    request<T>(path, { method: "POST", body }),

  uploadMedia(file: File) {
    const form = new FormData()
    form.append("file", file)
    return api.post<MediaIdResponse>("/media", form)
  },

  listMedia: () => api.get<MediaListItem[]>("/media"),

  getMedia: (id: string) => api.get<MediaDetailResponse>(`/media/${id}`),

  getJob: (id: string) => api.get<JobResponse>(`/jobs/${id}`),

  rerunChords: (mediaId: string) =>
    api.post<JobIdResponse>(`/media/${mediaId}/chords`),
}
