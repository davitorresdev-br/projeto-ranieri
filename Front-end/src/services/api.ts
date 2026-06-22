const API_URL = 'http://localhost:8080/api';

// 1. Busca os dados da fila de impressão atualizados do Banco SQLite
export async function obterFilaImpressao() {
  const resposta = await fetch(`${API_URL}/fila`);
  return resposta.json();
}

// 2. Busca os dados de controle de acesso (Quem está logado)
export async function obterDadosUsuario() {
  const resposta = await fetch(`${API_URL}/usuario`);
  return resposta.json();
}

// 3. Envia o formulário completo com o arquivo PDF anexado para o Python
export async function enviarSolicitacaoImpressao(formData: FormData) {
  const resposta = await fetch(`${API_URL}/enviar`, {
    method: 'POST',
    body: formData, // Envia como Multipart (Nativo para upload de arquivos)
  });
  return resposta.json();
}