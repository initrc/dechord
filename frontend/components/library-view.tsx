"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { api, type MediaListItem } from "@/lib/api"
import { useJobPoller } from "@/hooks/use-job-poller"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const TERMINAL = new Set(["done", "failed"])

function MediaRow({
  item,
  jobId: initialJobId,
  onJobComplete,
}: {
  item: MediaListItem
  jobId: string | null
  onJobComplete: () => void
}) {
  const [activeJobId, setActiveJobId] = useState<string | null>(initialJobId)
  const { status, error } = useJobPoller(activeJobId)
  const prevStatusRef = useRef<string | null>(null)

  useEffect(() => {
    const prev = prevStatusRef.current
    if (
      prev !== null &&
      !TERMINAL.has(prev) &&
      status !== null &&
      TERMINAL.has(status)
    ) {
      onJobComplete()
    }
    prevStatusRef.current = status
  }, [status, onJobComplete])

  const router = useRouter()
  const displayStatus = status ?? item.status

  async function handleRerun(e: React.MouseEvent) {
    e.stopPropagation()
    try {
      const res = await api.rerunChords(item.id)
      setActiveJobId(res.job_id)
    } catch {
      // surfaced on next list refresh
    }
  }

  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => router.push(`/media/${item.id}`)}
    >
      <TableCell>{item.original_filename}</TableCell>
      <TableCell>
        {displayStatus}
        {error && <span className="ml-1 text-destructive">({error})</span>}
      </TableCell>
      <TableCell>{item.has_chords ? "true" : "false"}</TableCell>
      <TableCell>
        <Button variant="outline" size="xs" onClick={handleRerun}>
          Re-run recognition
        </Button>
      </TableCell>
    </TableRow>
  )
}

export function LibraryView() {
  const [items, setItems] = useState<MediaListItem[]>([])
  const [mediaToJobIds, setMediaToJobIds] = useState<Record<string, string | null>>({})
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const initRef = useRef(false)

  async function refresh() {
    try {
      const list = await api.listMedia()
      setItems(list)
    } catch {
      // list fetch failure is non-fatal
    }
  }

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true
    refresh()
  }, [])

  async function handleUpload() {
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const res = await api.uploadMedia(file)
      if (res.job_id) {
        setMediaToJobIds((prev) => ({ ...prev, [res.id]: res.job_id! }))
      }
      await refresh()
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  function handleJobComplete() {
    refresh()
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <Input
          ref={fileRef}
          type="file"
          accept=".mp3,.wav,.flac,.m4a"
          className="max-w-xs"
        />
        <Button onClick={handleUpload} disabled={uploading}>
          {uploading ? "Uploading..." : "Upload"}
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Has chords</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <MediaRow
              key={item.id}
              item={item}
              jobId={mediaToJobIds[item.id] ?? null}
              onJobComplete={handleJobComplete}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
