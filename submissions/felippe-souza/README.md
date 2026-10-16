# Submissão — Felippe Silva de Souza — Challenge 001

## Sobre mim

- **Nome:** Felippe Silva de Souza
- **LinkedIn:** <!-- FELIPPE: preencher -->
- **Challenge escolhido:** 001 — Diagnóstico de Churn

---

## Executive Summary

O churn da RavenStack não subiu porque clientes antigos estão indo embora. Subiu porque **contratos novos estão quebrando no primeiro mês**: desde agosto de 2024, um contrato com até 30 dias encerra a 7,9% ao mês, contra 0,66% antes (12x). Contratos com mais de 6 meses seguem na mesma taxa. A alta é igual em todos os segmentos e não é explicada por preço, uso, suporte nem mix da base. Ela aponta para uma mudança na forma de vender ou implantar, que nenhuma das 5 tabelas registra. O paradoxo do CEO tem explicação nos instrumentos: a pesquisa de satisfação não tem notas 1 e 2, o uso total está parado enquanto a base cresceu 9x, e o motivo de saída é ruído. **Recomendação principal:** investigar esta semana o que mudou em agosto em vendas e implantação, e atacar já a fila das 81 contas que concentram 50% do risco do próximo mês.

**Para o CEO, ler primeiro:** [`solution/relatorio-executivo.md`](solution/relatorio-executivo.md) (5 minutos).

---

## Solução

| Arquivo | O que é |
|---|---|
| [`solution/relatorio-executivo.md`](solution/relatorio-executivo.md) | Relatório para o CEO: causa, paradoxo, 6 ações priorizadas com impacto, o que não fazer |
| [`solution/output/painel-risco.html`](solution/output/painel-risco.html) | Painel autocontido para o CS: fila de contas em risco com filtros. Abre no navegador, sem servidor |
| [`solution/output/contas_em_risco.csv`](solution/output/contas_em_risco.csv) | Lista das 500 contas com o MRR em risco nos próximos 30 dias |
| [`docs/01-auditoria-de-dados.md`](docs/01-auditoria-de-dados.md) | Auditoria: três definições de churn que discordam, uso fora da janela do contrato, escala de CSAT truncada |
| [`docs/02-diagnostico.md`](docs/02-diagnostico.md) | Diagnóstico completo com todas as hipóteses testadas, incluindo as descartadas |
| [`process-log/README.md`](process-log/README.md) | Como cheguei aqui: decisões, erros da IA, caminhos descartados |

### Como rodar

Requer Python 3.10+.

```bash
pip install pandas numpy scipy scikit-learn matplotlib
python solution/fetch_data.py      # baixa os 5 CSVs do Kaggle (público, sem login) e confere a contagem de linhas
python solution/01_audit.py        # auditoria de dados
python solution/02_analysis.py     # diagnóstico, gráficos e lista de risco (~1 minuto)
python solution/03_impact.py       # impacto estimado das ações
python solution/04_dashboard.py    # gera o painel HTML
```

Rodar a partir da pasta `submissions/felippe-souza/`. Os dados ficam em `data/`, fora do git.

### Abordagem

1. **Auditar antes de analisar.** As chaves estavam íntegras, mas o significado não: `accounts.churn_flag` marca 110 contas, `churn_events` cobre 352 e as assinaturas encerradas somam 312 contas. Nenhuma conta saiu de vez. Escolhi como definição a assinatura encerrada, medida em MRR, porque é a única fonte em que data de fim e flag batem 100%.
2. **Separar idade do contrato de calendário.** A contagem bruta de churn mistura as duas coisas, porque a base ficou mais jovem quando as vendas aceleraram. Medi a taxa por dias de exposição em cada faixa de idade, antes e depois do ponto de virada.
3. **Tentar derrubar cada achado.** Seis hipóteses testadas (mix, segmentos, troca de contrato, previsibilidade, primeira assinatura, mudança de produto ou preço), cinco descartadas e uma parcial. Diferenças entre grupos passaram por teste de significância com correção para múltiplos testes, placebo ou rótulo embaralhado.
4. **Traduzir em dinheiro e em fila de trabalho.** Impacto em MRR por ação e uma lista que o CS pode usar na segunda-feira.

### Resultados / Findings

1. **Contratos de até 30 dias: 0,66% → 7,90% ao mês desde ago/24 (p = 1e-34). 180+ dias: 0,88% → 0,88%.**
2. **Não é mix:** com as taxas antigas aplicadas à base de cada mês, o observado/esperado sobe de 1,0 (até jul/24) para 5,3 (dez/24).
3. **Não é segmento:** nenhuma de 9 variáveis (plano, cobrança, setor, canal, país, trial, upgrade, downgrade, auto-renovação) passa em p < 0,05.
4. **Não é previsível com os dados atuais:** modelo com 36 variáveis das 5 tabelas tem AUC de 0,475, igual ao acaso.
5. **Só ~13% é troca de contrato:** 66% dos encerramentos precoces têm outro contrato aberto em ±7 dias, contra 53% num placebo.
6. **US$ 648 mil dos US$ 990 mil de MRR perdidos entre ago e dez/24 são excesso** sobre o padrão anterior.
7. **Os instrumentos não enxergam:** CSAT só com notas 3, 4 e 5 e 41% sem resposta; uso total parado há 8 trimestres; motivo de saída independente do comentário (p = 0,99).

![](solution/output/g2_idade.png)

### Recomendações

Em ordem. Detalhe e impacto no [relatório executivo](solution/relatorio-executivo.md).

1. **Esta semana:** descobrir o que mudou em agosto em vendas e implantação (reunião com Vendas, CS e Financeiro; ligar para 20 contas que saíram no 1º mês).
2. **Esta semana:** fila de implantação nas 81 contas que cobrem 50% do risco. Fechar metade do gap preserva ~US$ 139 mil de MRR em 3 meses.
3. **30 dias:** comissão de venda paga só depois de 90 dias de contrato. Voltar ao padrão antigo vale ~US$ 228 mil de MRR por safra mensal.
4. **30 dias:** separar troca de contrato de cancelamento no faturamento.
5. **30 dias:** acompanhar churn por idade do contrato, com alerta se o 1º mês passar de 2%.
6. **60 dias:** consertar CSAT, telemetria de uso e formulário de saída.

**Não fazer:** desconto, roadmap guiado pelo formulário de saída, campanha de retenção por segmento, modelo preditivo de churn antes de consertar os dados.

### Limitações

- **Causa não identificada.** O diagnóstico localiza o problema (contrato novo, desde ago/24, todos os segmentos), mas o mecanismo está fora das 5 tabelas. Faltam dados de vendas (vendedor, comissão, campanha) e de implantação.
- **Dezembro de 2024 precisa de confirmação.** São 61 encerramentos nos 3 últimos dias do ano. A conclusão se sustenta só com agosto a novembro.
- **Uso não foi usado no nível do contrato.** 77% dos registros de uso caem antes do início do contrato a que estão ligados.
- **Impactos são estimativas** de um modelo de taxas por faixa de idade, sem vendas novas no horizonte e sem intervalo de confiança.
- **Dataset sintético.** O método vale para dado real; os números são ilustrativos.

---

## Process Log — Como usei IA

Detalhe completo em [`process-log/README.md`](process-log/README.md). Conversa exportada em [`process-log/chat-exports/`](process-log/chat-exports/).

### Ferramentas usadas

| Ferramenta | Para que usou |
|------------|--------------|
| Claude Code (desktop, Claude Opus 5.5) | Leitura do desafio e da vaga, download dos dados, scripts de auditoria e análise, testes estatísticos, gráficos, painel e redação |
| Navegador embutido do Claude Code | Leitura da página da vaga e conferência visual do painel |
| Git + GitHub CLI | Fork, branch e um commit por fase |

### Workflow

1. **Escolha do desafio:** li a vaga e os 4 desafios com a IA e escolhi o 001, pela proximidade com o meu trabalho em Controladoria (risco de carteira e inadimplência).
2. **Plano:** a IA propôs 7 fases. Aprovei com uma condição: auditar o dado antes de qualquer análise.
3. **Auditoria:** a IA escreveu as checagens; o achado das três definições de churn mudou o rumo do trabalho. Escolhi a definição por receita.
4. **Exploração:** muitas hipóteses rodadas em scripts descartáveis. O que sobreviveu foi para `02_analysis.py`.
5. **Tentativa de derrubar cada achado:** mix, segmento, troca de contrato, previsibilidade. Cada um com teste formal.
6. **Impacto, relatório e painel:** números conferidos contra a saída do script antes de entrar no texto.

### Onde a IA errou e como corrigi

- **Leitura errada da tabela de vida:** "4% dos contratos saem no 1º mês" parecia dizer que contrato novo é sempre arriscado. Separando idade de calendário, antes de ago/24 o 1º mês tinha a menor taxa. O problema é o contrato novo *desde agosto*.
- **Hipótese de mix:** a IA sugeriu que o pico era só a base ficando mais jovem. O teste rejeitou.
- **Falso positivo "primeira assinatura":** p = 0,008 no teste bruto, sumiu ao controlar o trimestre.
- **Correlação espúria:** "quem usa mais perde mais receita" era exposição (mais contratos = mais uso e mais encerramentos).
- **Troca de contrato superestimada:** 66% parecia muito; o placebo mostrou que 53% é acaso.
- **Afirmação errada no texto:** "de 5 a 16 contratos jovens por conta" no top 50. Conferido, o mínimo é 1. Corrigido.
- **Erros de código:** comparação de séries do pandas com índices desalinhados, gráfico com escalas misturadas, contagens fixas no código, plano da conta (não confiável segundo a auditoria) exibido no painel.

### O que eu adicionei que a IA sozinha não faria

<!-- FELIPPE: revisar e reescrever com as suas palavras. Abaixo, um rascunho com base no que aconteceu nesta conversa. -->

- **Desconfiar do dado antes de analisar.** No meu ambiente o dado falha em silêncio: o número sai errado, não ausente. Por isso a auditoria veio antes de tudo, e foi ela que mostrou que "churn" tinha três respostas diferentes.
- **Medir em receita, não em contagem.** Em cobrança, perder um contrato de US$ 50 não é perder um de US$ 5 mil. A definição por MRR veio daí.
- **Não entregar um modelo que não funciona.** Um modelo com AUC de 0,475 bem apresentado passaria no olho de quem não testa. Preferi dizer que o dado não tem o sinal e entregar uma fila baseada na única variável que discrimina.
- **Comissão atrelada à permanência do contrato.** <!-- FELIPPE: confirmar se é um mecanismo que você conhece da prática e descrever em uma frase. -->

---

## Evidências

- [x] Chat export: [`process-log/chat-exports/`](process-log/chat-exports/)
- [x] Git history: um commit por fase nesta branch
- [x] Narrativa escrita: [`process-log/README.md`](process-log/README.md)
- [x] Scripts reproduzíveis: `solution/01_audit.py` a `solution/04_dashboard.py`

---

_Submissão enviada em: <!-- data do PR -->_
