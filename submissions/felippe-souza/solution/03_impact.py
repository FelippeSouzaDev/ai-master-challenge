"""Fase 3: impacto estimado das recomendações.

Pergunta: quanto MRR a empresa recupera se o primeiro trimestre do contrato voltar
ao padrão de antes de ago/24? Usa as mesmas taxas por idade de 02_analysis.py.

Uso:
    python solution/03_impact.py
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("analysis", ROOT / "02_analysis.py")
an = importlib.util.module_from_spec(spec)
spec.loader.exec_module(an)


def main():
    acc, sub, use, tix, chn = an.load()
    before = an.exposure_by_band(sub, pd.Timestamp("2023-01-01"), an.REGIME - pd.Timedelta(days=1))
    after = an.exposure_by_band(sub, an.REGIME, an.SNAPSHOT)
    r_before = {k: ev / d for k, (d, ev) in before.items()}
    r_after = {k: ev / d for k, (d, ev) in after.items()}

    # 1. Quanto do MRR perdido entre ago e dez/24 é excesso sobre o padrão antigo?
    lost = sub[sub.churn_flag & (sub.end_date >= an.REGIME)]
    excess_events = 0.0
    for m in pd.period_range("2024-08", "2024-12", freq="M"):
        ex = an.exposure_by_band(sub, m.start_time, m.end_time.normalize())
        excess_events += sum(ev - d * r_before[k] for k, (d, ev) in ex.items())
    avg_mrr = lost.mrr_amount.mean()
    print(f"MRR perdido ago-dez/24: {lost.mrr_amount.sum():,.0f} em {len(lost)} contratos")
    print(f"Excesso sobre o padrão anterior: {excess_events:.0f} contratos ≈ {excess_events * avg_mrr:,.0f} de MRR"
          f" ({excess_events / len(lost):.0%} do perdido)")

    # 2. Daqui para frente: perda mensal esperada no regime atual x regime antigo, com a carteira de hoje
    act = sub[sub.end_date.isna()].copy()
    act["idade"] = (an.SNAPSHOT - act.start_date).dt.days

    def loss(rates, months=3):
        """MRR perdido em N meses, envelhecendo a carteira atual mês a mês (sem vendas novas)."""
        total, mrr, age = 0.0, act.mrr_amount.to_numpy(dtype=float), act.idade.to_numpy()
        for _ in range(months):
            p = np.zeros(len(age))
            for (lo, hi), r in rates.items():
                p[(age >= lo) & (age < hi)] = 1 - np.exp(-r * 30)
            total += (mrr * p).sum()
            mrr, age = mrr * (1 - p), age + 30
        return total

    cur, old = loss(r_after), loss(r_before)
    half = {k: (r_after[k] + r_before[k]) / 2 for k in r_after}
    mid = loss(half)
    print(f"\nPerda nos próximos 3 meses, carteira atual, sem vendas novas:")
    print(f"  regime atual:              {cur:,.0f}")
    print(f"  metade do caminho de volta:{mid:,.0f}  (recupera {cur - mid:,.0f})")
    print(f"  padrão pré-ago/24:          {old:,.0f}  (recupera {cur - old:,.0f})")

    # 3. Vendas novas: no ritmo de dez/24 (953 contratos/mês), quanto MRR novo se perde no 1º trimestre?
    new = sub[sub.start_date >= "2024-12-01"]
    surv_after = np.exp(-(r_after[(0, 30)] * 30 + r_after[(30, 90)] * 60))
    surv_before = np.exp(-(r_before[(0, 30)] * 30 + r_before[(30, 90)] * 60))
    mrr_new = new.mrr_amount.sum()
    print(f"\nMRR vendido em dez/24: {mrr_new:,.0f}")
    print(f"  sobrevive aos 90 dias no regime atual: {surv_after:.1%} | no padrão antigo: {surv_before:.1%}")
    print(f"  MRR novo perdido por safra mensal: {mrr_new * (1 - surv_after):,.0f} atual x {mrr_new * (1 - surv_before):,.0f} antigo")
    print(f"  diferença por safra: {mrr_new * (surv_before - surv_after):,.0f} de MRR "
          f"(≈ {mrr_new * (surv_before - surv_after) * 12:,.0f} de ARR)")

    # 4. Capacidade: quantas contas por semana a fila de implantação exige
    g = pd.read_csv(ROOT / "output" / "contas_em_risco.csv")
    cum = g.mrr_em_risco_30d.cumsum() / g.mrr_em_risco_30d.sum()
    cover = {}
    for share in (0.5, 0.8):
        cover[share] = int((cum < share).sum()) + 1
        print(f"Contas para cobrir {share:.0%} do risco de 30 dias: {cover[share]}")

    # Números consumidos pelo relatório HTML (04_report.py)
    impact = dict(mrr_perdido_regime=float(lost.mrr_amount.sum()), contratos_perdidos_regime=int(len(lost)),
                  excesso_mrr=float(excess_events * avg_mrr), excesso_pct=float(excess_events / len(lost)),
                  perda_3m_atual=float(cur), perda_3m_metade=float(mid), perda_3m_antigo=float(old),
                  mrr_vendido_dez=float(mrr_new), sobrevivencia_90d_atual=float(surv_after),
                  sobrevivencia_90d_antigo=float(surv_before), ganho_por_safra=float(mrr_new * (surv_before - surv_after)),
                  contas_50pct=cover[0.5], contas_80pct=cover[0.8],
                  mrr_ativo=float(act.mrr_amount.sum()), mrr_ate_90d=float(act[act.idade < 90].mrr_amount.sum()),
                  risco_30d=float(g.mrr_em_risco_30d.sum()))
    (ROOT / "output" / "impacto.json").write_text(json.dumps(impact, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
