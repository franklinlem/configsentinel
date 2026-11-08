# Especificação e Redesenho da Interface Web — Tema Escuro com Destaques em Laranja

Data: 08/11/2026  
Módulo: `apps/web` (`configsentinel-web`)  
Arquivos modificados: [`apps/web/src/styles.css`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/web/src/styles.css), [`apps/web/index.html`](file:///mnt/HD-NOTE1/apps-skills/configsentinel/apps/web/index.html)

---

## 1. Visão Geral

A interface web do ConfigSentinel foi atualizada a partir do esquema claro/esverdeado anterior para um tema escuro moderno de alto contraste, com foco em legibilidade operacional, ergonomia visual e destaques na cor laranja para sinalizações e ações interativas.

Todas as alterações preservam integralmente a responsividade (desktop, tablet e mobile), a estrutura de classes CSS e o cumprimento das diretrizes de acessibilidade WCAG 2.1 (níveis AA e AAA).

---

## 2. Paleta de Cores

### 2.1 Fundos (Tons Escuros e Pretos)
- **Fundo Principal (Body / Root / Layout):** `#0a0d12` (preto profundo azulado)
- **Barra Lateral (Sidebar):** `#070a0e` (preto obsidiana com borda divisória `#1a222c`)
- **Barra Superior (Topbar):** `#0c1017` com borda inferior `#222b38`
- **Painéis, Cards, Caixas de Métricas e Tabelas:** `#10161f` (grafite escuro)
- **Campos de Entrada (Input, Select, Textarea, Search):** `#10161f` com borda `#283241` e foco `#ea580c`
- **Diálogos Modais:** `#111720` com sombra de profundidade `rgba(0, 0, 0, 0.75)`
- **Banner de Resumo (Summary Banner):** `#141820` com borda `#222b38`
- **Blocos de Princípio e Destaque:** `#131822`

### 2.2 Tipografia (Tons Claros e Branco)
- **Texto Primário (Títulos `h1`, `h2`, textos destacados e números):** `#f9fafb` / `#f3f4f6`
- **Texto Secundário / Corpo de Tabela / Labels:** `#e5e7eb` / `#d1d5db`
- **Texto Suave / Muted (`p`, legendas, `small`, timestamps):** `#9ca3af`
- **Código e Monospace (`code`, visualização de hashes):** `#fdba74` (laranja suave claro) sobre fundo `#0d1219`

### 2.3 Destaques e Ações (Tons de Laranja)
- **Botões Primários (`.primary`):** Fundo `#c2410c` (laranja queimado escuro de alto contraste), borda `#ea580c`, hover `#9a3412` e texto `#ffffff`
- **Botões Secundários (`.secondary`):** Fundo `#10161f`, borda `#283241`, texto `#f3f4f6`, hover `#161e2a` com destaque `#fb923c`
- **Navegação Ativa (`nav a.active`):** Fundo `#2a150a`, texto `#fb923c` e borda `#4a2412`
- **Links e Ações Rápidas (`.text-link`):** Cor `#fb923c`, hover `#fdba74`
- **Identidade e Logo (`.brand`):** Ícone em `#f97316` e legenda em `#fb923c`
- **Ícones de Estado e Métricas:** Caixa `#1c2430` com ícone `#fb923c`
- **Radar de Monitoramento:** Círculo interno `#26160c`, borda externa `#3d2010`, ícone `#fb923c`
- **Pills de Ambiente e Hash:** Fundo `#2b1708`, borda `#542b10`, texto `#fdba74`

### 2.4 Badges de Estado
- **Online / Reconhecido (`.badge.online`, `.badge.ack`):** Fundo `#062b16`, texto `#4ade80`, borda `#14532d`
- **Offline / Falha / Deletado (`.badge.offline`, `.badge.unreadable`, `.badge.deleted`):** Fundo `#3c0d0d`, texto `#f87171`, borda `#7f1d1d`
- **Atrasado / Modificado / Alerta (`.badge.delayed`, `.badge.modified`, `.event-icon.warning`):** Fundo `#381507`, texto `#fb923c`, borda `#7c2d12`
- **Informativo / Baseline (`.badge.info`, `.badge.baseline`):** Fundo `#0f1d3a`, texto `#60a5fa`, borda `#1e3a8a`

---

## 3. Conformidade de Acessibilidade (WCAG 2.1)

Todos os contrastes calculados atendem ou superam os critérios mínimos de 4,5:1 (nível AA) e 7:1 (nível AAA):

| Elemento / Combinação | Cores | Rácio de Contraste | Nível WCAG |
|---|---|---|---|
| Texto normal sobre fundo principal | `#f3f4f6` sobre `#0a0d12` | **17,68:1** | AAA |
| Texto normal sobre cartões / painéis | `#f3f4f6` sobre `#10161f` | **16,50:1** | AAA |
| Texto atenuado (*muted*) sobre cartões | `#9ca3af` sobre `#10161f` | **7,15:1** | AAA |
| Botão primário (texto branco sobre laranja) | `#ffffff` sobre `#c2410c` | **5,18:1** | AA |
| Links de destaque laranja sobre cartões | `#fb923c` sobre `#10161f` | **8,02:1** | AAA |
| Acento laranja ativo na barra lateral | `#fb923c` sobre `#070a0e` | **8,76:1** | AAA |
| Itens de navegação na barra lateral | `#cbd5e1` sobre `#070a0e` | **13,36:1** | AAA |
| Texto pill de ambiente / hash | `#fdba74` sobre `#2b1708` | **10,13:1** | AAA |
| Botão de perigo / exclusão | `#fca5a5` sobre `#3b1111` | **8,68:1** | AAA |
| Badge online (verde escuro / claro) | `#4ade80` sobre `#062b16` | **8,83:1** | AAA |
| Badge offline (vermelho escuro / claro) | `#f87171` sobre `#3c0d0d` | **6,05:1** | AA |

---

## 4. Validação Técnica

1. **Build do Frontend:** `npm run build` executado com sucesso gerando bundle de produção em `apps/web/dist/`.
2. **Whitespace Check:** `git diff --check` sem achados de formatação ou linhas em branco espúrias.
3. **Scan de Segredos:** `.local/tools/gitleaks` executado com 0 achados.
