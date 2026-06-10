import { NavLink } from 'react-router-dom'
import {
  IconLeaf,
  IconTimeline,
  IconFence,
  IconTrendingUp,
  IconCloudUpload,
} from '@tabler/icons-react'
import { cn } from '@/lib/utils'

const nav = [
  { to: '/history', icon: IconTimeline, label: 'Historial animal' },
  { to: '/lot',     icon: IconFence,    label: 'Estado de lote' },
  { to: '/adg',     icon: IconTrendingUp, label: 'ADPV' },
  { to: '/upload',  icon: IconCloudUpload, label: 'Carga de datos' },
]

export function Sidebar() {
  return (
    <aside className="w-[220px] shrink-0 bg-white border-r border-[#e8eaed] flex flex-col h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-[#e8eaed] shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#2e7d32] to-[#66bb6a] flex items-center justify-center shrink-0">
          <IconLeaf size={18} className="text-white" stroke={2} />
        </div>
        <span className="text-[15px] font-semibold text-[#1a1a2e]">FieldData</span>
      </div>

      {/* Nav */}
      <div className="flex-1 px-2 py-3">
        <p className="text-[10px] font-semibold text-[#9aa0ac] uppercase tracking-[0.8px] px-2 mb-1.5">
          Trazabilidad
        </p>
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-colors',
                isActive
                  ? 'bg-[#eff6ff] text-[#2563eb] font-semibold'
                  : 'text-[#555] hover:bg-[#f0f4ff] hover:text-[#2563eb]',
              )
            }
          >
            <Icon size={17} stroke={1.8} />
            {label}
          </NavLink>
        ))}
      </div>
    </aside>
  )
}
