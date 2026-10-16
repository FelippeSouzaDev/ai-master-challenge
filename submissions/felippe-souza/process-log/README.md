# Process log

Registro de como o trabalho foi feito, de quem decidiu o quê e de onde a IA errou ou foi corrigida.

**Ferramenta principal:** Claude Code (app desktop) com Claude Opus 5.5. A conversa completa é exportada em `chat-exports/` no final. O git history desta branch mostra a evolução por fase.

**Divisão de papéis:** eu (Felippe) defino o problema, escolho entre as alternativas e valido as conclusões contra o que conheço de cobrança e inadimplência. A IA escreve o código, roda as checagens e propõe interpretações, que eu aceito, ajusto ou recuso.

## Linha do tempo

### 0. Escolha do desafio

- Li a vaga e os 4 desafios com a IA.
- **Decisão minha:** Challenge 001 (Churn). Motivo: é o mais próximo do que faço em Controladoria. Risco de carteira, régua de cobrança e impacto em receita são o mesmo raciocínio de churn, com outro nome.

### 1. Plano

- A IA propôs 7 fases. Aprovei o plano com uma regra: **auditar o dado antes de analisar**. No meu ambiente de trabalho o dado falha em silêncio: o número sai errado, não ausente. Pular esta etapa é o erro que eu mais vejo.
- O download do Kaggle foi automatizado em [`solution/fetch_data.py`](../solution/fetch_data.py), com conferência da contagem de linhas.

### 2. Auditoria de dados

- A IA escreveu [`solution/01_audit.py`](../solution/01_audit.py) com checagens de chave, nulos, janela temporal e consistência entre tabelas.
- **Erro da IA:** a primeira versão do script quebrou ao comparar duas séries do pandas com índices em ordem diferente (`ValueError: Can only compare identically-labeled Series objects`). Corrigido ordenando os índices antes da comparação.
- Resultado em [`docs/01-auditoria-de-dados.md`](../docs/01-auditoria-de-dados.md). O achado central: há três definições de churn que discordam (110, 352 e 312 contas), e nenhuma conta saiu de vez.

## Decisões

| # | Decisão | Alternativas | Escolha | Por quê |
|---|---|---|---|---|
| 1 | Desafio | 001, 002, 003, 004 | 001 Churn | Aderência à minha experiência |
| 2 | Auditar antes de analisar | ir direto para a análise | auditar | O dado falha em silêncio |
| 3 | Definição de churn | _pendente_ | | |
