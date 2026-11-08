# Especificação da Interface Web — Alternador de Tema e Fluxo Resiliente de Logout

Data: 08/11/2026
Módulo: `apps/web` (`configsentinel-web`) e `apps/api` (`configsentinel-api`)
Arquivos modificados:
- [`apps/web/src/styles.css`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/web/src/styles.css): variáveis dinâmicas de tema CSS (`:root, [data-theme="dark"]` e `[data-theme="light"]`).
- [`apps/web/src/main.tsx`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/web/src/main.tsx): alternador de tema (Sun/Moon), persistência via `localStorage`, logout com tratamento `try/finally` e redirecionamento para `/`.
- [`apps/web/src/api.ts`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/web/src/api.ts): persistência e leitura síncrona de CSRF com fallback em `localStorage` e `sessionStorage`.
- [`apps/api/internal/server/server.go`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/api/internal/server/server.go): flexibilização de CSRF em `/auth/logout` condicionada à validação estrita de `Origin`.
- [`apps/api/internal/server/integration_test.go`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/api/internal/server/integration_test.go): teste de regressão validando logout com token CSRF vazio.

---

## 1. Visão Geral

A interface web do ConfigSentinel passou por duas evoluções fundamentais:
1. **Alternador de Tema Claro / Escuro (Theme Toggle):**
   - Suporte nativo a tema escuro (fundo preto/escuro, texto claro e destaques em tons de laranja) e tema claro corporativo.
   - Ícone intuitivo de alternância (`Sun` / `Moon` da biblioteca `lucide-react`) posicionado tanto na tela de autenticação quanto na barra superior do painel (`topbar`).
   - Persistência imediata da preferência no navegador do usuário (`localStorage.getItem('cs_theme')`), com carregamento inicial padrão no modo escuro.
2. **Resiliência e Correção do Fluxo de Logout:**
   - Anteriormente, o backend rejeitava chamadas de logout com `403` caso o token CSRF em memória estivesse ausente (por exemplo, após recarregamento de página ou abertura em nova aba), travando o cliente no painel.
   - O backend agora autoriza a rota `POST /auth/logout` validando estritamente a identidade de `Origin == s.Origin`, dispensando o token CSRF específico de sessão.
   - O frontend armazena o token CSRF de forma sincronizada em `localStorage` e `sessionStorage`.
   - O encerramento de sessão executa `clearCsrf()`, limpa o cache do React Query e redireciona forçadamente para a raiz (`/`) em bloco `finally`, garantindo que o usuário nunca fique preso em sessão expirada ou inválida.

---

## 2. Paleta de Cores e Variáveis Dinâmicas de Tema

Todas as cores foram refatoradas para tokens semânticos CSS suportados em `:root, [data-theme="dark"]` e `[data-theme="light"]`:

### 2.1 Tema Escuro (Padrão)
- **Fundo Principal (Body / Root / Layout):** `#0a0d12` (preto profundo azulado)
- **Barra Lateral (Sidebar):** `#070a0e` (preto obsidiana com borda divisória `#1a222c`)
- **Barra Superior (Topbar):** `#0c1017` com borda inferior `#222b38`
- **Painéis, Cards, Caixas de Métricas e Tabelas:** `#10161f` (grafite escuro)
- **Campos de Entrada (Input, Select, Textarea, Search):** `#10161f` com borda `#283241` e foco `#ea580c`
- **Diálogos Modais:** `#111720` com sombra de profundidade `rgba(0, 0, 0, 0.75)`
- **Tipografia:** `#f3f4f6` (texto principal), `#e5e7eb` (secundário), `#9ca3af` (suave/muted)
- **Destaques em Laranja:** `#c2410c` / `#ea580c` (botões primários), `#fb923c` / `#fdba74` (links, ícones e acentos)

### 2.2 Tema Claro
- **Fundo Principal (Body / Root / Layout):** `#f6f7f5` (cinza claro suave)
- **Barra Lateral (Sidebar):** `#181d24` (contraste neutro escuro com a navegação)
- **Barra Superior (Topbar):** `#ffffff` com borda inferior `#e2e8f0`
- **Painéis, Cards e Tabelas:** `#ffffff` com borda `#e2e8f0`
- **Tipografia:** `#0f172a` (texto principal), `#334155` (secundário), `#64748b` (suave/muted)
- **Destaques em Laranja:** `#ea580c` (primário), `#c2410c` (hover), `#9a3412` (acentos escuros para alto contraste)

---

## 3. Conformidade de Acessibilidade (WCAG 2.1)

Todos os contrastes calculados atendem ou superam os critérios mínimos de 4,5:1 (nível AA) e 7:1 (nível AAA):

| Elemento / Combinação | Cores (Tema Escuro) | Rácio de Contraste | Nível WCAG |
|---|---|---|---|
| Texto normal sobre fundo principal | `#f3f4f6` sobre `#0a0d12` | **17,68:1** | AAA |
| Texto normal sobre cartões / painéis | `#f3f4f6` sobre `#10161f` | **16,50:1** | AAA |
| Texto atenuado (*muted*) sobre cartões | `#9ca3af` sobre `#10161f` | **7,15:1** | AAA |
| Botão primário (texto branco sobre laranja) | `#ffffff` sobre `#c2410c` | **5,18:1** | AA |
| Links de destaque laranja sobre cartões | `#fb923c` sobre `#10161f` | **8,02:1** | AAA |
| Acento laranja ativo na barra lateral | `#fb923c` sobre `#070a0e` | **8,76:1** | AAA |

---

## 4. Validação Técnica e Implantação

1. **Testes Unitários e Race Detector (Backend):**
   `cd apps/api && go test -race -count=1 ./...` — aprovado com 0 falhas e detecção de concorrência ativa.
2. **Testes de Operações:**
   `python3 -m unittest discover -s tests/operations -v` — 28 testes aprovados.
3. **Compilação e Verificação do Frontend:**
   `cd apps/web && npm run build` (`tsc -b && vite build`) — compilação concluída sem erros ou avisos de tipagem.
4. **Implantação no Ambiente de Homologação:**
   - Estáticos atualizados em `/usr/share/nginx/html` no container `oi6lvzwzomwtbbgzf5uzofuh-web-1` do servidor Contabo.
   - Imagem da API atualizada para `ghcr.io/franklinlem/configsentinel-api:local-patch` e reiniciada em modo saudável no container `oi6lvzwzomwtbbgzf5uzofuh-api-1`.
5. **Verificação de Regressão e Segurança:**
   - `git diff --check` sem achados de formatação ou espaços espúrios.
   - `.local/tools/gitleaks` com 0 ocorrências de credenciais ou segredos expostos.
