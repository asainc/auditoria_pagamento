/** Mensagens comuns distinguem o servidor da aplicação do provedor de extração. */
export function connectionMessage(status: number): string {
  if (status === 401 || status === 403) return 'O acesso ao servidor foi recusado. Verifique a autenticação do ambiente.';
  if (status === 404) return 'O endereço configurado não oferece a API da calculadora. Confira apiBaseUrl e o encaminhamento de /api.';
  return 'O servidor da aplicação está indisponível. Inicie frontend e backend com o iniciador start-dev e clique em Verificar conexão. Consulte o README se persistir.';
}
