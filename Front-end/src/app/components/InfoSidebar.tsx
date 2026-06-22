import { Card } from "./ui/card";
import { AlertTriangle, Clock, FileText } from "lucide-react";

export function InfoSidebar() {
  return (
    <div className="space-y-5">
      <Card className="p-6 border-[var(--brand-border)] shadow-sm">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 text-[var(--brand-amber)] flex items-center justify-center shrink-0">
            <AlertTriangle size={20} />
          </div>
          <div>
            <p style={{ fontWeight: 600, color: "#0f172a" }}>Suporte Técnico</p>
            <p className="text-slate-600 mt-1" style={{ fontSize: "0.9rem", lineHeight: 1.5 }}>
              Quaisquer dúvidas referentes à plataforma, entre em contato com o
              Departamento de T.I (Ramal <span style={{ fontWeight: 600 }}>1113</span>).
            </p>
          </div>
        </div>
      </Card>

      <Card className="p-6 bg-[var(--brand-blue)] text-white border-0 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-white/5 -translate-y-12 translate-x-12" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <Clock size={20} />
            <p style={{ fontWeight: 600 }}>Horário de Funcionamento</p>
          </div>
          <p className="mt-3 opacity-90" style={{ lineHeight: 1.5 }}>
            Segunda a Sexta-feira
            <br />
            <span style={{ fontSize: "1.25rem", fontWeight: 700 }}>07:00 às 19:00</span>
          </p>

          <div className="h-px bg-white/20 my-5" />

          <div className="flex items-start gap-2">
            <FileText size={16} className="mt-0.5 shrink-0" />
            <p className="opacity-90" style={{ fontSize: "0.85rem", lineHeight: 1.5 }}>
              <span style={{ fontWeight: 600 }}>Restrição:</span> é permitido apenas o
              envio de documentos salvos em PDF.
            </p>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[var(--brand-red)]" />
      </Card>
    </div>
  );
}
