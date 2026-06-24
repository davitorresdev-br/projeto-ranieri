import { useEffect, useState } from "react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { BarChart3, FileText, Copy } from "lucide-react";
import { API_BASE_URL } from "../config";

type Props = {
  // Nome de quem está vendo o relatório. O backend confere, pelo nome, se
  // a pessoa é mesmo do Departamento de T.I. antes de devolver os números.
  currentUser: string;
};

type LinhaProfessor = { professor: string; pedidos: number; copias: number };

type Relatorio = {
  por_professor: LinhaProfessor[];
  total_pedidos: number;
  total_copias: number;
};

type Base = "criado" | "impresso";

// Mês atual no formato "AAAA-MM", já no horário de Brasília — o mesmo valor
// que o <input type="month"> usa e que o backend espera no parâmetro `mes`.
function mesAtual(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
  }).format(new Date());
}

export function ReportPanel({ currentUser }: Props) {
  const [mes, setMes] = useState<string>(mesAtual());
  const [base, setBase] = useState<Base>("criado");
  const [dados, setDados] = useState<Relatorio | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;

    const buscar = async () => {
      if (!currentUser) return;
      setCarregando(true);
      setErro(null);
      try {
        const url =
          `${API_BASE_URL}/api/relatorio` +
          `?user_name=${encodeURIComponent(currentUser)}` +
          `&mes=${encodeURIComponent(mes)}` +
          `&base=${base}`;
        const resposta = await fetch(url, { method: "GET" });
        const json = await resposta.json();
        if (cancelado) return;
        if (resposta.ok) {
          setDados(json);
        } else {
          setErro(json.erro || "Não foi possível carregar o relatório.");
          setDados(null);
        }
      } catch {
        if (!cancelado) setErro("Erro ao comunicar com o servidor.");
      } finally {
        if (!cancelado) setCarregando(false);
      }
    };

    buscar();
    return () => {
      cancelado = true;
    };
  }, [currentUser, mes, base]);

  const linhas = dados?.por_professor ?? [];

  return (
    <Card className="border-[var(--brand-border)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--brand-border)] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-slate-100 text-[var(--brand-blue)] flex items-center justify-center">
            <BarChart3 size={18} />
          </div>
          <div>
            <p style={{ fontWeight: 600, color: "#0f172a" }}>Relatório de Impressões</p>
            <p className="text-slate-500" style={{ fontSize: "0.8rem" }}>
              Cópias e pedidos por coordenador no período selecionado.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Alterna entre contar pela data de ENVIO ou pela data de IMPRESSÃO */}
          <div className="inline-flex rounded-md border border-[var(--brand-border)] overflow-hidden">
            <button
              type="button"
              onClick={() => setBase("criado")}
              className={`px-3 h-9 text-sm transition ${
                base === "criado" ? "bg-[var(--brand-blue)] text-white" : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Por envio
            </button>
            <button
              type="button"
              onClick={() => setBase("impresso")}
              className={`px-3 h-9 text-sm transition ${
                base === "impresso" ? "bg-[var(--brand-blue)] text-white" : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Por impressão
            </button>
          </div>

          <input
            type="month"
            value={mes}
            onChange={(e) => setMes(e.target.value)}
            className="h-9 rounded-md border border-[var(--brand-border)] px-3 text-sm text-slate-700 bg-white"
          />
        </div>
      </div>

      {/* Totais do período */}
      <div className="px-6 py-4 grid grid-cols-2 gap-4 border-b border-[var(--brand-border)] bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 text-[var(--brand-blue)] flex items-center justify-center">
            <FileText size={18} />
          </div>
          <div>
            <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", lineHeight: 1 }}>
              {dados?.total_pedidos ?? 0}
            </p>
            <p className="text-slate-500" style={{ fontSize: "0.8rem" }}>pedidos no período</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
            <Copy size={18} />
          </div>
          <div>
            <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", lineHeight: 1 }}>
              {dados?.total_copias ?? 0}
            </p>
            <p className="text-slate-500" style={{ fontSize: "0.8rem" }}>cópias no período</p>
          </div>
        </div>
      </div>

      {erro ? (
        <div className="px-6 py-8 text-center text-slate-500">{erro}</div>
      ) : carregando ? (
        <div className="px-6 py-8 text-center text-slate-400">Carregando…</div>
      ) : linhas.length === 0 ? (
        <div className="px-6 py-8 text-center text-slate-500">
          Nenhuma impressão registrada neste período.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead>Coordenador</TableHead>
                <TableHead className="text-center">Pedidos</TableHead>
                <TableHead className="text-center">Cópias</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {linhas.map((linha) => (
                <TableRow key={linha.professor} className="hover:bg-slate-50/50">
                  <TableCell style={{ fontWeight: 500, color: "#0f172a" }}>{linha.professor}</TableCell>
                  <TableCell className="text-center text-slate-600">{linha.pedidos}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="bg-slate-50">{linha.copias}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
}
