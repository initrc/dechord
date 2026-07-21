import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { api, type MediaDetailResponse } from "@/lib/api"
import { toDisplayChords } from "@/lib/chords"
import { ItemView } from "@/components/item-view"

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  let media: MediaDetailResponse | null = null
  let error: string | null = null
  try {
    media = await api.getMedia(id)
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load media"
  }

  if (error || !media) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Link href="/" className="text-sm text-muted-foreground hover:underline">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <p className="text-sm text-destructive">{error ?? "Media not found"}</p>
      </div>
    )
  }

  const displayChords = toDisplayChords(media.chords)
  const title = media.original_filename.replace(/\.[^.]+$/, "")

  return (
    <div className="flex justify-center px-2 sm:px-6 py-6">
      <div className="flex flex-col items-center gap-8 overflow-x-auto max-w-full">
        <div className="flex w-full items-center gap-2">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="flex-1 text-center text-lg font-semibold pr-5">{title}</h1>
        </div>
        <ItemView
          mediaId={media.id}
          duration={media.audio.duration}
          chords={displayChords}
        />
      </div>
    </div>
  )
}
