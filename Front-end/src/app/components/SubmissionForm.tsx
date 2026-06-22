import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Card } from "./ui/card";
import { FileDropzone } from "./FileDropzone";
import { ColorMode, Finishing, PageMode } from "./types";
import { Minus, Plus, Printer } from "lucide-react";
import { toast } from "sonner";

export type SubmissionDraft = {
  subject: string;
  turma: string;
  copies: number;
  color: ColorMode;
  pageMode: PageMode;
  finishing: Finishing;
  fileName: string;
  file?: File;
};

type Props = {
  onReview: (draft: SubmissionDraft) => void;
};

export function SubmissionForm({ onReview }: Props) {
  const [subject, setSubject] = useState("");
  const [turma, setTurma] = useState("");
  const [copies, setCopies] = useState(1);
  const [color, setColor] = useState<ColorMode>("PB");
  const [pageMode, setPageMode] = useState<PageMode>("Frente");
  const [finishing, setFinishing] = useState<Finishing>("Normal");
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !turma.trim() || !file) {
      toast.error("Preencha todos os campos obrigatórios e anexe o PDF.");
      return;
    }
    onReview({ 
        subject, 
        turma, 
        copies, 
        color, 
        pageMode, 
        finishing, 
        fileName: file.name, 
        file: file 
    });
  };

  const SegBtn = ({ value, label }: { value: ColorMode; label: string }) => (
    <button
      type="button"
      onClick={() => setColor(value)}
      className={`flex-1 h-10 rounded-md border transition ${
        color === value
          ? "bg-[var(--brand-blue)] text-white border-[var(--brand-blue)]"
          : "bg-white text-slate-700 border-[var(--brand-border)] hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );

  return (
    <Card className="p-8 border-[var(--brand-border)] shadow-sm">
      <div className="mb-6">
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a" }}>Nova Solicitação de Impressão</h2>
        <p className="text-slate-500 mt-1">Preencha todos os campos obrigatórios</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid md:grid-cols-2 gap-5">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="subject">Matéria / Disciplina</Label>
            <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Ex: Matemática" />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="turma">Turma</Label>
            <Input id="turma" value={turma} onChange={(e) => setTurma(e.target.value)} placeholder="Ex: 3º Ano B — Ensino Médio" />
          </div>

          <div className="space-y-2">
            <Label>Número de Cópias</Label>
            <div className="flex items-center h-11 rounded-md border border-[var(--brand-border)] overflow-hidden">
              <button type="button" onClick={() => setCopies((c) => Math.max(1, c - 1))} className="w-11 h-full flex items-center justify-center text-slate-600 hover:bg-slate-100 transition">
                <Minus size={16} />
              </button>
              <input
                type="number"
                min={1}
                value={copies}
                onChange={(e) => setCopies(Math.max(1, parseInt(e.target.value) || 1))}
                className="flex-1 h-full text-center bg-transparent outline-none"
              />
              <button type="button" onClick={() => setCopies((c) => c + 1)} className="w-11 h-full flex items-center justify-center text-slate-600 hover:bg-slate-100 transition">
                <Plus size={16} />
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Modo de Página</Label>
            <Select value={pageMode} onValueChange={(v) => setPageMode(v as PageMode)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Frente">Apenas Frente</SelectItem>
                <SelectItem value="FrenteVerso">Frente e Verso</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label>Tipo de Cor</Label>
            <div className="flex gap-2">
              <SegBtn value="PB" label="P/B (Preto e Branco)" />
              <SegBtn value="Colorida" label="Colorida" />
            </div>
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label>Acabamento</Label>
            <Select value={finishing} onValueChange={(v) => setFinishing(v as Finishing)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Normal">Normal</SelectItem>
                <SelectItem value="Grampeada">Grampeada</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Anexo da Prova</Label>
          <FileDropzone file={file} onChange={setFile} />
        </div>

        <Button
          type="submit"
          className="w-full h-14 bg-[var(--brand-blue)] hover:bg-[var(--brand-blue-hover)] text-white transition relative overflow-hidden"
          style={{ borderBottom: "4px solid var(--brand-red)" }}
        >
          <Printer size={18} className="mr-2" />
          Enviar para o TI &amp; Impressora
        </Button>
      </form>
    </Card>
  );
}
