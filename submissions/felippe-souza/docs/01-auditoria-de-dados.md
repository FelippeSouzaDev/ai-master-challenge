# Fase 1: auditoria de dados

Antes de qualquer análise, conferi se os dados sustentam um diagnóstico. Script: [`solution/01_audit.py`](../solution/01_audit.py). Todos os números abaixo saem dele e podem ser reproduzidos.

## Resumo

As chaves estão íntegras: não há órfãos, e as datas de signup, assinatura e churn seguem a ordem certa. **O problema está no significado do dado, não no formato.** "Churn" tem três definições que discordam entre si. Várias tabelas que deveriam se explicar mutuamente não se conectam no tempo. Um diagnóstico que pula esta etapa vai achar causa raiz em ruído.

## Achados

### 1. Três números de churn diferentes

| Fonte | Contas "churnadas" |
|---|---|
| `accounts.churn_flag = True` | 110 (22%) |
| Contas com pelo menos 1 linha em `churn_events` | 352 (70%) |
| Contas com pelo menos 1 assinatura `churn_flag = True` | 312 (62%) |

- 277 contas têm evento de churn mas `churn_flag = False`. 35 têm a flag sem nenhum evento.
- **As 110 contas com `churn_flag = True` ainda têm pelo menos uma assinatura ativa.** Todas as 500 contas têm assinatura ativa. Nenhuma conta saiu de vez.
- 295 das 352 contas com evento de churn continuam registrando uso **depois** do último evento.
- Só 6 dos 600 eventos têm `churn_date` igual ao `end_date` de alguma assinatura da conta. Só 47 ficam a até 7 dias. 214 eventos são de contas sem nenhuma assinatura encerrada.

Leitura: `churn_events` não registra "o cliente foi embora". Parece um log de cancelamentos parciais ou de intenção de saída, sem ligação com as assinaturas. O único par consistente é `subscriptions.end_date` × `subscriptions.churn_flag`, que batem em 100% (486 assinaturas encerradas, todas com flag).

### 2. Assinaturas são linhas de contrato simultâneas, não uma sequência

- Mediana de 10 assinaturas por conta (de 2 a 19).
- 4.410 das 5.000 assinaturas começam antes de a anterior da mesma conta terminar.
- O `plan_tier` da conta bate com o da assinatura mais recente em só 34% dos casos.

Consequência: MRR da conta = soma das assinaturas ativas. "Churn de assinatura" é perda parcial de receita (contração), não perda do cliente.

### 3. Uso não cai na janela da assinatura a que pertence

- 19.142 de 25.000 registros de uso (77%) têm data **anterior** ao início da assinatura ligada a eles. A mediana é 197 dias antes.
- 290 registros caem depois do fim da assinatura.
- 21 `usage_id` repetidos, cada par apontando para assinaturas diferentes.

Consequência: medir "uso caiu antes do churn" por assinatura não funciona. Uso só pode ser lido no nível da conta, e com cautela.

### 4. Satisfação: a escala está truncada e a ausência de resposta é grande

- `satisfaction_score` só tem notas 3, 4 e 5. Não existe nenhuma nota 1 ou 2 em 2.000 tickets.
- 41% dos tickets não têm resposta.
- Média de 3,97 nas contas sem flag de churn e 4,01 nas com flag. Taxa de não resposta de 42% contra 40%.

É a explicação mais direta para a frase "o CS diz que a satisfação está ok". A métrica não tem como mostrar insatisfação. Quem não respondeu, 41%, some da média.

### 5. Motivo declarado de churn não carrega informação

- `reason_code` tem distribuição quase uniforme entre 6 categorias (de 91 a 114 cada). "unknown" é 16%.
- `feedback_text` só tem 3 frases distintas e é independente de `reason_code`: há "switched to competitor" com reason `pricing`, "too expensive" com reason `features` e assim por diante, em proporções iguais.

Consequência: não dá para usar o motivo declarado como causa. Se houver causa raiz, ela tem de vir do comportamento (receita, uso, suporte), não do formulário de saída.

### 6. Sinais uniformes demais

- Taxa de churn (flag da conta) de 22,0% no Basic, 22,1% no Enterprise e 21,9% no Pro.
- Prioridade dos tickets dividida em ~25% por nível.

O dataset é sintético (o README do autor diz isso). Uniformidade assim indica que boa parte das colunas foi gerada de forma independente. A análise precisa provar cada sinal com teste estatístico e comparar contra o acaso, não só mostrar diferença de médias.

## Decisões que isso força

1. **Definição de churn**: precisa ser escolhida e declarada. Ver a seção de decisões no process log.
2. **Uso** é agregado por conta e por mês, nunca pela janela da assinatura.
3. **Motivo declarado** entra só como evidência de que o processo de saída não coleta informação útil, não como causa.
4. **Toda diferença entre grupos** passa por teste de significância e por comparação com uma linha de base aleatória.
