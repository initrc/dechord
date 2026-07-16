const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
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

  getJob: (id: string) => api.get<JobResponse>(`/jobs/${id}`),

  rerunChords: (mediaId: string) =>
    api.post<JobIdResponse>(`/media/${mediaId}/chords`),
}
