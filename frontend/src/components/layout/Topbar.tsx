interface Props {
  title: string
  actions?: React.ReactNode
}

export function Topbar({ title, actions }: Props) {
  return (
    <div className="bg-white border-b border-[#e8eaed] px-6 h-14 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-[#2563eb]" />
        <span className="text-[15px] font-semibold text-[#1a1a2e]">{title}</span>
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}
