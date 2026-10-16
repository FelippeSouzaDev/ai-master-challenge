# RavenStack: por que o churn subiu

**Para:** CEO · **Leitura:** 5 minutos · **Base:** dados de jan/23 a dez/24, 5 tabelas cruzadas

---

## A resposta curta

**O cliente antigo não está saindo mais. O contrato novo é que está quebrando no primeiro mês.**

Desde agosto de 2024, um contrato com até 30 dias de vida encerra a **7,9% ao mês**. Antes eram **0,66%**: subiu 12 vezes. Contratos com mais de 6 meses continuam exatamente como sempre (0,88% ao mês). A alta é igual em todos os planos, setores, países e canais de aquisição. Não é um tipo de cliente; é algo que mudou na forma de vender ou de implantar a partir de agosto.

![](output/g2_idade.png)

**Quanto custa:** o MRR perdido no mês foi de 0,6% em julho para 5,4% em dezembro. Entre agosto e dezembro saíram US$ 990 mil de MRR, e **US$ 648 mil disso (65%) é excesso** sobre o padrão de antes. Hoje, **43% do MRR ativo (US$ 4,4 milhões) está em contratos com menos de 90 dias**, justamente a faixa que está quebrando.

## Por que os times discordam

| O que dizem | O que o dado mostra |
|---|---|
| CS: "a satisfação está ok" | A pesquisa só tem notas 3, 4 e 5. **Nenhuma nota 1 ou 2 em 2.000 tickets**, e 41% não respondem. A métrica não consegue mostrar insatisfação. |
| Produto: "o uso cresceu" | O uso **total** está parado há 8 trimestres, enquanto a base cresceu 9 vezes. O uso **por conta** caiu 89%. Ou o cliente novo usa muito menos, ou a telemetria não acompanha a base nova. |
| Formulário de saída: "pricing", "features"... | O motivo marcado e o comentário escrito não têm relação entre si (p = 0,99). O formulário não informa nada. |

Ninguém está mentindo. Os três times olham instrumentos que não enxergam o problema.

## O que fazer, em ordem

| # | Ação | Quando | Dono | Impacto estimado |
|---|---|---|---|---|
| 1 | **Descobrir o que mudou em agosto.** Uma reunião com Vendas, CS e Financeiro, com a pergunta: o que mudou em meta, comissão, campanha, time, contrato padrão ou implantação? Ligar para 20 das 154 contas que tiveram contrato encerrado no 1º mês desde agosto. | Esta semana | CEO + RevOps | Destrava as ações 3 e 4. Custo: poucas horas |
| 2 | **Fila de implantação.** CS liga para as contas com mais MRR em contratos jovens. As **81 primeiras da lista cobrem 50% do risco** do próximo mês. A lista sai do script; não depende de ninguém montar planilha. | Esta semana | Head de CS | Fechar metade do gap = **US$ 139 mil de MRR** preservados em 3 meses |
| 3 | **Comissão atrelada a 90 dias.** Pagar a comissão de venda só depois de o contrato passar do 1º trimestre, com estorno se ele sair antes. Faz a venda ruim custar para quem vende. | 30 dias | CFO + Vendas | Se a safra voltar ao padrão antigo (97,5% de sobrevivência aos 90 dias, contra 87,5% hoje): **US$ 228 mil de MRR por safra mensal**, ~US$ 2,7 milhões de ARR |
| 4 | **Separar troca de contrato de cancelamento.** Cerca de 13% dos encerramentos precoces parecem reemissão de contrato, não saída. Marcar isso no faturamento. | 30 dias | Financeiro | Número de churn correto. Hoje está inflado |
| 5 | **Consertar os instrumentos.** CSAT de 1 a 5 de verdade, com follow-up para quem não responde. Conferir se a telemetria cobre as contas novas. Formulário de saída com um motivo obrigatório. Ligar cada evento de churn a um contrato. | 60 dias | CS + Produto + Dados | Os próximos diagnósticos param de depender de investigação manual |
| 6 | **Trocar o KPI.** Acompanhar churn de receita **por idade do contrato**, e não o churn total. Alerta se o 1º mês passar de 2%. | 30 dias | RevOps | Este problema teria aparecido em setembro, não em dezembro |

## O que NÃO fazer

- **Não dar desconto.** Nada indica preço: o preço por seat não mudou, e o motivo "pricing" no formulário é ruído.
- **Não priorizar roadmap pelo formulário de saída.** Ele não carrega informação.
- **Não fazer campanha de retenção por segmento.** Nenhum segmento difere dos outros; a campanha atingiria o alvo por acaso.
- **Não comprar um modelo preditivo de churn agora.** Testei um com 36 variáveis das 5 tabelas, e ele acerta o mesmo que uma moeda (AUC 0,475). O dado de hoje não tem o sinal. Primeiro a ação 5.

## Cuidados

- **Dezembro precisa ser confirmado com janeiro.** 61 encerramentos caíram nos últimos 3 dias do ano, contra uma média de ~5 por dia no resto de dezembro. Pode ser cancelamento em lote ou artefato de extração. A conclusão não depende de dezembro: de agosto a novembro o excesso já é de 1,4x a 2,5x, todos significativos.
- **O diagnóstico localiza o problema; não prova a causa.** Que o problema está no contrato novo, desde agosto e em todos os segmentos, os dados mostram. *Por que* isso acontece está fora das 5 tabelas. É o que a ação 1 responde.
- O dataset é sintético. O método serve para dado real.

---

Detalhes e testes: [auditoria de dados](../docs/01-auditoria-de-dados.md) · [diagnóstico completo](../docs/02-diagnostico.md) · [lista de contas em risco](output/contas_em_risco.csv) · [relatório interativo](output/relatorio.html)
