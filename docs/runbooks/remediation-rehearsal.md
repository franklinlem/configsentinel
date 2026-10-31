# Ensaio do candidato sem promoção

Base de recuperação: revisão `0524bee`, release ativa `v0.1.0-rc.1`. IDs das três imagens e restore verificado estão em `../evidence/remediation/recovery-point.json`. A aplicação Coolify ativa e o piloto permanecem nesse RC até revisão humana.

Executar somente em stack isolada de homologação, sem routers, rede Coolify ou portas públicas. Volume próprio; nunca montar o volume da central ativa. Restaurar backup verificado em cópia vazia, aplicar `db/roles/provision.sql` como administrador exclusivo da cópia, executar API `--migrate` com credencial migrator e iniciar runtime com role restrita. Senhas devem ser passadas por ambiente protegido, nunca por argumentos ou relatórios.

O candidato mantém PostgreSQL 17.11 e schema 1. O helper gosu é removido; entrypoints usam su-exec somente para executar como postgres. Não há pg_upgrade, alteração de formato ou SQL destrutivo. Inicialização nova, restore e reabertura do volume de ensaio devem passar antes de considerar atualização de qualquer banco ativo.

Ensaio: verificar health/autorização e contagens; parar apenas containers da cópia; usar imagens anteriores por ID imutável, mantendo o volume da cópia; verificar compatibilidade; voltar aos mesmos digests candidatos e conferir novamente dados/health. Não usar `down -v` nem restaurar por cima do banco ativo. O RC antigo inicializa com schema 1 existente e não precisa de DDL, portanto suporta a role runtime para rollback. Candidato recusa schema diferente de 1.

Builds e scans são por digest em GHCR privado, plataforma linux/amd64. Cosign usa chave pública fixada em `deploy/release-signing.pub`; assinatura e atestações vinculam digest/commit/SBOM. Não há publicação no log público de transparência: a política privada verifica assinaturas com a chave fixada e não verifica Rekor. Isso não oferece identidade OIDC pública nem transparência independente. Chave privada cifrada e senha existem somente em armazenamento local protegido e secrets do Actions.

Uma chave SSH de CI tem forced-command exclusivo `registry-pull-only.py`, sem shell, forwarding ou deploy. Faz login temporário com o GITHUB_TOKEN efêmero, baixa apenas os quatro repositórios ConfigSentinel por digest e apaga o login. Não habilita deploy no Coolify. Para promoção futura, configurar credencial de pull somente leitura no recurso ConfigSentinel e revisar o Compose por digest e o manifest; não alterar o proxy.

Produção permanece desativada. Publicação de candidato no registry não autoriza promoção para tráfego de homologação ou produção. Exige revisão de Franklin.
