import Link from "next/link"

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  return (
    <div className="flex flex-col gap-4 p-6">
      <Link href="/" className="text-sm text-muted-foreground hover:underline">
        &larr; Back to library
      </Link>
      <p className="text-sm">Media item: {id}</p>
      <p className="text-xs text-muted-foreground">
        Item view will be implemented in T0010/T0011.
      </p>
    </div>
  )
}
