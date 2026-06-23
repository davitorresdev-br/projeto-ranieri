// ---------------------------------------------------------------------
// Endereço do servidor (Backend Flask) na rede do colégio.
// ---------------------------------------------------------------------
// Em vez de fixar um único IP, descobrimos automaticamente qual
// endereço o navegador usou para abrir a página (window.location.hostname)
// e montamos a URL da API a partir dele. Assim o sistema funciona ao
// mesmo tempo pela rede cabeada e pela rede Wi-Fi — cada pessoa acessa
// pelo IP que conseguir alcançar, e a chamada da API usa esse mesmo IP
// automaticamente, sem precisar editar este arquivo de novo.
//
// Único requisito: o computador servidor (o que roda o app.py) precisa
// estar conectado na(s) mesma(s) rede(s) que as pessoas vão usar para
// acessar, com as portas 5173 e 8080 liberadas no Firewall do Windows
// para os perfis de rede correspondentes.
export const API_BASE_URL = `http://${window.location.hostname}:8080`;
