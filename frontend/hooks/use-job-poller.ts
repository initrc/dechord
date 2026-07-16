"use client"

import { useEffect, useState } from "react"
import { api, type JobResponse } from "@/lib/api"

const POLL_INTERVAL = 1500
const TERMINAL = new Set(["done", "failed"])

export function useJobPoller(jobId: string | null) {
  const [job, setJob] = useState<JobResponse | null>(null)

  useEffect(() => {
    if (!jobId) return

    let stopped = false

    async function poll() {
      if (stopped) return
      try {
        const res = await api.getJob(jobId!)
        if (stopped) return
        setJob(res)
        if (!TERMINAL.has(res.status)) {
          setTimeout(poll, POLL_INTERVAL)
        }
      } catch {
        stopped = true
      }
    }

    poll()

    return () => {
      stopped = true
    }
  }, [jobId])

  return {
    status: job?.status ?? null,
    progress: job?.progress ?? 0,
    error: job?.error ?? null,
  }
}
