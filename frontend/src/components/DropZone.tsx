import { useRef, useState } from 'react'
import { IconUpload } from '@tabler/icons-react'
import { cn } from '@/lib/utils'

interface Props {
  onFile: (file: File) => void
  hint?: string
}

export function DropZone({ onFile, hint }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  function handle(file: File) {
    setFileName(file.name)
    onFile(file)
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border p-6 cursor-pointer transition-colors',
        dragging && 'border-primary bg-primary/5',
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) handle(file)
      }}
    >
      <IconUpload size={24} className="text-muted-foreground" />
      {fileName ? (
        <p className="text-sm font-medium text-foreground">{fileName}</p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Arrastrá un CSV o hacé click para seleccionar
        </p>
      )}
      {hint && (
        <p className="text-xs text-muted-foreground text-center font-mono bg-muted px-2 py-1 rounded">
          {hint}
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handle(file)
        }}
      />
    </div>
  )
}
