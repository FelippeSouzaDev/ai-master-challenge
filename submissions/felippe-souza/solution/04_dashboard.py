"""Gera solution/output/painel-risco.html: painel autocontido para o time de CS.

O painel abre direto no navegador, sem servidor e sem internet. Mostra os KPIs do diagnóstico,
os gráficos e a fila de contas em risco, com filtros por setor e país e busca por nome.
Rodar depois de 02_analysis.py, toda semana, com o dado novo.

Uso:
    python solution/04_dashboard.py
"""
import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"


def img(name):
    return "data:image/png;base64," + base64.b64encode((OUT / name).read_bytes()).decode()


def main():
    risk = pd.read_csv(OUT / "contas_em_risco.csv")
    age = pd.read_csv(OUT / "taxa_por_idade.csv")
    trend = pd.read_csv(OUT / "tendencia_mensal.csv")
    last = trend.iloc[-1]
    rows = risk[["account_id", "account_name", "industry", "country", "contratos_ativos",
                 "contratos_ate_90d", "mrr_ativo", "mrr_ate_90d", "mrr_em_risco_30d"]].to_dict("records")
    kpis = [
        ("Churn de receita em dez/24", f"{last.churn_mrr_pct:.1f}%".replace(".", ","), "do MRR ativo; era 0,6% em jul/24"),
        ("1º mês do contrato", age.iloc[0].taxa_depois.replace(".", ","), f"ao mês desde ago/24; antes {age.iloc[0].taxa_antes}".replace(".", ",")),
        ("Base madura (180+ dias)", age.iloc[3].taxa_depois.replace(".", ","), "ao mês; não mudou"),
        ("MRR em risco, 30 dias", f"US$ {risk.mrr_em_risco_30d.sum() / 1000:,.0f} mil", "se nada mudar"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="k-label">{a}</div><div class="k-val">{b}</div>'
                       f'<div class="k-note">{c}</div></div>' for a, b, c in kpis)
    html = TEMPLATE.replace("{{KPIS}}", kpi_html).replace("{{DATA}}", json.dumps(rows)) \
        .replace("{{G1}}", img("g1_tendencia.png")).replace("{{G2}}", img("g2_idade.png")) \
        .replace("{{G3}}", img("g3_paradoxo.png"))
    (OUT / "painel-risco.html").write_text(html, encoding="utf-8")
    print(f"Painel gravado em {OUT / 'painel-risco.html'} ({len(rows)} contas)")


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de Risco RavenStack</title>
<style>
:root { --bg:#f7f7f5; --card:#ffffff; --text:#1f2937; --muted:#6b7280; --line:#e5e7eb; --accent:#b91c1c; --bar:#fecaca; }
@media (prefers-color-scheme: dark) { :root { --bg:#111214; --card:#1b1d21; --text:#e5e7eb; --muted:#9ca3af; --line:#2d3036; --accent:#f87171; --bar:#5b2323; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:16px; margin:32px 0 12px; }
.sub { color:var(--muted); margin:0 0 20px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
.kpi, .card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px 16px; }
.k-label { color:var(--muted); font-size:12px; } .k-val { font-size:26px; font-weight:650; color:var(--accent); }
.k-note { color:var(--muted); font-size:12px; }
.charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:12px; }
.charts img { width:100%; height:auto; background:#fff; border-radius:4px; }
.filters { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:10px; }
select, input { font:inherit; padding:6px 8px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--text); }
input { flex:1; min-width:160px; }
.tablewrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
th, td { padding:7px 8px; border-bottom:1px solid var(--line); text-align:right; white-space:nowrap; }
th { color:var(--muted); font-weight:500; font-size:12px; cursor:pointer; user-select:none; }
th:nth-child(-n+3), td:nth-child(-n+3) { text-align:left; }
td.risk { position:relative; } td.risk span { position:relative; z-index:1; }
td.risk::before { content:""; position:absolute; right:0; top:4px; bottom:4px; width:var(--w); background:var(--bar); border-radius:3px; }
.summary { color:var(--muted); margin:8px 0 0; }
.howto { color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<main>
<h1>Painel de risco de churn</h1>
<p class="sub">RavenStack · dado até 31/12/2024 · gerado por <code>solution/04_dashboard.py</code></p>
<div class="kpis">{{KPIS}}</div>

<h2>Fila de implantação: quem ligar primeiro</h2>
<p class="howto">Ordenado pelo MRR que deve sair nos próximos 30 dias, aplicando a taxa atual por idade a cada contrato ativo.
O risco vem da idade do contrato, não do perfil do cliente: nenhum segmento difere dos outros. Comece pelo topo;
em contas com vários contratos jovens, confira se a implantação de cada um começou.</p>
<div class="card">
  <div class="filters">
    <input id="q" placeholder="Buscar conta" aria-label="Buscar conta">
    <select id="ind" aria-label="Setor"><option value="">Todos os setores</option></select>
    <select id="cty" aria-label="País"><option value="">Todos os países</option></select>
    <select id="top" aria-label="Quantidade"><option value="81">Top 81 (50% do risco)</option><option value="222">Top 222 (80%)</option><option value="1000">Todas</option></select>
  </div>
  <div class="tablewrap"><table>
    <thead><tr>
      <th data-k="account_name">Conta</th><th data-k="industry">Setor</th><th data-k="country">País</th>
      <th data-k="contratos_ate_90d">Contratos &lt;90d</th><th data-k="mrr_ate_90d">MRR &lt;90d</th><th data-k="mrr_ativo">MRR ativo</th>
      <th data-k="mrr_em_risco_30d">MRR em risco 30d ▼</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
  <p class="summary" id="sum"></p>
</div>

<h2>Por que a fila é por idade do contrato</h2>
<div class="charts">
  <div class="card"><img src="{{G2}}" alt="Taxa de encerramento por idade do contrato antes e depois de ago/24"></div>
  <div class="card"><img src="{{G1}}" alt="Churn de receita mensal"></div>
  <div class="card"><img src="{{G3}}" alt="Uso por conta e distribuição de satisfação"></div>
</div>
</main>
<script>
const DATA = {{DATA}};
const fmt = v => "US$ " + Math.round(v).toLocaleString("pt-BR");
const $ = id => document.getElementById(id);
let sortKey = "mrr_em_risco_30d", sortDir = -1;
for (const [id, k] of [["ind", "industry"], ["cty", "country"]]) {
  [...new Set(DATA.map(r => r[k]))].sort().forEach(v => $(id).add(new Option(v, v)));
}
function render() {
  const q = $("q").value.toLowerCase(), ind = $("ind").value, cty = $("cty").value, top = +$("top").value;
  const ranked = DATA.slice(0, top);
  const rows = ranked.filter(r => (!ind || r.industry === ind) && (!cty || r.country === cty) &&
    (!q || r.account_name.toLowerCase().includes(q) || r.account_id.toLowerCase().includes(q)))
    .sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0) * sortDir);
  const max = Math.max(...DATA.map(r => r.mrr_em_risco_30d));
  $("rows").innerHTML = rows.map(r => `<tr><td>${r.account_name}</td><td>${r.industry}</td><td>${r.country}</td>
    <td>${r.contratos_ate_90d}</td><td>${fmt(r.mrr_ate_90d)}</td><td>${fmt(r.mrr_ativo)}</td>
    <td class="risk" style="--w:${(r.mrr_em_risco_30d / max * 100).toFixed(0)}%"><span>${fmt(r.mrr_em_risco_30d)}</span></td></tr>`).join("");
  const tot = rows.reduce((s, r) => s + r.mrr_em_risco_30d, 0);
  $("sum").textContent = `${rows.length} contas · ${fmt(tot)} de MRR em risco nos próximos 30 dias`;
}
document.querySelectorAll("th").forEach(th => th.onclick = () => {
  const k = th.dataset.k; sortDir = k === sortKey ? -sortDir : -1; sortKey = k;
  document.querySelectorAll("th").forEach(h => h.textContent = h.textContent.replace(/ [▲▼]$/, ""));
  th.textContent += sortDir < 0 ? " ▼" : " ▲"; render();
});
["q", "ind", "cty", "top"].forEach(id => $(id).oninput = render);
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
