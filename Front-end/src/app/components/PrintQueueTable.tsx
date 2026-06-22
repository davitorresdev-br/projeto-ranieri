import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { IdlePrinterIllustration } from "./IdlePrinterIllustration";
import { JobStatus, PrintJob, Role } from "./types";
import { ArrowRight, Download, RotateCcw } from "lucide-react";

type Props = {
  jobs: PrintJob[];
  role: Role;
  currentUser: string;
  onCycleStatus: (id: string) => void;
  onReprint: (id: string) => void;
};

const STATUS_STYLES: Record<JobStatus, string> = {
  Pendente: "bg-amber-100 text-amber-800 border-amber-200",
  Imprimindo: "bg-blue-100 text-blue-800 border-blue-200",
  Concluído: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge variant="outline" className={`${STATUS_STYLES[status]}`}>
      {status === "Imprimindo" && (
        <span className="relative flex h-1.5 w-1.5 mr-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-600" />
        </span>
      )}
      {status}
    </Badge>
  );
}

export function PrintQueueTable({ jobs, role, currentUser, onCycleStatus, onReprint }: Props) {
  // COORDENADOR sees and manages only their own submissions; TI has full admin access
  const isTeacher = role === "COORDENADOR";
  const visibleJobs = isTeacher ? jobs.filter((j) => j.sender === currentUser) : jobs;

  const pendingQueue = jobs.filter((j) => j.status === "Pendente");
  const teacherPosition = (job: PrintJob): string => {
    if (job.status === "Concluído") return "—";
    if (job.status === "Imprimindo") return "Em impressão";
    const idx = pendingQueue.findIndex((j) => j.id === job.id);
    return idx >= 0 ? `${idx + 1}º na fila` : "—";
  };

  if (visibleJobs.length === 0) {
    return (
      <Card className="p-12 flex flex-col items-center justify-center text-center border-[var(--brand-border)]">
        <IdlePrinterIllustration />
        <p className="mt-6 text-slate-700" style={{ fontSize: "1.125rem", fontWeight: 600 }}>
          Nenhuma impressão pendente na fila.
        </p>
        <p className="text-slate-500 mt-1">Quando você enviar um documento, ele aparecerá aqui.</p>
      </Card>
    );
  }

  return (
    <Card className="border-[var(--brand-border)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--brand-border)] flex items-center justify-between">
        <div>
          <p style={{ fontWeight: 600, color: "#0f172a" }}>
            {isTeacher ? "Minhas Impressões" : "Fila Completa de Impressão"}
          </p>
          <p className="text-slate-500" style={{ fontSize: "0.85rem" }}>
            {isTeacher
              ? "Apenas os documentos enviados por você são exibidos."
              : "Todos os documentos enviados pelos coordenadores de área."}
          </p>
        </div>
        <Badge variant="outline" className="bg-slate-50">
          {visibleJobs.length} {visibleJobs.length === 1 ? "registro" : "registros"}
        </Badge>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead>ID</TableHead>
              {!isTeacher && <TableHead>Remetente</TableHead>}
              <TableHead>Matéria / Turma</TableHead>
              <TableHead>Arquivo</TableHead>
              <TableHead className="text-center">Cópias</TableHead>
              <TableHead>{isTeacher ? "Sua Posição na Fila" : "Fila"}</TableHead>
              <TableHead>Status</TableHead>
              {!isTeacher && <TableHead className="text-right">Ações</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleJobs.map((job) => (
              <TableRow key={job.id} className="hover:bg-slate-50/50">
                <TableCell className="text-slate-500" style={{ fontFamily: "ui-monospace, monospace", fontSize: "0.8rem" }}>
                  {job.id}
                </TableCell>
                {!isTeacher && (
                  <TableCell style={{ fontWeight: 500 }}>{job.sender}</TableCell>
                )}
                <TableCell>
                  <div style={{ fontWeight: 500, color: "#0f172a" }}>{job.subject}</div>
                  <div className="text-slate-500" style={{ fontSize: "0.8rem" }}>{job.turma}</div>
                </TableCell>
                <TableCell>
                  <button className="inline-flex items-center gap-1.5 text-[var(--brand-blue)] hover:underline" style={{ fontSize: "0.85rem" }}>
                    <Download size={14} />
                    <span className="max-w-[180px] truncate">{job.fileName}</span>
                  </button>
                </TableCell>
                <TableCell className="text-center">{job.copies}</TableCell>
                <TableCell>
                  {isTeacher ? (
                    <Badge className="bg-[var(--brand-blue)] text-white hover:bg-[var(--brand-blue)]">
                      {teacherPosition(job)}
                    </Badge>
                  ) : (
                    <span className="text-slate-600">
                      {job.status === "Pendente" ? `${pendingQueue.findIndex((j) => j.id === job.id) + 1}º` : job.status === "Imprimindo" ? "—" : "—"}
                    </span>
                  )}
                </TableCell>
                <TableCell><StatusBadge status={job.status} /></TableCell>
                {!isTeacher && (
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {job.status !== "Concluído" ? (
                        <Button size="sm" variant="outline" onClick={() => onCycleStatus(job.id)} className="gap-1">
                          Avançar <ArrowRight size={14} />
                        </Button>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => onReprint(job.id)} className="gap-1 text-[var(--brand-blue)]">
                          <RotateCcw size={14} /> Reimprimir
                        </Button>
                      )}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
