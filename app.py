# -*- coding: utf-8 -*-
"""
Frontera Eficiente de Proveedores (Markowitz)
---------------------------------------------
App de Streamlit que optimiza la asignación del presupuesto anual de compras
entre proveedores, tratando a cada proveedor como un "activo" cuyo
rendimiento mensual es el ahorro neto frente al costo de referencia de mercado:

    Rendimiento_t = (Costo Referencia Mercado_t - Costo Total Real_t) / Costo Referencia Mercado_t

Fuente: Base_de_datos_Gestion_Proveedores.xlsx
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from scipy.optimize import minimize

# =============================================================================
# CONFIGURACIÓN GENERAL Y ESTILO (azul / negro, Arial blanca, look FINTECH)
# =============================================================================
st.set_page_config(
    page_title="Frontera Eficiente · Proveedores",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

C = {
    "bg": "#000000",
    "panel": "#070B14",
    "panel2": "#0B1220",
    "grid": "#172238",
    "blue": "#1E6BFF",
    "blue_lt": "#4D9BFF",
    "cyan": "#00B8FF",
    "navy": "#0A2A66",
    "white": "#FFFFFF",
    "muted": "#8A97AD",
    "neg": "#FF4D6D",
}
FONT = "Arial, Helvetica, sans-serif"
BLUE_SCALE = [[0, "#050A14"], [0.35, "#0A2A66"], [0.7, "#1E6BFF"], [1, "#9CCBFF"]]
CORR_SCALE = [[0, "#C9D3E3"], [0.5, "#000000"], [1, "#1E6BFF"]]

st.markdown(
    f"""
<style>
html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, label, h1, h2, h3, h4, h5, h6,
button, input, textarea, select {{
    font-family: {FONT} !important;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
    font-family: "Material Symbols Rounded" !important;
}}
.stApp {{ background: {C['bg']}; color: {C['white']}; }}
[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #030814 0%, #000000 100%);
    border-right: 1px solid {C['grid']};
}}
[data-testid="stSidebar"] * {{ color: {C['white']}; }}
h1, h2, h3, h4, p, label, span, li {{ color: {C['white']}; }}
.block-container {{ padding-top: 1.2rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {C['grid']}; }}
.stTabs [data-baseweb="tab"] {{
    background: {C['panel']}; color: {C['muted']}; border-radius: 4px 4px 0 0;
    padding: 8px 16px; border: 1px solid {C['grid']}; border-bottom: none;
}}
.stTabs [aria-selected="true"] {{ background: {C['navy']} !important; color: {C['white']} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {C['grid']}; border-radius: 6px; }}
.stButton>button, .stDownloadButton>button {{
    background: {C['blue']}; color: {C['white']}; border: none; border-radius: 4px; font-weight: 700;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{ background: {C['blue_lt']}; color: {C['white']}; }}

/* Encabezado tipo terminal bursátil */
.hdr {{ display:flex; justify-content:space-between; align-items:flex-end;
        border-bottom: 2px solid {C['blue']}; padding-bottom: 8px; margin-bottom: 6px; }}
.hdr h1 {{ font-size: 1.75rem; margin: 0; letter-spacing: .5px; }}
.hdr .sub {{ color: {C['muted']}; font-size: .85rem; }}
.live {{ color: {C['cyan']}; font-size: .8rem; font-weight: 700; letter-spacing: 1px; }}
.live:before {{ content:"● "; }}

/* Cinta de cotizaciones */
.ticker-wrap {{ width:100%; overflow:hidden; background:{C['panel']};
               border-top:1px solid {C['grid']}; border-bottom:1px solid {C['grid']};
               padding:6px 0; margin-bottom:14px; }}
.ticker {{ display:inline-block; white-space:nowrap; padding-left:100%;
          animation: tick 60s linear infinite; font-size:.85rem; }}
.ticker span {{ margin-right: 28px; }}
@keyframes tick {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-100%); }} }}
.up {{ color:{C['cyan']}; font-weight:700; }} .dn {{ color:{C['neg']}; font-weight:700; }}
.tk {{ color:{C['white']}; font-weight:700; }}

/* Tarjetas KPI */
.kpi {{ background: linear-gradient(180deg, {C['panel2']} 0%, {C['bg']} 100%);
        border:1px solid {C['grid']}; border-left:3px solid {C['blue']};
        border-radius:6px; padding:12px 14px; height:100%; }}
.kpi .lbl {{ color:{C['muted']}; font-size:.72rem; text-transform:uppercase; letter-spacing:1px; }}
.kpi .val {{ color:{C['white']}; font-size:1.45rem; font-weight:700; margin-top:4px; }}
.kpi .sub {{ color:{C['blue_lt']}; font-size:.78rem; margin-top:2px; }}
.sec {{ color:{C['white']}; font-size:1.05rem; font-weight:700; margin:14px 0 6px 0;
        border-left:3px solid {C['blue']}; padding-left:8px; }}
.note {{ color:{C['muted']}; font-size:.8rem; }}
</style>
""",
    unsafe_allow_html=True,
)


def style_fig(fig: go.Figure, height: int = 460, title: str | None = None) -> go.Figure:
    """Aplica el tema azul/negro con tipografía Arial blanca a una figura Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=C["bg"],
        plot_bgcolor=C["panel"],
        font=dict(family=FONT, color=C["white"], size=12),
        height=height,
        margin=dict(l=50, r=20, t=50 if title else 20, b=45),
        title=dict(text=title, font=dict(size=15, color=C["white"])) if title else None,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=C["white"])),
        hoverlabel=dict(bgcolor=C["panel2"], font=dict(family=FONT, color=C["white"])),
    )
    fig.update_xaxes(gridcolor=C["grid"], zerolinecolor=C["grid"], linecolor=C["grid"])
    fig.update_yaxes(gridcolor=C["grid"], zerolinecolor=C["grid"], linecolor=C["grid"])
    return fig


def kpi(col, label: str, value: str, sub: str = "") -> None:
    col.markdown(
        f'<div class="kpi"><div class="lbl">{label}</div>'
        f'<div class="val">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def fmt_mxn(x: float) -> str:
    if abs(x) >= 1e9:
        return f"${x / 1e9:,.2f} mmd"
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.1f} M"
    return f"${x:,.0f}"


def pct(x: float, d: int = 2) -> str:
    return f"{x * 100:,.{d}f}%"


# =============================================================================
# CARGA Y PREPARACIÓN DE DATOS
# =============================================================================
DEFAULT_FILES = [
    "Base_de_datos_Gestion_Proveedores.xlsx",
    "data/Base_de_datos_Gestion_Proveedores.xlsx",
]


def _period_matrix(xls: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """Lee una hoja con Periodo en filas y proveedores en columnas; descarta notas."""
    df = pd.read_excel(xls, sheet)
    df = df.rename(columns={df.columns[0]: "Periodo"})
    df["Periodo"] = pd.to_datetime(df["Periodo"], errors="coerce")
    df = df.dropna(subset=["Periodo"]).set_index("Periodo")
    df = df[[c for c in df.columns if str(c).startswith("PRV")]]
    return df.apply(pd.to_numeric, errors="coerce")


def _parse_parametros(xls: pd.ExcelFile) -> tuple[dict, pd.DataFrame]:
    raw = pd.read_excel(xls, "Parametros", header=None)
    params: dict[str, float] = {}
    giro_rows = []
    in_giro = False
    for _, row in raw.iterrows():
        k, v = row.iloc[0], row.iloc[1]
        if isinstance(k, str) and k.strip() == "Giro" and str(v).strip() == "Código":
            in_giro = True
            continue
        if in_giro:
            if not isinstance(k, str) or k.strip() == "Totales":
                in_giro = False
                continue
            giro_rows.append(
                dict(Giro=k.strip(), Codigo=v, Min=float(row.iloc[2]),
                     Max=float(row.iloc[3]), SpreadGiro=float(row.iloc[4]))
            )
            continue
        if isinstance(k, str):
            try:
                params[k.strip()] = float(v)
            except (TypeError, ValueError):
                pass

    def find(fragment: str, default: float) -> float:
        for key, val in params.items():
            if fragment.lower() in key.lower():
                return val
        return default

    p = dict(
        presupuesto=find("Presupuesto total anual", 1.2e9),
        tasa_ref=find("Tasa de referencia promedio", 0.0988),
        w_min=find("Participación mínima por proveedor", 0.002),
        w_max=find("Participación máxima por proveedor", 0.08),
        idp_min=find("Calificación IDP mínima", 75.0),
        min_por_giro=find("Número mínimo de proveedores por giro", 2),
    )
    return p, pd.DataFrame(giro_rows)


@st.cache_data(show_spinner="Cargando base de datos…")
def load_data(file_bytes: bytes) -> dict:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    cat = pd.read_excel(xls, "Catalogo Proveedores").dropna(subset=["ID Proveedor"])
    cat = cat[cat["ID Proveedor"].astype(str).str.startswith("PRV")]
    contratos = pd.read_excel(xls, "Contratos").dropna(subset=["Anio"])
    hist = pd.read_excel(xls, "Historial Mensual").dropna(subset=["Periodo"])
    hist["Periodo"] = pd.to_datetime(hist["Periodo"], errors="coerce")
    aud = pd.read_excel(xls, "Auditoria Cumplimiento").dropna(subset=["Anio"])
    rend = _period_matrix(xls, "Matriz Rendimientos")
    tasas = _period_matrix(xls, "Tasas de aumento de precio")
    ref = pd.read_excel(xls, "Tasa Referencia").iloc[:, :2]
    ref.columns = ["Periodo", "Tasa"]
    ref["Periodo"] = pd.to_datetime(ref["Periodo"], errors="coerce")
    ref = ref.dropna().set_index("Periodo")["Tasa"].astype(float)
    params, giros = _parse_parametros(xls)
    return dict(cat=cat, contratos=contratos, hist=hist, aud=aud, rend=rend,
                tasas=tasas, ref=ref, params=params, giros=giros)


# Rangos de negocio solicitados
TASA_BUCKETS = ["Menor del 1%", "Menor del 2%", "Más del 2%"]
MONTO_BUCKETS = ["De 5,000,000 a 9,000,000", "De 10,000,000 a 49,000,000", "Más de 50,000,000"]
MONTO_FUERA = "Menor de 5,000,000 (fuera de rango)"


def bucket_tasa(x: float) -> str:
    if x < 0.01:
        return TASA_BUCKETS[0]
    if x < 0.02:
        return TASA_BUCKETS[1]
    return TASA_BUCKETS[2]


def bucket_monto(x: float) -> str:
    # Los rangos se tratan como continuos: [5M,10M), [10M,50M), [50M, ∞)
    if x < 5e6:
        return MONTO_FUERA
    if x < 10e6:
        return MONTO_BUCKETS[0]
    if x < 50e6:
        return MONTO_BUCKETS[1]
    return MONTO_BUCKETS[2]


AUD_COLS = ["Documentacion Fiscal", "Cumplimiento Contractual",
            "Facturacion Correcta", "Cumplimiento del Proceso"]


@st.cache_data(show_spinner=False)
def build_master(_d: dict, key: str, audit_basis: str, p0: str, p1: str) -> pd.DataFrame:
    """Tabla maestra por proveedor con los inputs y métricas base."""
    d = _d
    cat = d["cat"].set_index("ID Proveedor")
    m = cat[["Razon Social", "Giro", "Codigo Giro", "Criticidad", "Proveedor Unico",
             "Certificacion ISO", "Plazo Pago Dias", "Spread Riesgo Proveedor"]].copy()

    # Auditoría de cumplimiento
    aud = d["aud"]
    if audit_basis == "Promedio 2023-2025":
        a = aud.groupby("ID Proveedor")[AUD_COLS + ["No Conformidades Auditoria"]].mean()
    else:
        a = aud[aud["Anio"] == int(audit_basis)].set_index("ID Proveedor")[
            AUD_COLS + ["No Conformidades Auditoria"]]
    m = m.join(a)

    # Monto de contrato anual (último año disponible)
    co = d["contratos"]
    last = co["Anio"].max()
    m["Monto Contrato Anual"] = co[co["Anio"] == last].set_index("ID Proveedor")["Monto Contrato Anual MXN"]
    m["Rango Monto"] = m["Monto Contrato Anual"].apply(bucket_monto)

    # Periodo de análisis
    rend = d["rend"].loc[p0:p1]
    tasas = d["tasas"].loc[p0:p1]
    hist = d["hist"][(d["hist"]["Periodo"] >= p0) & (d["hist"]["Periodo"] <= p1)]

    # Tasa de aumento de precio (promedio mensual de la hoja 'Tasas de aumento de precio')
    m["Tasa Aumento Precio"] = tasas.mean()
    m["Rango Tasa"] = m["Tasa Aumento Precio"].apply(bucket_tasa)

    # Estadísticos Markowitz
    m["Rend. Mensual"] = rend.mean()
    m["Volatilidad Mensual"] = rend.std()

    # Costos reales
    g = hist.groupby("ID Proveedor")
    m["Monto Facturado"] = g["Monto Facturado MXN"].sum()
    m["Costo Real"] = g["Costo Total Real MXN"].sum()
    m["Costo Referencia"] = g["Costo Referencia Mercado MXN"].sum()
    m["Desviación Costo"] = m["Costo Real"] / m["Monto Facturado"] - 1
    m["IDP"] = g["Indice Desempeno IDP"].mean()
    m["Tasa Proveedor Anual"] = g["Tasa Proveedor Anual"].mean()

    # Riesgo de contratación (0-100, mayor = más riesgo)
    crit = m["Criticidad"].map({"Alta": 10, "Media": 5, "Baja": 0}).fillna(0)
    unico = np.where(m["Proveedor Unico"].astype(str).str.lower().str.startswith("s"), 10, 0)
    iso = np.where(m["Certificacion ISO"].astype(str).str.lower() == "ninguna", 5, 0)
    base = 100 - m[AUD_COLS].mean(axis=1)
    m["Riesgo Contratación"] = (base + crit + unico + iso
                                + 2 * m["No Conformidades Auditoria"].fillna(0)).clip(0, 100)

    # Riesgo financiero individual: VaR 95% paramétrico mensual
    m["VaR 95% Mensual"] = -(m["Rend. Mensual"] - 1.645 * m["Volatilidad Mensual"])
    return m


def nivel_riesgo(x: float, lo: float, hi: float) -> str:
    return "BAJO" if x < lo else ("MODERADO" if x < hi else "ALTO")


# =============================================================================
# MOTOR DE OPTIMIZACIÓN (MARKOWITZ)
# =============================================================================
def ledoit_wolf(X: np.ndarray) -> tuple[np.ndarray, float]:
    """Covarianza con shrinkage de Ledoit-Wolf hacia la identidad escalada.
    Necesaria porque hay más proveedores (N) que meses (T) y la muestral es singular."""
    X = X - X.mean(axis=0)
    T, N = X.shape
    S = X.T @ X / T
    mu = np.trace(S) / N
    F = mu * np.eye(N)
    d2 = np.linalg.norm(S - F, "fro") ** 2 / N
    b2 = sum(np.linalg.norm(np.outer(x, x) - S, "fro") ** 2 for x in X) / N / T**2
    b2 = min(b2, d2)
    delta = b2 / d2 if d2 > 0 else 1.0
    return (delta * F + (1 - delta) * S) * T / (T - 1), delta


class Optimizer:
    def __init__(self, mu, cov, bounds, giro_idx=None, giro_lims=None):
        self.mu, self.cov = np.asarray(mu), np.asarray(cov)
        self.n = len(mu)
        self.bounds = [bounds] * self.n
        self.cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
        if giro_idx is not None:
            for g, idx in giro_idx.items():
                lo, hi = giro_lims[g]
                self.cons.append({"type": "ineq", "fun": lambda w, i=idx, l=lo: w[i].sum() - l})
                self.cons.append({"type": "ineq", "fun": lambda w, i=idx, h=hi: h - w[i].sum()})

    def _x0(self):
        return np.full(self.n, 1 / self.n)

    def _solve(self, fun, extra=None, x0=None):
        cons = self.cons + (extra or [])
        r = minimize(fun, self._x0() if x0 is None else x0, method="SLSQP",
                     bounds=self.bounds, constraints=cons,
                     options={"maxiter": 600, "ftol": 1e-12})
        return r.x if r.success else None

    def vol(self, w):
        return float(np.sqrt(w @ self.cov @ w))

    def ret(self, w):
        return float(w @ self.mu)

    def min_var(self):
        return self._solve(lambda w: w @ self.cov @ w)

    def max_ret(self):
        return self._solve(lambda w: -w @ self.mu)

    def max_sharpe(self, rf):
        return self._solve(lambda w: -(w @ self.mu - rf) / np.sqrt(w @ self.cov @ w))

    def target(self, r, x0=None):
        return self._solve(lambda w: w @ self.cov @ w,
                           [{"type": "eq", "fun": lambda w: w @ self.mu - r}], x0)

    def frontier(self, n_pts=35):
        w0, w1 = self.min_var(), self.max_ret()
        if w0 is None or w1 is None:
            return pd.DataFrame(columns=["ret", "vol"])
        rets = np.linspace(self.ret(w0), self.ret(w1), n_pts)
        out, x0 = [], w0
        for r in rets:
            w = self.target(r, x0)
            if w is not None:
                out.append((self.ret(w), self.vol(w)))
                x0 = w
        return pd.DataFrame(out, columns=["ret", "vol"])


@st.cache_data(show_spinner=False)
def monte_carlo(mu, cov, n, seed=7):
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.full(len(mu), 0.6), n)
    r = W @ mu
    v = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    return r, v


def ols(y: np.ndarray, x: np.ndarray) -> dict:
    res = stats.linregress(x, y)
    return dict(alpha=res.intercept, beta=res.slope, r2=res.rvalue**2,
                corr=res.rvalue, p=res.pvalue, se=res.stderr)


# =============================================================================
# ENCABEZADO
# =============================================================================
st.markdown(
    '<div class="hdr"><div><h1>SUPPLIER EFFICIENT FRONTIER</h1>'
    '<div class="sub">Optimización de portafolio de proveedores · Modelo media-varianza de Markowitz</div></div>'
    '<div class="live">MODELO ACTIVO</div></div>',
    unsafe_allow_html=True,
)

# =============================================================================
# SIDEBAR · FUENTE DE DATOS E INPUTS
# =============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Fuente de datos")
    up = st.file_uploader("Base de datos Excel (.xlsx)", type=["xlsx"])
    file_bytes = None
    if up is not None:
        file_bytes = up.getvalue()
    else:
        for f in DEFAULT_FILES:
            fp = Path(__file__).parent / f
            if fp.exists():
                file_bytes = fp.read_bytes()
                st.caption(f"Usando archivo del repositorio: `{f}`")
                break

if file_bytes is None:
    st.info("Sube el archivo **Base_de_datos_Gestion_Proveedores.xlsx** en la barra lateral "
            "o colócalo en la raíz del repositorio para iniciar.")
    st.stop()

try:
    D = load_data(file_bytes)
except Exception as e:  # noqa: BLE001
    st.error(f"No fue posible leer la base de datos. Verifica que conserve las hojas originales. Detalle: {e}")
    st.stop()

P = D["params"]
periodos = list(D["rend"].index)
giros_all = sorted(D["cat"]["Giro"].dropna().unique())

with st.sidebar:
    st.markdown("### 🎯 Inputs del modelo")
    sel_giros = st.multiselect("Giro", giros_all, default=giros_all)

    st.markdown("**Auditoría de cumplimiento (puntaje mínimo 0-100)**")
    audit_basis = st.selectbox("Base de auditoría", ["Promedio 2023-2025", "2025", "2024", "2023"])
    min_fiscal = st.slider("Documentación Fiscal", 0, 100, 60)
    min_contr = st.slider("Cumplimiento Contractual", 0, 100, 60)
    min_fact = st.slider("Facturación Correcta", 0, 100, 60)
    min_proc = st.slider("Cumplimiento del Proceso", 0, 100, 60)

    st.markdown("**Tasa de aumento de precio (promedio mensual)**")
    sel_tasa = st.multiselect("Rango de tasa", TASA_BUCKETS, default=TASA_BUCKETS)

    st.markdown("**Monto del contrato anual (MXN)**")
    sel_monto = st.multiselect("Rango de monto", MONTO_BUCKETS, default=MONTO_BUCKETS)
    if st.checkbox("Incluir contratos menores a 5,000,000", value=False):
        sel_monto = sel_monto + [MONTO_FUERA]

    st.markdown("### 📐 Parámetros de optimización")
    per = st.select_slider(
        "Periodo de análisis", options=periodos, value=(periodos[0], periodos[-1]),
        format_func=lambda x: pd.Timestamp(x).strftime("%b-%Y"),
    )
    presupuesto = st.number_input("Presupuesto anual de compras (MXN)", min_value=1e6,
                                  value=float(P["presupuesto"]), step=5e7, format="%.0f")
    rf_anual = st.number_input("Tasa libre de riesgo anual (referencia)", min_value=0.0,
                               max_value=0.5, value=round(float(P["tasa_ref"]), 4),
                               step=0.0025, format="%.4f")
    w_min = st.slider("Participación mínima por proveedor", 0.0, 0.05, float(P["w_min"]), 0.001,
                      format="%.3f")
    w_max = st.slider("Participación máxima por proveedor", 0.01, 1.0, float(P["w_max"]), 0.01)
    objetivo = st.radio("Portafolio objetivo", ["Máximo Sharpe", "Mínima varianza", "Rendimiento objetivo"])
    use_giro_lims = st.checkbox("Aplicar límites de participación por giro (hoja Parámetros)", value=False)
    use_idp = st.checkbox(f"Exigir IDP mínimo ({P['idp_min']:.0f})", value=False)
    use_lw = st.checkbox("Covarianza con shrinkage Ledoit-Wolf (recomendado)", value=True)
    n_sim = st.select_slider("Portafolios simulados (Monte Carlo)", [1000, 2500, 5000, 10000], 5000)
    bench_opt = st.selectbox(
        "Índice de referencia (regresión)",
        ["Índice de mercado de proveedores (equiponderado)",
         "Índice ponderado por monto de contrato",
         "Tasa de referencia (mensual)"],
    )

p0, p1 = pd.Timestamp(per[0]), pd.Timestamp(per[1])
M = build_master(D, hashlib.md5(file_bytes).hexdigest(), audit_basis, str(p0.date()), str(p1.date()))

# =============================================================================
# FILTRO DE UNIVERSO ELEGIBLE
# =============================================================================
mask = (
    M["Giro"].isin(sel_giros)
    & (M["Documentacion Fiscal"] >= min_fiscal)
    & (M["Cumplimiento Contractual"] >= min_contr)
    & (M["Facturacion Correcta"] >= min_fact)
    & (M["Cumplimiento del Proceso"] >= min_proc)
    & M["Rango Tasa"].isin(sel_tasa)
    & M["Rango Monto"].isin(sel_monto)
)
if use_idp:
    mask &= M["IDP"] >= P["idp_min"]
U = M[mask].copy()
ids = list(U.index)
n = len(ids)

if n < 2:
    st.warning("Con los filtros actuales quedan menos de 2 proveedores elegibles. "
               "Amplía los rangos de los inputs para construir la frontera eficiente.")
    st.dataframe(M[["Razon Social", "Giro", "Rango Tasa", "Rango Monto"] + AUD_COLS], width="stretch")
    st.stop()

R = D["rend"].loc[p0:p1, ids]
if len(R) < 6:
    st.warning("Selecciona un periodo de al menos 6 meses.")
    st.stop()

mu = R.mean().values
cov_s = R.cov().values
cov, delta = ledoit_wolf(R.values) if use_lw else (cov_s, 0.0)
rf_m = rf_anual / 12

# Factibilidad de límites
lo_b = min(w_min, 1 / n)
hi_b = max(w_max, 1 / n + 1e-9)
notes = []
if lo_b != w_min:
    notes.append(f"Participación mínima ajustada a {pct(lo_b)} (hay {n} proveedores).")
if hi_b != w_max:
    notes.append(f"Participación máxima ajustada a {pct(hi_b)} para que la suma pueda llegar a 100%.")

giro_idx, giro_lims = None, None
if use_giro_lims and not D["giros"].empty:
    gl = D["giros"].set_index("Giro")
    present = U["Giro"].unique()
    giro_idx = {g: np.where(U["Giro"].values == g)[0] for g in present if g in gl.index}
    giro_lims = {g: (gl.loc[g, "Min"], gl.loc[g, "Max"]) for g in giro_idx}
    s_min = sum(v[0] for v in giro_lims.values())
    s_max = sum(v[1] for v in giro_lims.values())
    cap_ok = all(len(giro_idx[g]) * hi_b >= giro_lims[g][0] for g in giro_idx)
    if s_min > 1 or s_max < 1 or not cap_ok:
        notes.append("Los límites por giro no son factibles con la selección actual; se omitieron.")
        giro_idx, giro_lims = None, None

opt = Optimizer(mu, cov, (lo_b, hi_b), giro_idx, giro_lims)
w_mv = opt.min_var()
w_ms = opt.max_sharpe(rf_m)
if w_mv is None and giro_idx is not None:
    notes.append("No se encontró solución con límites por giro; se omitieron.")
    opt = Optimizer(mu, cov, (lo_b, hi_b))
    w_mv, w_ms = opt.min_var(), opt.max_sharpe(rf_m)
if w_mv is None:
    st.error("El optimizador no encontró solución factible. Relaja las participaciones mínima/máxima.")
    st.stop()
if w_ms is None:
    w_ms = w_mv
front = opt.frontier()
w_mr = opt.max_ret()

if objetivo == "Mínima varianza":
    w = w_mv
elif objetivo == "Máximo Sharpe":
    w = w_ms
else:
    r_lo, r_hi = opt.ret(w_mv), opt.ret(w_mr if w_mr is not None else w_mv)
    with st.sidebar:
        tgt = st.slider("Rendimiento objetivo mensual (%)", float(r_lo * 100), float(max(r_hi * 100, r_lo * 100 + 0.01)),
                        float((r_lo + r_hi) / 2 * 100), format="%.2f")
    w = opt.target(tgt / 100, w_mv)
    if w is None:
        notes.append("Rendimiento objetivo no alcanzable; se muestra el portafolio de mínima varianza.")
        w = w_mv

w = np.where(w < 1e-6, 0, w)
w = w / w.sum()
U["Peso"] = w
U["Asignación MXN"] = w * presupuesto

# =============================================================================
# MÉTRICAS DEL PORTAFOLIO
# =============================================================================
port_r = R.values @ w
exp_m = opt.ret(w)
vol_m = opt.vol(w)
sharpe = (exp_m - rf_m) / vol_m if vol_m > 0 else np.nan
var95 = -(exp_m - 1.645 * vol_m)
cvar95 = -(exp_m - vol_m * stats.norm.pdf(1.645) / 0.05)
desv_costo = float(np.sum(w * U["Desviación Costo"].fillna(0)))
riesgo_contr = float(np.sum(w * U["Riesgo Contratación"]))
spread_p = float(np.sum(w * U["Spread Riesgo Proveedor"].fillna(0)))
tasa_prov_p = float(np.sum(w * U["Tasa Proveedor Anual"].fillna(0)))
tasa_aum_p = float(np.sum(w * U["Tasa Aumento Precio"].fillna(0)))
costo_real_esp = presupuesto * (1 - exp_m)

# Índice de referencia
R_all = D["rend"].loc[p0:p1]
if bench_opt.startswith("Índice de mercado"):
    bench = R_all.mean(axis=1)
elif bench_opt.startswith("Índice ponderado"):
    wt = M["Monto Contrato Anual"].reindex(R_all.columns).fillna(0)
    bench = (R_all * (wt / wt.sum())).sum(axis=1)
else:
    bench = D["ref"].reindex(R_all.index).ffill() / 12
bench.name = "Índice"
reg = ols(port_r, bench.values)

# =============================================================================
# CINTA DE COTIZACIONES
# =============================================================================
last = D["rend"].loc[:p1].iloc[-1]
top_tk = U.sort_values("Peso", ascending=False).head(25).index
items = []
for pid in top_tk:
    v = last.get(pid, np.nan)
    cls, arrow = ("up", "▲") if v >= 0 else ("dn", "▼")
    items.append(f'<span><span class="tk">{pid}</span> <span class="{cls}">{arrow} {v * 100:+.2f}%</span></span>')
items.append(f'<span><span class="tk">PORTAFOLIO</span> <span class="{"up" if port_r[-1] >= 0 else "dn"}">'
             f'{port_r[-1] * 100:+.2f}%</span></span>')
st.markdown(f'<div class="ticker-wrap"><div class="ticker">{"".join(items)}</div></div>',
            unsafe_allow_html=True)

for t in notes:
    st.caption(f"ℹ️ {t}")

# KPI principales
k = st.columns(6)
kpi(k[0], "Rendimiento esperado", pct(exp_m), f"ahorro mensual vs mercado · {fmt_mxn(presupuesto * exp_m)}/año")
kpi(k[1], "Volatilidad (σ)", pct(vol_m), "desviación estándar mensual")
kpi(k[2], "Desviación de costo", pct(desv_costo), "Costo real vs facturado")
kpi(k[3], "Riesgo de contratación", f"{riesgo_contr:,.1f}",
    f"{nivel_riesgo(riesgo_contr, 20, 30)} · escala 0-100")
kpi(k[4], "Riesgo financiero · VaR 95%", pct(max(var95, 0)),
    f"{fmt_mxn(var95 * presupuesto / 12)} pérdida máx. / mes" if var95 > 0
    else f"sin pérdida al 95% · peor caso {pct(-var95)} de ahorro")
kpi(k[5], "Sharpe", f"{sharpe:,.3f}", f"{int((w > 0).sum())} de {n} proveedores activos")

# =============================================================================
# PESTAÑAS
# =============================================================================
tabs = st.tabs(["📈 Frontera eficiente", "💼 Portafolio óptimo", "⚠️ Riesgos y costo por giro",
                "🔗 Correlación y regresión", "🗂️ Universo de proveedores", "📘 Metodología"])

# ---------------------------------------------------------------- Frontera
with tabs[0]:
    r_mc, v_mc = monte_carlo(mu, cov, n_sim)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=v_mc * 100, y=r_mc * 100, mode="markers", name="Portafolios simulados",
        marker=dict(size=4, color=(r_mc - rf_m) / v_mc, colorscale=BLUE_SCALE, opacity=0.65,
                    colorbar=dict(title="Sharpe", tickfont=dict(color=C["white"]))),
        hovertemplate="σ %{x:.2f}%<br>Rend. %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=U["Volatilidad Mensual"] * 100, y=U["Rend. Mensual"] * 100,
        mode="markers", name="Proveedores", text=U.index + " · " + U["Giro"],
        marker=dict(size=7, color=C["white"], symbol="diamond-open", line=dict(width=1)),
        hovertemplate="%{text}<br>σ %{x:.2f}%<br>Rend. %{y:.2f}%<extra></extra>"))
    if not front.empty:
        fig.add_trace(go.Scatter(
            x=front["vol"] * 100, y=front["ret"] * 100, mode="lines",
            name="Frontera eficiente", line=dict(color=C["cyan"], width=3)))
    # Línea del mercado de capitales
    xs = np.linspace(0, max(v_mc.max(), vol_m) * 100, 50)
    s_ms = (opt.ret(w_ms) - rf_m) / opt.vol(w_ms)
    fig.add_trace(go.Scatter(x=xs, y=(rf_m * 100) + s_ms * xs, mode="lines", name="CML",
                             line=dict(color=C["blue_lt"], dash="dash", width=1.5)))
    for lbl, ww, sym in [("Mínima varianza", w_mv, "circle"), ("Máximo Sharpe", w_ms, "star"),
                         ("Seleccionado", w, "x")]:
        fig.add_trace(go.Scatter(
            x=[opt.vol(ww) * 100], y=[opt.ret(ww) * 100], mode="markers",
            name=lbl, marker=dict(size=16 if sym == "star" else 13, symbol=sym,
                                  color=C["blue"] if sym != "x" else C["white"],
                                  line=dict(color=C["white"], width=1.5))))
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.14, x=0))
    fig.update_xaxes(title="Riesgo · volatilidad mensual σ (%)")
    fig.update_yaxes(title="Rendimiento esperado mensual (%) · ahorro vs mercado")
    st.plotly_chart(style_fig(fig, 560, "Frontera eficiente de Markowitz"), width="stretch")
    if use_lw:
        st.markdown(f'<div class="note">Shrinkage Ledoit-Wolf aplicado: δ = {delta:.2f} '
                    f'({n} proveedores, {len(R)} meses).</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, lbl, ww in [(c1, "Mínima varianza", w_mv), (c2, "Máximo Sharpe", w_ms),
                         (c3, "Máximo rendimiento", w_mr if w_mr is not None else w_mv)]:
        rr, vv = opt.ret(ww), opt.vol(ww)
        kpi(col, lbl, pct(rr), f"σ {pct(vv)} · Sharpe {(rr - rf_m) / vv:.3f}")

# ---------------------------------------------------------------- Portafolio
with tabs[1]:
    act = U[U["Peso"] > 0].sort_values("Peso", ascending=False)
    c1, c2 = st.columns([3, 2])
    with c1:
        top = act.head(25).iloc[::-1]
        fig = go.Figure(go.Bar(
            x=top["Peso"] * 100, y=top.index + " · " + top["Codigo Giro"].astype(str), orientation="h",
            marker=dict(color=top["Peso"], colorscale=BLUE_SCALE),
            text=[f"{v * 100:.2f}%" for v in top["Peso"]], textposition="outside",
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>"))
        fig.update_xaxes(title="Participación (%)")
        st.plotly_chart(style_fig(fig, 620, "Participación por proveedor (top 25)"), width="stretch")
    with c2:
        gw = act.groupby("Giro")["Peso"].sum().sort_values(ascending=False)
        fig = go.Figure(go.Pie(
            labels=gw.index, values=gw.values, hole=0.6,
            marker=dict(colors=["#1E6BFF", "#00B8FF", "#0A2A66", "#4D9BFF", "#9CCBFF",
                                "#123E8C", "#2F80ED", "#5AC8FA", "#0D1B3D", "#7FB3FF"],
                        line=dict(color=C["bg"], width=2)),
            textinfo="percent", textfont=dict(color=C["white"])))
        fig.add_annotation(text=f"<b>{fmt_mxn(presupuesto)}</b><br>presupuesto", showarrow=False,
                           font=dict(color=C["white"], size=14))
        st.plotly_chart(style_fig(fig, 620, "Asignación por giro"), width="stretch")

    section("Detalle de la asignación óptima")
    show = act[["Razon Social", "Giro", "Peso", "Asignación MXN", "Rend. Mensual", "Volatilidad Mensual",
                "Desviación Costo", "Riesgo Contratación", "Tasa Aumento Precio", "Rango Monto"]].copy()
    st.dataframe(
        show.style.format({"Peso": "{:.2%}", "Asignación MXN": "${:,.0f}", "Rend. Mensual": "{:.2%}",
                           "Volatilidad Mensual": "{:.2%}", "Desviación Costo": "{:.2%}",
                           "Riesgo Contratación": "{:.1f}", "Tasa Aumento Precio": "{:.2%}"}),
        width="stretch", height=420)
    st.download_button("⬇️ Descargar asignación (CSV)", show.to_csv().encode("utf-8-sig"),
                       "asignacion_optima_proveedores.csv", "text/csv")

    section("Desempeño histórico acumulado · portafolio vs índice")
    cum = pd.DataFrame({"Portafolio": (1 + pd.Series(port_r, index=R.index)).cumprod() * 100,
                        "Índice": (1 + bench).cumprod() * 100})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum.index, y=cum["Portafolio"], name="Portafolio", fill="tozeroy",
                             line=dict(color=C["cyan"], width=2.5), fillcolor="rgba(30,107,255,0.15)"))
    fig.add_trace(go.Scatter(x=cum.index, y=cum["Índice"], name="Índice de referencia",
                             line=dict(color=C["white"], width=1.5, dash="dot")))
    fig.update_yaxes(title="Base 100", range=[cum.min().min() * 0.97, cum.max().max() * 1.02])
    st.plotly_chart(style_fig(fig, 380), width="stretch")

# ---------------------------------------------------------------- Riesgos y costos
with tabs[2]:
    k = st.columns(4)
    kpi(k[0], "CVaR 95% mensual", pct(cvar95), f"{fmt_mxn(cvar95 * presupuesto / 12)} pérdida esperada en cola")
    kpi(k[1], "Spread de riesgo ponderado", pct(spread_p), "sobre la tasa de referencia")
    kpi(k[2], "Tasa proveedor ponderada", pct(tasa_prov_p), "anual promedio del periodo")
    kpi(k[3], "Beta vs índice", f"{reg['beta']:.3f}", f"R² {reg['r2']:.2f}")

    section("Costo real por giro · asignación óptima")
    U["Costo Real Esperado"] = U["Asignación MXN"] * (1 - U["Rend. Mensual"])
    U["Costo Real Ajustado"] = U["Costo Real Esperado"] * (1 + U["Desviación Costo"].fillna(0))
    cg = U.groupby("Giro").agg(
        Proveedores=("Peso", lambda s: int((s > 0).sum())),
        Participacion=("Peso", "sum"),
        Asignacion=("Asignación MXN", "sum"),
        CostoRealEsperado=("Costo Real Esperado", "sum"),
        DesvCosto=("Desviación Costo", "mean"),
        RiesgoContr=("Riesgo Contratación", "mean"),
    )
    cg["Ahorro"] = cg["Asignacion"] - cg["CostoRealEsperado"]
    cg = cg[cg["Participacion"] > 0].sort_values("Asignacion", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Asignación (costo de referencia de mercado)", x=cg.index, y=cg["Asignacion"],
                         marker_color=C["navy"]))
    fig.add_trace(go.Bar(name="Costo real esperado", x=cg.index, y=cg["CostoRealEsperado"],
                         marker_color=C["blue"]))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="MXN")
    st.plotly_chart(style_fig(fig, 420), width="stretch")
    st.dataframe(
        cg.rename(columns={"Participacion": "Participación", "Asignacion": "Asignación MXN",
                           "CostoRealEsperado": "Costo real esperado MXN", "DesvCosto": "Desv. costo prom.",
                           "RiesgoContr": "Riesgo contratación prom.", "Ahorro": "Ahorro esperado MXN"})
        .style.format({"Participación": "{:.2%}", "Asignación MXN": "${:,.0f}",
                       "Costo real esperado MXN": "${:,.0f}", "Desv. costo prom.": "{:.2%}",
                       "Riesgo contratación prom.": "{:.1f}", "Ahorro esperado MXN": "${:,.0f}"}),
        width="stretch")

    section("Costo real histórico por giro · universo elegible")
    hg = U.groupby("Giro")[["Monto Facturado", "Costo Real", "Costo Referencia"]].sum()
    hg = hg.sort_values("Costo Real", ascending=False)
    fig = go.Figure()
    for colname, colr in [("Costo Referencia", C["navy"]), ("Monto Facturado", C["blue_lt"]),
                          ("Costo Real", C["blue"])]:
        fig.add_trace(go.Bar(name=colname, x=hg.index, y=hg[colname], marker_color=colr))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="MXN acumulado del periodo")
    st.plotly_chart(style_fig(fig, 420), width="stretch")

    section("Mapa de riesgo: contratación vs financiero")
    fig = go.Figure(go.Scatter(
        x=U["Riesgo Contratación"], y=U["VaR 95% Mensual"] * 100, mode="markers",
        text=U.index + " · " + U["Giro"],
        marker=dict(size=8 + 60 * U["Peso"] / max(U["Peso"].max(), 1e-9), color=U["Peso"],
                    colorscale=BLUE_SCALE, line=dict(color=C["white"], width=0.6),
                    colorbar=dict(title="Peso")),
        hovertemplate="%{text}<br>Riesgo contratación %{x:.1f}<br>VaR 95%% %{y:.2f}%<extra></extra>"))
    fig.add_vline(x=20, line=dict(color=C["muted"], dash="dot"))
    fig.add_vline(x=30, line=dict(color=C["neg"], dash="dot"))
    fig.update_xaxes(title="Riesgo de contratación (0-100)")
    fig.update_yaxes(title="Riesgo financiero · VaR 95% mensual (%)")
    st.plotly_chart(style_fig(fig, 460), width="stretch")

# ---------------------------------------------------------------- Correlación y regresión
with tabs[3]:
    nivel = st.radio("Nivel de la matriz de correlación", ["Por giro", "Proveedores del portafolio (top 20)"],
                     horizontal=True)
    if nivel == "Por giro":
        gm = {g: R[U.index[U["Giro"] == g]].mean(axis=1) for g in U["Giro"].unique()}
        cm = pd.DataFrame(gm)
        cm["ÍNDICE"] = bench.values
        corr = cm.corr()
    else:
        top_ids = U.sort_values("Peso", ascending=False).head(20).index
        cm = R[top_ids].copy()
        cm["ÍNDICE"] = bench.values
        corr = cm.corr()
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index, zmin=-1, zmax=1, colorscale=CORR_SCALE,
        text=np.round(corr.values, 2), texttemplate="%{text}", textfont=dict(size=10, color=C["white"]),
        colorbar=dict(title="ρ")))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig, 620, "Matriz de correlación de rendimientos"), width="stretch")

    section(f"Regresión del portafolio vs {bench_opt}")
    c1, c2 = st.columns([3, 2])
    with c1:
        xb = bench.values
        xx = np.linspace(xb.min(), xb.max(), 50)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xb * 100, y=port_r * 100, mode="markers", name="Meses",
                                 text=[d.strftime("%b-%Y") for d in R.index],
                                 marker=dict(size=9, color=C["cyan"], line=dict(color=C["white"], width=0.5)),
                                 hovertemplate="%{text}<br>Índice %{x:.2f}%<br>Portafolio %{y:.2f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=xx * 100, y=(reg["alpha"] + reg["beta"] * xx) * 100, mode="lines",
                                 name=f"y = {reg['alpha'] * 100:.3f}% + {reg['beta']:.3f}·x",
                                 line=dict(color=C["blue"], width=3)))
        fig.update_xaxes(title="Rendimiento del índice (%)")
        fig.update_yaxes(title="Rendimiento del portafolio (%)")
        st.plotly_chart(style_fig(fig, 460), width="stretch")
    with c2:
        kk = st.columns(2)
        kpi(kk[0], "Alfa (mensual)", pct(reg["alpha"], 3), "intercepto")
        kpi(kk[1], "Beta", f"{reg['beta']:.3f}", f"e.e. {reg['se']:.3f}")
        kk = st.columns(2)
        kpi(kk[0], "R²", f"{reg['r2']:.3f}", "varianza explicada")
        kpi(kk[1], "Correlación", f"{reg['corr']:.3f}", f"p-valor {reg['p']:.4f}")
        te = np.std(port_r - bench.values, ddof=1)
        ir = (port_r.mean() - bench.mean()) / te if te > 0 else np.nan
        kk = st.columns(2)
        kpi(kk[0], "Tracking error", pct(te), "mensual")
        kpi(kk[1], "Information ratio", f"{ir:.3f}", "mensual")

    section("Beta individual de los proveedores del portafolio vs índice")
    rows = []
    for pid in U.index[U["Peso"] > 0]:
        rr = ols(R[pid].values, bench.values)
        rows.append(dict(ID=pid, Giro=U.at[pid, "Giro"], Peso=U.at[pid, "Peso"], Alfa=rr["alpha"],
                         Beta=rr["beta"], R2=rr["r2"], Correlación=rr["corr"]))
    bt = pd.DataFrame(rows).set_index("ID").sort_values("Peso", ascending=False)
    fig = go.Figure(go.Bar(x=bt.index[:30], y=bt["Beta"][:30],
                           marker_color=[C["blue"] if b >= 0 else C["neg"] for b in bt["Beta"][:30]]))
    fig.add_hline(y=1, line=dict(color=C["white"], dash="dot"))
    fig.update_yaxes(title="Beta")
    st.plotly_chart(style_fig(fig, 360), width="stretch")
    st.dataframe(bt.style.format({"Peso": "{:.2%}", "Alfa": "{:.3%}", "Beta": "{:.3f}", "R2": "{:.3f}",
                                  "Correlación": "{:.3f}"}), width="stretch", height=320)

# ---------------------------------------------------------------- Universo
with tabs[4]:
    k = st.columns(4)
    kpi(k[0], "Proveedores en base", f"{len(M)}", f"{len(giros_all)} giros")
    kpi(k[1], "Elegibles tras filtros", f"{n}", f"{n / len(M):.0%} del universo")
    kpi(k[2], "Meses analizados", f"{len(R)}", f"{p0:%b-%Y} → {p1:%b-%Y}")
    kpi(k[3], "Tasa de aumento prom.", pct(tasa_aum_p), "mensual, ponderada por peso")
    cols = ["Razon Social", "Giro", "Rango Tasa", "Tasa Aumento Precio", "Rango Monto", "Monto Contrato Anual",
            *AUD_COLS, "IDP", "Rend. Mensual", "Volatilidad Mensual", "Desviación Costo", "Riesgo Contratación",
            "VaR 95% Mensual", "Spread Riesgo Proveedor"]
    view = M[cols].copy()
    view.insert(0, "Elegible", mask)
    st.dataframe(
        view.style.format({"Tasa Aumento Precio": "{:.2%}", "Monto Contrato Anual": "${:,.0f}",
                           "Documentacion Fiscal": "{:.1f}", "Cumplimiento Contractual": "{:.1f}",
                           "Facturacion Correcta": "{:.1f}", "Cumplimiento del Proceso": "{:.1f}",
                           "IDP": "{:.1f}", "Rend. Mensual": "{:.2%}", "Volatilidad Mensual": "{:.2%}",
                           "Desviación Costo": "{:.2%}", "Riesgo Contratación": "{:.1f}",
                           "VaR 95% Mensual": "{:.2%}", "Spread Riesgo Proveedor": "{:.2%}"}),
        width="stretch", height=560)
    c1, c2 = st.columns(2)
    with c1:
        vc = M["Rango Tasa"].value_counts().reindex(TASA_BUCKETS, fill_value=0)
        fig = go.Figure(go.Bar(x=vc.index, y=vc.values, marker_color=C["blue"], text=vc.values,
                               textposition="outside"))
        st.plotly_chart(style_fig(fig, 320, "Proveedores por tasa de aumento de precio"), width="stretch")
    with c2:
        vc = M["Rango Monto"].value_counts().reindex(MONTO_BUCKETS + [MONTO_FUERA], fill_value=0)
        fig = go.Figure(go.Bar(x=vc.index, y=vc.values, marker_color=C["blue"], text=vc.values,
                               textposition="outside"))
        st.plotly_chart(style_fig(fig, 320, "Proveedores por monto de contrato anual"), width="stretch")

# ---------------------------------------------------------------- Metodología
with tabs[5]:
    st.markdown(
        r"""
**Activo.** Cada proveedor es un activo. Su rendimiento mensual es el ahorro neto frente al costo de
referencia de mercado (hoja *Matriz Rendimientos*):
$r_{i,t} = \dfrac{\text{Costo ref. mercado}_{i,t} - \text{Costo total real}_{i,t}}{\text{Costo ref. mercado}_{i,t}}$

**Optimización (Markowitz).** Con el vector de rendimientos esperados $\mu$ y la matriz de covarianzas
$\Sigma$ se resuelve $\min_w \; w^\top \Sigma w$ sujeto a $w^\top \mu = r^*$, $\sum w_i = 1$ y
$w_{\min} \le w_i \le w_{\max}$ (opcionalmente límites por giro). Barriendo $r^*$ se obtiene la frontera eficiente.
El portafolio de **Máximo Sharpe** maximiza $(w^\top\mu - r_f)/\sqrt{w^\top\Sigma w}$, con $r_f$ = tasa de referencia anual / 12 (misma convención que la columna *Rendimiento Exceso* de la base).
Como hay más proveedores que meses, $\Sigma$ se estima con *shrinkage* de Ledoit-Wolf.

**Outputs**
- **Rendimiento:** $w^\top\mu$, ahorro promedio mensual sobre el costo de mercado. Como es un porcentaje sobre el gasto, no se capitaliza ×12: el ahorro anual en MXN es presupuesto × $w^\top\mu$.
- **Desviación de costo:** $\sum w_i \left(\dfrac{\text{Costo real}_i}{\text{Monto facturado}_i} - 1\right)$ — sobrecosto por incidencias,
  no calidad y penalizaciones sobre lo facturado.
- **Riesgo de contratación (0-100):** $100 - \overline{\text{auditoría}}$ (Documentación Fiscal, Cumplimiento Contractual,
  Facturación Correcta, Cumplimiento del Proceso) + criticidad (Alta 10, Media 5) + proveedor único (10) +
  sin ISO (5) + 2 × no conformidades. Bajo < 20 ≤ Moderado < 30 ≤ Alto.
- **Riesgo financiero:** volatilidad, VaR y CVaR paramétricos al 95%, spread de riesgo y tasa del proveedor ponderados,
  beta frente al índice.
- **Costo real por giro:** asignación × (1 − rendimiento esperado); se compara contra el costo de referencia.
- **Correlación y regresión:** matriz de correlación de rendimientos y regresión MCO del portafolio contra el índice
  seleccionado (alfa, beta, R², tracking error, information ratio).

**Inputs de filtrado.** Giro; puntajes mínimos de auditoría; tasa de aumento de precio (promedio mensual de la hoja
*Tasas de aumento de precio*: < 1%, 1%-2%, ≥ 2%); monto del contrato anual del último año (hoja *Contratos*).
"""
    )

st.markdown(
    f'<div class="note" style="text-align:center;margin-top:24px;border-top:1px solid {C["grid"]};padding-top:8px">'
    'Modelo media-varianza de Markowitz · Datos: Base_de_datos_Gestion_Proveedores.xlsx · '
    'Resultados con fines de análisis; no constituyen recomendación financiera.</div>',
    unsafe_allow_html=True,
)
