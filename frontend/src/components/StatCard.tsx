interface Props {
  label: string
  value: string | number
  sub?: string
}

export function StatCard({ label, value, sub }: Props) {
  return (
    <div className="bg-white border border-[#e8eaed] rounded-xl p-4">
      <p className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px] mb-1.5">
        {label}
      </p>
      <p className="text-2xl font-bold text-[#1a1a2e] leading-none">{value}</p>
      {sub && <p className="text-[12px] text-[#9aa0ac] mt-1.5">{sub}</p>}
    </div>
  )
}
