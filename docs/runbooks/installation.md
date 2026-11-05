# Instalação e operação

## Central

Use Compose local para desenvolvimento; Coolify Raw para homologação. Consulte deploy/coolify.md. Bootstrap apenas em banco sem usuários. Cadastre projetos/ambientes/servidor e provisione o agente pelo painel. Nunca envie o token ao Git ou a sistemas de mensagens.

## Agente Linux

Compatível com Linux com openat2 (kernel >= 5.6). Sem fallback para symlinks. Requer filesystem local estável; não use mounts de rede ou arquivos hostis que possam bloquear leitura. Binários independentes para amd64 e arm64. Instalação é manual; os comandos seguintes dependem de autorização do administrador do host.

1. Criar usuário de sistema `configsentinel` sem shell e sem sudo, grupos privilegiados ou Docker socket.
2. Instalar binário em `/usr/local/bin/configsentinel-agent` (root:root 0755), unit distribuída e `/etc/configsentinel` (root:configsentinel 0750).
3. Configuração root:configsentinel 0640 e token configsentinel:configsentinel 0600. Paths absolutos individuais; aliases únicos; hash_only obrigatório. Denylists padrão são cumulativas e não podem ser desativadas.
4. Fixture piloto: `/opt/configsentinel-lab/demo.conf`, texto inteiramente sintético, root:root 0644. O agente tem somente leitura; o administrador altera a fixture para ensaios.
5. `systemctl daemon-reload` e `systemctl enable --now configsentinel-agent`. Validar journal, estado online e baseline no painel.

O diretório da fila deve existir antes de iniciar o agente, pertencer ao UID do agente e não permitir escrita por grupo ou outros. A unit fornecida o cria com `StateDirectoryMode=0700`; em instalações sem systemd, provisione-o antecipadamente. A fila e o lock devem ser arquivos regulares pertencentes ao agente e sem links adicionais. O caminho do token não pode conter symlinks. Não mova nem substitua uma fila existente sem preservar seus dados e validar a recuperação.

Não monitorar `/home`, `/root`, `/proc`, `/sys`, `/dev`, segredos, `.env`, PEM/keys ou diretórios inteiros. Nunca alterar permissões de configurações reais para acelerar piloto. Arquivos regulares com múltiplos hardlinks são recusados. Arquivos podem mudar e voltar entre polls sem detecção. Root comprometido pode adulterar evidências.

## Rotação

Emita token novo, instale atomicamente com 0600, valide comunicação e revogue o anterior. Rotação não muda agent_id nem fila. Nova instalação muda agent_id e exige outro banco de fila; nunca apagar fila pendente para resolver conflito.

## Recuperar acesso

Via SSH, atualize ADMIN_EMAIL/ADMIN_PASSWORD nas variáveis exclusivas do recurso e execute `/app/server --reset-password` no container da API usando essas variáveis. A ferramenta gera Argon2id, revoga todas as sessões do usuário e audita o reset em transação. Não editar hashes manualmente. O bootstrap não substitui senha de usuário existente. Não há recuperação por e-mail nesta versão.
