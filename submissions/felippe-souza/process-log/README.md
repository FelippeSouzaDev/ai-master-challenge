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

### 3. Diagnóstico

Fiz a exploração em scripts descartáveis e consolidei o que sobreviveu em [`solution/02_analysis.py`](../solution/02_analysis.py). Resultado em [`docs/02-diagnostico.md`](../docs/02-diagnostico.md).

Como o raciocínio andou, incluindo os caminhos errados:

1. **Primeira varredura:** testei todas as variáveis de conta e de assinatura contra o churn. Nada passou em p < 0,05. DevTools (31%) e o canal "event" (30%) pareciam altos, mas com 20 testes feitos isso é o esperado pelo acaso. Não entraram como achado.
2. **Armadilha de correlação:** o uso aparecia correlacionado *positivamente* com a perda de receita (rho = +0,14). Parecia "quem usa mais sai mais". Era exposição: contas com mais assinaturas usam mais e têm mais assinaturas para encerrar. Descartado.
3. **A tabela de vida mostrou o primeiro sinal real:** 4% dos contratos encerram no 1º mês, contra ~0,8% depois. A IA leu isso como "o risco está no começo do contrato".
4. **Hipótese da IA: o pico de dezembro é efeito de mix** (base mais jovem porque as vendas aceleraram). Testei aplicando as taxas por idade de antes de ago/24 aos meses seguintes. **Hipótese rejeitada:** a razão observado/esperado sobe de 1,0 para 5,3.
5. **Erro de leitura corrigido:** o "4% no 1º mês" da tabela de vida também estava contaminado pelo calendário, porque quase todo contrato jovem é do fim de 2024. Separando idade de período, ficou claro: antes de ago/24 o 1º mês tinha a *menor* taxa (0,66%). O problema não é "contrato novo é arriscado". É "contrato novo **a partir de ago/24** é arriscado".
6. **Efeito "primeira assinatura":** saiu significativo no teste bruto (p = 0,008), mas sumiu ao controlar o trimestre (OR 1,15, IC95 de 0,65 a 1,71). Era confusão. Descartado.
7. **Troca de contrato:** 66% dos encerramentos precoces têm outro contrato aberto em ±7 dias. Parecia que boa parte do churn era só reemissão de contrato. O placebo com datas deslocadas deu 53%, então o excesso real é de só 13 p.p.
8. **Modelo preditivo:** AUC de 0,475, contra 0,498 com rótulo embaralhado. Decidi **não** entregar um "modelo de churn" que na prática é aleatório. Em vez dele, a lista de risco usa a única variável que discrimina: a idade do contrato no regime atual.
9. **Erros de código da IA corrigidos:** gráfico de uso misturando escalas (troquei por índice em escala log) e contagens de satisfação fixas no código (agora calculadas do dado). Revisei os números do documento contra a saída do script e corrigi uma afirmação errada: "de 5 a 16 contratos jovens por conta" virou "mediana de 8, de 1 a 16".

### 4. Impacto, recomendações e entrega

- [`solution/03_impact.py`](../solution/03_impact.py) transforma as taxas por idade em dinheiro: o excesso de MRR perdido desde ago/24, a perda dos próximos 3 meses em três cenários e o custo por safra mensal de vendas.
- [`solution/relatorio-executivo.md`](../solution/relatorio-executivo.md): uma página para o CEO, com ações em ordem, dono, prazo e impacto, mais uma seção "o que NÃO fazer". Essa seção existe porque, com o dado que existe, as respostas óbvias (desconto, roadmap pelo formulário, campanha por segmento, modelo preditivo) desperdiçariam dinheiro.
- [`solution/04_dashboard.py`](../solution/04_dashboard.py) gera um painel HTML autocontido para o CS, conferido no navegador (filtros e ordenação testados).
- **Correções nesta fase:** decimal com ponto nos KPIs (o resto estava em pt-BR). A coluna "Plano" saiu do painel porque a auditoria mostrou que `accounts.plan_tier` bate com o contrato em só 34% dos casos. Mostrar "Basic" numa conta de US$ 75 mil de MRR confundiria o CS. "191 clientes" virou "154 contas", porque os 191 são contratos, não contas.
- **Reprodutibilidade:** o pipeline inteiro foi rodado de novo (download → auditoria → análise → impacto → painel), e os números dos documentos foram conferidos contra a saída.

## Decisões

| # | Decisão | Alternativas | Escolha | Por quê |
|---|---|---|---|---|
| 1 | Desafio | 001, 002, 003, 004 | 001 Churn | Aderência à minha experiência |
| 2 | Auditar antes de analisar | ir direto para a análise | auditar | O dado falha em silêncio |
| 3 | Definição de churn | A) receita via assinaturas encerradas; B) só `accounts.churn_flag`; C) `churn_events` | A, com B como churn "oficial" de logo e C só como evidência de processo | Única fonte em que fim e flag batem 100%. Delegado à IA após ler a auditoria, aceitei a recomendação |
| 4 | Entregar modelo preditivo? | modelo com AUC ~0,5; lista por idade do contrato | lista por idade | Modelo sem poder preditivo passaria uma confiança falsa |
| 5 | Ponto de corte do regime | data escolhida no olho; teste formal | ago/24, confirmado pelo teste de mix | É o primeiro mês com p < 0,05 e a razão sobe todo mês depois dele |
