import * as React from "react";
import { Role, ROLE_LABELS } from "./types";
import { Badge } from "./ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { ChevronDown, LogOut, Printer, Send } from "lucide-react";

type View = "dashboard" | "queue";

type Props = {
  view: View;
  setView: (v: View) => void;
  role: Role;
  setRole: (r: Role) => void;
  isSuperAdmin: boolean;
  currentUser: string;
  pendingCount: number;
  onLogout: () => void;
};

export function TopNavbar({ view, setView, role, setRole, isSuperAdmin, currentUser, pendingCount, onLogout }: Props) {
  const NavLink = ({ id, label, icon, badge }: { id: View; label: string; icon: React.ReactNode; badge?: number }) => {
    const active = view === id;
    return (
      <button
        onClick={() => setView(id)}
        className={`relative flex items-center gap-2 px-4 h-10 rounded-md transition ${
          active ? "bg-white/10 text-white" : "text-white/70 hover:text-white hover:bg-white/5"
        }`}
      >
        {icon}
        <span>{label}</span>
        {badge && badge > 0 ? (
          <span className="ml-1 min-w-5 h-5 px-1.5 rounded-full bg-[var(--brand-red)] text-white flex items-center justify-center" style={{ fontSize: "0.7rem", fontWeight: 700 }}>
            {badge}
          </span>
        ) : null}
        {active && <span className="absolute left-2 right-2 -bottom-px h-0.5 bg-[var(--brand-red)] rounded-full" />}
      </button>
    );
  };

  return (
    <header className="sticky top-0 z-30 bg-[var(--brand-blue)] text-white border-b-2 border-[var(--brand-red)]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-white text-[var(--brand-blue)] flex items-center justify-center" style={{ fontWeight: 700 }}>IA</div>
          <div className="hidden md:block">
            <p style={{ fontSize: "0.875rem", fontWeight: 700, letterSpacing: "0.05em" }}>INSTITUTO ACALANTO DE ENSINO</p>
            <p className="opacity-70" style={{ fontSize: "0.7rem" }}>Portal de Impressão</p>
          </div>
        </div>

        <nav className="flex items-center gap-1 ml-4">
          <NavLink id="dashboard" label="Enviar Impressão" icon={<Send size={16} />} />
          <NavLink id="queue" label="Fila de Impressão" icon={<Printer size={16} />} badge={pendingCount} />
        </nav>

        <div className="flex-1" />

        <div className="hidden md:flex items-center gap-3">
          <Badge className="bg-[var(--brand-amber)] text-slate-900 hover:bg-[var(--brand-amber)]" style={{ fontWeight: 600 }}>
            {ROLE_LABELS[role]}
          </Badge>

          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center gap-2 h-10 px-3 rounded-md text-white hover:bg-white/10 transition outline-none">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center" style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                {currentUser.split(" ").map((p) => p[0]).slice(0, 2).join("")}
              </div>
              <span>{currentUser}</span>
              <ChevronDown size={14} />
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {/* Só o Admin (super_admin no banco de dados) vê e usa isso —
                  e continua vendo nos dois modos, já que depende de
                  isSuperAdmin e não do "role" que está sendo visualizado. */}
              {isSuperAdmin && (
                <>
                  <DropdownMenuLabel>Trocar Perfil (Admin)</DropdownMenuLabel>
                  <DropdownMenuItem onClick={() => setRole("COORDENADOR")}>
                    Coordenador de Área
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setRole("TI")}>
                    Departamento de T.I.
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem onClick={onLogout} className="text-red-600 font-medium">
                <LogOut className="mr-2 h-4 w-4" />
                <span>Sair</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
