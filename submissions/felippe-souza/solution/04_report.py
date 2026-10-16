"""Gera solution/output/relatorio.html: relatório executivo + fila de risco num arquivo só.

O HTML é autocontido (sem servidor, sem internet, sem bibliotecas externas): os dados vão
embutidos como JSON e os gráficos são SVG desenhados no próprio navegador, com tooltip
e tabela de dados em cada um. Rodar depois de 02_analysis.py e 03_impact.py.

Uso:
    python solution/04_report.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
TEMPLATE = ROOT / "report_template.html"


def pct(s):
    return float(str(s).rstrip("%")) / 100


def main():
    trend = pd.read_csv(OUT / "tendencia_mensal.csv")
    age = pd.read_csv(OUT / "taxa_por_idade.csv")
    mix = pd.read_csv(OUT / "mix_esperado_vs_observado.csv")
    par = pd.read_csv(OUT / "paradoxo_ceo.csv")
    csat = pd.read_csv(OUT / "csat.csv")
    seg = pd.read_csv(OUT / "segmentos_precoce.csv")
    risk = pd.read_csv(OUT / "contas_em_risco.csv")
    impact = json.loads((OUT / "impacto.json").read_text(encoding="utf-8"))

    t = trend[trend.mes >= "2023-10"]
    data = {
        "trend": [dict(mes=r.mes, pct=r.churn_mrr_pct / 100, perdido=r.mrr_perdido, ativo=r.mrr_ativo,
                       novos=r.assinaturas_novas) for r in t.itertuples()],
        "age": [dict(faixa=r.idade, antes=pct(r.taxa_antes), depois=pct(r.taxa_depois), n_antes=r.n_antes,
                     n_depois=r.n_depois, mult=r.multiplicador, p=r.p_valor) for r in age.itertuples()],
        "mix": [dict(mes=r.mes, obs=r.observado, esp=r.esperado_pelo_mix, razao=r.razao, p=r.p_valor) for r in mix.itertuples()],
        "paradox": [dict(q=r.trimestre, contas=r.contas, uso=r.uso_total, uso_conta=r.uso_por_conta,
                         csat=r.csat_medio, sem_resp=r.csat_sem_resposta) for r in par.itertuples()],
        "csat": csat.to_dict("records"),
        "segments": seg.to_dict("records"),
        "risk": risk[["account_id", "account_name", "industry", "country", "contratos_ativos", "contratos_ate_90d",
                      "mrr_ativo", "mrr_ate_90d", "mrr_em_risco_30d"]].to_dict("records"),
        "impact": impact,
    }
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    (OUT / "relatorio.html").write_text(html, encoding="utf-8")
    print(f"Relatório gravado em {OUT / 'relatorio.html'} ({len(data['risk'])} contas na fila)")


if __name__ == "__main__":
    main()
