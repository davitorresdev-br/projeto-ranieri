// ---------------------------------------------------------------------
// Endereço do servidor (Backend Flask) na rede do colégio.
// ---------------------------------------------------------------------
// Mude SOMENTE este valor para apontar o app para o computador que está
// rodando o app.py. Use o IP local da máquina servidora (NUNCA
// "localhost"), assim os professores conseguem acessar de qualquer sala
// ou computador ligado à mesma rede do colégio.
//
// Como descobrir o IP da máquina servidora no Windows:
//   1. Abra o "Prompt de Comando" (cmd)
//   2. Digite "ipconfig" e pressione Enter
//   3. Procure por "Endereço IPv4" na rede usada pelo colégio
//
// Depois de alterar este valor, reinicie o "npm run dev".
export const API_BASE_URL = "http://192.168.0.133:8080";
