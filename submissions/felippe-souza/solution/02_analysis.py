"""Fase 2: diagnóstico de churn.

Definição de churn usada (ver docs/01-auditoria-de-dados.md):
- Churn de receita = assinatura encerrada (subscriptions.end_date preenchida). É a única fonte em
  que data de fim e flag batem 100%. Medido em MRR, não em contagem.
- accounts.churn_flag aparece só como o número "oficial" de logos.
- churn_events serve só para mostrar que o motivo declarado não informa nada.

Saídas em solution/output/: tabelas CSV, gráficos PNG e a lista de contas em risco.

Uso:
    python solution/02_analysis.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data"
OUT = ROOT / "output"
SNAPSHOT = pd.Timestamp("2024-12-31")  # último dia com dado em todas as tabelas
REGIME = pd.Timestamp("2024-08-01")  # início da alta, achado na exploração (ver docs/02)
AGE_BANDS = [(0, 30), (30, 90), (90, 180), (180, 100_000)]
BAND_LABELS = ["0-29 dias", "30-89 dias", "90-179 dias", "180+ dias"]
SEED = 42


def load():
    acc = pd.read_csv(DATA / "ravenstack_accounts.csv", parse_dates=["signup_date"])
    sub = pd.read_csv(DATA / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
    use = pd.read_csv(DATA / "ravenstack_feature_usage.csv", parse_dates=["usage_date"])
    tix = pd.read_csv(DATA / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"])
    chn = pd.read_csv(DATA / "ravenstack_churn_events.csv", parse_dates=["churn_date"])
    sub["age_at_end"] = (sub.end_date - sub.start_date).dt.days
    return acc, sub, use, tix, chn


def header(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def exposure_by_band(sub, t0, t1):
    """Dias de exposição e encerramentos por faixa de idade da assinatura dentro de [t0, t1].

    Taxa = encerramentos / dias expostos. Corrige o fato de a base ficar mais jovem quando
    as vendas aceleram: comparar contagem bruta de churn mistura idade com calendário.
    """
    stop = sub.end_date.fillna(SNAPSHOT)
    out = {}
    for lo, hi in AGE_BANDS:
        a0 = (sub.start_date + pd.to_timedelta(lo, "D")).clip(lower=t0)
        a1 = pd.concat([sub.start_date + pd.to_timedelta(hi, "D"), stop], axis=1).min(axis=1).clip(upper=t1)
        days = (a1 - a0).dt.days.clip(lower=0).sum()
        events = (sub.churn_flag & sub.end_date.between(t0, t1) & sub.age_at_end.between(lo, hi - 1)).sum()
        out[(lo, hi)] = (days, events)
    return out


def monthly_trend(sub):
    header("1. Tendência mensal do churn de receita")
    rows = []
    for m in pd.period_range("2023-01", "2024-12", freq="M"):
        s, e = m.start_time, m.end_time.normalize()
        active = sub[(sub.start_date <= e) & (sub.end_date.isna() | (sub.end_date >= s))]
        ended = sub[sub.end_date.between(s, e)]
        new = sub[sub.start_date.between(s, e)]
        rows.append(dict(mes=str(m), assinaturas_ativas=len(active), mrr_ativo=active.mrr_amount.sum(),
                         assinaturas_novas=len(new), assinaturas_encerradas=len(ended), mrr_perdido=ended.mrr_amount.sum()))
    t = pd.DataFrame(rows)
    t["churn_mrr_pct"] = (t.mrr_perdido / t.mrr_ativo * 100).round(2)
    print(t.tail(12).to_string(index=False))
    t.to_csv(OUT / "tendencia_mensal.csv", index=False)
    return t


def age_by_period(sub):
    header("2. Taxa mensal de encerramento por idade da assinatura: antes x depois de ago/24")
    before = exposure_by_band(sub, pd.Timestamp("2023-01-01"), REGIME - pd.Timedelta(days=1))
    after = exposure_by_band(sub, REGIME, SNAPSHOT)
    rows = []
    for (band, lab) in zip(AGE_BANDS, BAND_LABELS):
        (d0, e0), (d1, e1) = before[band], after[band]
        r0, r1 = e0 / d0 * 30, e1 / d1 * 30
        # teste de razão de taxas (Poisson condicional = binomial)
        p = stats.binomtest(e1, e0 + e1, d1 / (d0 + d1)).pvalue
        rows.append(dict(idade=lab, taxa_antes=f"{r0:.2%}", n_antes=e0, taxa_depois=f"{r1:.2%}", n_depois=e1,
                         multiplicador=round(r1 / r0, 1), p_valor=f"{p:.1e}"))
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    t.to_csv(OUT / "taxa_por_idade.csv", index=False)
    return before, after


def mix_test(sub, before):
    header("3. A alta é só efeito de base mais jovem? (esperado pelo mix x observado)")
    rate = {k: ev / d for k, (d, ev) in before.items()}
    rows = []
    for m in pd.period_range("2024-01", "2024-12", freq="M"):
        ex = exposure_by_band(sub, m.start_time, m.end_time.normalize())
        expected = sum(d * rate[k] for k, (d, _) in ex.items())
        observed = sum(ev for _, ev in ex.values())
        rows.append(dict(mes=str(m), observado=observed, esperado_pelo_mix=round(expected, 1),
                         razao=round(observed / expected, 2), p_valor=round(stats.poisson.sf(observed - 1, expected), 4)))
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print("Leitura: se fosse só mix, a razão ficaria perto de 1. A partir de ago/24 ela sobe todo mês.")
    t.to_csv(OUT / "mix_esperado_vs_observado.csv", index=False)
    return t


def segment_tests(acc, sub):
    header("4. A alta de encerramento precoce se concentra em algum segmento?")
    s = sub[(sub.start_date >= REGIME) & (sub.start_date <= SNAPSHOT - pd.Timedelta(days=30))].merge(
        acc[["account_id", "industry", "referral_source", "country"]], on="account_id")
    s["precoce"] = s.churn_flag & (s.age_at_end < 30)
    print(f"Assinaturas iniciadas entre ago e nov/24: {len(s)}; encerradas em <30 dias: {s.precoce.sum()} ({s.precoce.mean():.1%})")
    rows = []
    for col in ["plan_tier", "billing_frequency", "auto_renew_flag", "is_trial", "upgrade_flag", "downgrade_flag",
                "industry", "referral_source", "country"]:
        ct = pd.crosstab(s[col], s.precoce)
        p = stats.chi2_contingency(ct)[1]
        rates = (ct[True] / ct.sum(axis=1)).round(3)
        rows.append(dict(variavel=col, p_valor=round(p, 3), menor=f"{rates.idxmin()} {rates.min():.1%}",
                         maior=f"{rates.idxmax()} {rates.max():.1%}"))
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"Nenhuma variável passa em p<0,05 com correção de Bonferroni (limite {0.05 / len(t):.4f}).")
    t.to_csv(OUT / "segmentos_precoce.csv", index=False)


def replacement_test(sub):
    header("5. Encerramento precoce é troca de contrato? (teste placebo)")
    e = sub[sub.churn_flag & (sub.end_date >= REGIME) & (sub.age_at_end < 30)]
    starts = {a: g[["subscription_id", "start_date"]].values for a, g in sub.groupby("account_id")}

    def rate(dates):
        hits = sum(any(sid2 != sid and abs((st - d).days) <= 7 for sid2, st in starts[a])
                   for sid, a, d in zip(e.subscription_id, e.account_id, dates))
        return hits / len(e)

    observed = rate(e.end_date)
    rng = np.random.default_rng(SEED)
    placebo = []
    for _ in range(200):
        shift = pd.to_timedelta(rng.choice([-1, 1], len(e)) * rng.integers(20, 45, len(e)), "D")
        placebo.append(rate((e.end_date + shift).clip(REGIME, SNAPSHOT)))
    lo, hi = np.percentile(placebo, [2.5, 97.5])
    print(f"Com nova assinatura na mesma conta em ±7 dias: observado {observed:.0%} | placebo {np.mean(placebo):.0%} (IC95 {lo:.0%}-{hi:.0%})")
    print(f"Excesso sobre o acaso: {observed - np.mean(placebo):.0%} dos encerramentos precoces. O resto é perda real.")
    return observed, float(np.mean(placebo))


def ceo_paradox(acc, sub, use, tix):
    header("6. O paradoxo do CEO: 'satisfação ok' e 'uso cresceu'")
    rows = []
    for q in pd.period_range("2023Q1", "2024Q4", freq="Q"):
        s, e = q.start_time, q.end_time.normalize()
        n_acc = (acc.signup_date <= e).sum()
        n_sub = ((sub.start_date <= e) & (sub.end_date.isna() | (sub.end_date >= s))).sum()
        u = use[use.usage_date.between(s, e)]
        t = tix[tix.submitted_at.between(s, e + pd.Timedelta(days=1))]
        rows.append(dict(trimestre=str(q), contas=n_acc, assinaturas_ativas=n_sub, uso_total=u.usage_count.sum(),
                         uso_por_conta=round(u.usage_count.sum() / n_acc, 1), taxa_erro=round(u.error_count.sum() / u.usage_count.sum(), 3),
                         tickets=len(t), csat_medio=round(t.satisfaction_score.mean(), 2),
                         csat_sem_resposta=f"{t.satisfaction_score.isna().mean():.0%}"))
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print("Notas de satisfação existentes:", sorted(tix.satisfaction_score.dropna().unique().astype(int).tolist()),
          "| sem resposta:", f"{tix.satisfaction_score.isna().mean():.0%}")
    t.to_csv(OUT / "paradoxo_ceo.csv", index=False)
    return t


def reason_codes(chn):
    header("7. O motivo declarado de saída informa algo?")
    ct = pd.crosstab(chn.reason_code, chn.feedback_text.fillna("(vazio)"))
    p = stats.chi2_contingency(ct)[1]
    print(ct)
    print(f"reason_code x feedback_text: p={p:.2f}. Os dois campos são independentes; nenhum serve como causa.")


def predictability(acc, sub, tix, use):
    header("8. Dá para prever qual contrato novo vai sair? (validação cruzada)")
    s = sub[(sub.start_date >= REGIME) & (sub.start_date <= SNAPSHOT - pd.Timedelta(days=30))].copy()
    s["y"] = (s.churn_flag & (s.age_at_end < 30)).astype(int)
    s = s.merge(acc[["account_id", "industry", "referral_source", "country", "signup_date"]], on="account_id")
    s["dias_de_conta"] = (s.start_date - s.signup_date).dt.days
    # histórico da conta até o início da assinatura (sem vazamento de futuro)
    feats = []
    usage = use.merge(sub[["subscription_id", "account_id"]], on="subscription_id")
    for r in s[["subscription_id", "account_id", "start_date"]].itertuples():
        prev = sub[(sub.account_id == r.account_id) & (sub.start_date < r.start_date)]
        t = tix[(tix.account_id == r.account_id) & (tix.submitted_at < r.start_date) & (tix.submitted_at >= r.start_date - pd.Timedelta(days=90))]
        u = usage[(usage.account_id == r.account_id) & (usage.usage_date < r.start_date) & (usage.usage_date >= r.start_date - pd.Timedelta(days=90))]
        feats.append(dict(subscription_id=r.subscription_id, subs_anteriores=len(prev), encerradas_antes=int(prev.churn_flag.sum()),
                          tickets_90d=len(t), escalados_90d=int(t.escalation_flag.sum()), csat_90d=t.satisfaction_score.mean(),
                          uso_90d=u.usage_count.sum(), erros_90d=u.error_count.sum()))
    s = s.merge(pd.DataFrame(feats), on="subscription_id")
    cat = ["plan_tier", "billing_frequency", "industry", "referral_source", "country"]
    num = ["seats", "mrr_amount", "dias_de_conta", "subs_anteriores", "encerradas_antes", "tickets_90d", "escalados_90d",
           "csat_90d", "uso_90d", "erros_90d"]
    X = pd.concat([s[num], s[["auto_renew_flag", "is_trial", "upgrade_flag", "downgrade_flag"]].astype(int),
                   pd.get_dummies(s[cat]).astype(int)], axis=1)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED)
    auc = cross_val_score(model, X, s.y, cv=cv, scoring="roc_auc")
    rng = np.random.default_rng(SEED)
    null = [cross_val_score(model, X, rng.permutation(s.y), cv=cv, scoring="roc_auc").mean() for _ in range(10)]
    print(f"{len(s)} contratos, {s.y.sum()} saíram em <30 dias, {X.shape[1]} variáveis das 5 tabelas")
    print(f"AUC validação cruzada: {auc.mean():.3f} ± {auc.std():.3f} | AUC com rótulo embaralhado: {np.mean(null):.3f}")
    print("Leitura: AUC perto de 0,5 = as variáveis disponíveis não distinguem quem sai. O risco é a idade do contrato.")
    return auc.mean(), float(np.mean(null))


def risk_list(acc, sub, after):
    header("9. Contas em risco: MRR em contratos jovens x taxa atual por idade")
    rate = {k: ev / d for k, (d, ev) in after.items()}
    act = sub[sub.end_date.isna()].copy()
    act["idade"] = (SNAPSHOT - act.start_date).dt.days
    # probabilidade de sair nos próximos 30 dias, com a taxa diária da faixa atual (regime pós-ago/24)
    def p30(age):
        for (lo, hi) in AGE_BANDS:
            if lo <= age < hi:
                return 1 - np.exp(-rate[(lo, hi)] * 30)
    act["p_saida_30d"] = act.idade.map(p30)
    act["mrr_em_risco_30d"] = act.mrr_amount * act.p_saida_30d
    g = act.groupby("account_id").agg(mrr_ativo=("mrr_amount", "sum"), contratos_ativos=("subscription_id", "size"),
                                      contratos_ate_90d=("idade", lambda x: (x < 90).sum()),
                                      mrr_ate_90d=("mrr_amount", lambda x: x[act.loc[x.index, "idade"] < 90].sum()),
                                      mrr_em_risco_30d=("mrr_em_risco_30d", "sum"))
    g = g.join(acc.set_index("account_id")[["account_name", "industry", "country", "plan_tier", "churn_flag"]])
    g = g.sort_values("mrr_em_risco_30d", ascending=False).round(0)
    g["mrr_em_risco_30d"] = g.mrr_em_risco_30d.astype(int)
    g.to_csv(OUT / "contas_em_risco.csv")
    top = g.head(50)
    print(f"MRR ativo: {act.mrr_amount.sum():,.0f} | MRR em contratos com <90 dias: {act[act.idade < 90].mrr_amount.sum():,.0f}"
          f" ({act[act.idade < 90].mrr_amount.sum() / act.mrr_amount.sum():.0%})")
    print(f"Perda esperada nos próximos 30 dias se nada mudar: {act.mrr_em_risco_30d.sum():,.0f} de MRR")
    print(f"Top 50 contas concentram {top.mrr_em_risco_30d.sum() / g.mrr_em_risco_30d.sum():.0%} desse risco")
    print(top.head(15)[["account_name", "industry", "contratos_ate_90d", "mrr_ate_90d", "mrr_em_risco_30d"]].to_string())
    return g, act


# Paleta validada com dataviz/scripts/validate_palette.js (modo claro, superfície #fcfcfb).
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BEFORE, AFTER = "#2a78d6", "#e34948"  # antes de ago/24 / desde ago/24
SERIES3 = ["#2a78d6", "#eb6834", "#1baf7a"]


def _style(ax, title, subtitle=None):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=12, fontweight="semibold", color=INK, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=9, color=INK_2)



def charts(trend, before, after, paradox, tix_scores):
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "figure.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE})

    # 1. tendência mensal
    t = trend[trend.mes >= "2023-10"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = np.arange(len(t))
    colors = [AFTER if m >= "2024-08" else BEFORE for m in t.mes]
    ax.bar(x, t.churn_mrr_pct, width=0.55, color=colors, linewidth=0)
    for i in (t.index[t.mes == "2024-07"][0], len(t) - 1):
        ax.text(i, t.churn_mrr_pct[i] + 0.12, f"{t.churn_mrr_pct[i]:.1f}%".replace(".", ","), ha="center",
                fontsize=9, color=INK, fontweight="semibold")
    meses = "jan fev mar abr mai jun jul ago set out nov dez".split()
    labels = [f"{meses[pd.Period(m).month - 1]}/{m[2:4]}" for m in t.mes]
    ax.set_xticks(x, labels, rotation=0, fontsize=8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _style(ax, "Churn de receita por mês", "% do MRR ativo perdido no mês · azul: até jul/24 · vermelho: desde ago/24")
    fig.tight_layout(); fig.savefig(OUT / "g1_tendencia.png", dpi=170); plt.close(fig)

    # 2. idade x período
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = np.arange(len(AGE_BANDS))
    r0 = [before[b][1] / before[b][0] * 30 * 100 for b in AGE_BANDS]
    r1 = [after[b][1] / after[b][0] * 30 * 100 for b in AGE_BANDS]
    w = 0.3
    ax.bar(x - w / 2 - 0.01, r0, w, color=BEFORE, linewidth=0, label="jan/23 a jul/24")
    ax.bar(x + w / 2 + 0.01, r1, w, color=AFTER, linewidth=0, label="desde ago/24")
    for i, (a, b) in enumerate(zip(r0, r1)):
        ax.text(i + w / 2, b + 0.18, f"{b:.1f}%".replace(".", ","), ha="center", fontsize=9, color=INK, fontweight="semibold")
        ax.text(i - w / 2, a + 0.18, f"{a:.1f}%".replace(".", ","), ha="center", fontsize=8, color=INK_2)
    ax.text(0 + w / 2 + 0.22, r1[0] * 0.55, f"{r1[0] / r0[0]:.0f}x", fontsize=20, fontweight="bold", color=INK)
    ax.set_xticks(x, BAND_LABELS, fontsize=9)
    ax.set_ylim(0, max(r1) * 1.15)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(frameon=False, fontsize=9, loc="upper right", labelcolor=INK_2)
    _style(ax, "A alta está nos contratos novos", "% de contratos encerrados por mês, por idade do contrato")
    fig.tight_layout(); fig.savefig(OUT / "g2_idade.png", dpi=170); plt.close(fig)

    # 3. paradoxo: índice de uso e distribuição de CSAT
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    q = [p.replace("20", "", 1) for p in paradox.trimestre]
    for (col, lab), color in zip([("contas", "contas"), ("uso_total", "uso total"), ("uso_por_conta", "uso por conta")], SERIES3):
        idx = paradox[col] / paradox[col].iloc[0] * 100
        ax.plot(q, idx, color=color, linewidth=2, solid_capstyle="round")
        ax.scatter(q[-1], idx.iloc[-1], s=36, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(len(q) - 0.85, idx.iloc[-1], f"{lab} {idx.iloc[-1]:.0f}", va="center", fontsize=8.5, color=INK)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.set_xlim(-0.3, len(q) + 1.6)
    ax.tick_params(axis="x", labelsize=8)
    _style(ax, "Base 9x maior, uso total igual", "índice, 1º tri/23 = 100, escala log")
    ax = axes[1]
    counts = [int((tix_scores == n).sum()) for n in range(1, 6)] + [int(tix_scores.isna().sum())]
    labs = ["1", "2", "3", "4", "5", "sem\nresp."]
    ax.bar(range(6), counts, width=0.55, color=[BEFORE] * 5 + [AFTER], linewidth=0)
    for i, c in enumerate(counts):
        ax.text(i, c + 15, str(c), ha="center", fontsize=8.5, color=INK if c else MUTED)
    ax.set_xticks(range(6), labs, fontsize=8.5)
    _style(ax, "Satisfação sem notas 1 e 2", "tickets por nota de CSAT")
    fig.tight_layout(); fig.savefig(OUT / "g3_paradoxo.png", dpi=170); plt.close(fig)
    pd.DataFrame({"nota": ["1", "2", "3", "4", "5", "sem resposta"], "tickets": counts}).to_csv(OUT / "csat.csv", index=False)


def main():
    OUT.mkdir(exist_ok=True)
    acc, sub, use, tix, chn = load()
    trend = monthly_trend(sub)
    before, after = age_by_period(sub)
    mix_test(sub, before)
    segment_tests(acc, sub)
    replacement_test(sub)
    paradox = ceo_paradox(acc, sub, use, tix)
    reason_codes(chn)
    predictability(acc, sub, tix, use)
    risk_list(acc, sub, after)
    charts(trend, before, after, paradox, tix.satisfaction_score)
    print(f"\nSaídas gravadas em {OUT}")


if __name__ == "__main__":
    main()
