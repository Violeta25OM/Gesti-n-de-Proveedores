# 📈 Supplier Efficient Frontier · Markowitz para gestión de proveedores

Aplicación en **Streamlit** que usa el modelo media-varianza de **Markowitz** para repartir el presupuesto anual de compras entre proveedores. Cada proveedor se trata como un activo y su rendimiento es el **ahorro neto frente al costo de referencia de mercado**.

> Estilo visual: terminal bursátil / FINTECH en azul y negro, con tipografía Arial blanca.

---

## 1. Estructura del repositorio

```
├── app.py                                   # Aplicación Streamlit
├── requirements.txt                         # Dependencias
├── README.md                                # Este documento
├── Base_de_datos_Gestion_Proveedores.xlsx   # Fuente de datos (opcional en el repo)
└── .streamlit/
    └── config.toml                          # Tema oscuro azul/negro (recomendado)
```

La app carga el Excel automáticamente si está en la raíz o en `data/`. Si no lo encuentra, permite subirlo desde la barra lateral.

## 2. Fuente de datos

`Base_de_datos_Gestion_Proveedores.xlsx`: 100 proveedores, 10 giros, 36 meses (2023-2025).

| Hoja | Uso en el modelo |
|---|---|
| Parametros | Presupuesto, tasa de referencia, participación mín./máx., IDP mínimo, límites por giro |
| Catalogo Proveedores | Giro, criticidad, proveedor único, ISO, spread de riesgo |
| Contratos | Monto del contrato anual (último año) |
| Historial Mensual | Monto facturado, costo real, costo de referencia, IDP, tasa del proveedor |
| Auditoria Cumplimiento | Documentación fiscal, cumplimiento contractual, facturación correcta, cumplimiento del proceso |
| Matriz Rendimientos | Rendimientos mensuales para μ y Σ |
| Tasas de aumento de precio | Tasa mensual por proveedor, usada para clasificar |
| Tasa Referencia | Tasa libre de riesgo e índice de referencia |

## 3. Inputs (barra lateral)

| Input | Regla |
|---|---|
| **Giro** | Selección múltiple de los 10 giros |
| **Documentación Fiscal** | Puntaje mínimo 0-100 |
| **Cumplimiento Contractual** | Puntaje mínimo 0-100 |
| **Facturación Correcta** | Puntaje mínimo 0-100 |
| **Cumplimiento del Proceso** | Puntaje mínimo 0-100 |
| **Tasa de aumento de precio** | Menor del 1% · Menor del 2% (1%-2%) · Más del 2% (promedio mensual) |
| **Monto del contrato anual** | De 5,000,000 a 9,000,000 · De 10,000,000 a 49,000,000 · Más de 50,000,000 |

Los puntajes de auditoría pueden tomarse como promedio 2023-2025 o de un solo año. Los rangos de monto son continuos ([5M,10M), [10M,50M), ≥50M). Hay una casilla opcional para incluir contratos menores a 5M, que en la base son 24 proveedores.

**Parámetros de optimización:** periodo de análisis, presupuesto, tasa libre de riesgo, participación mínima y máxima por proveedor, portafolio objetivo (máximo Sharpe, mínima varianza o rendimiento objetivo), límites por giro, IDP mínimo, shrinkage Ledoit-Wolf, número de simulaciones Monte Carlo e índice de referencia.

## 4. Outputs

| Output | Definición |
|---|---|
| **Rendimiento** | wᵀμ: ahorro promedio mensual sobre el costo de mercado, en % y en MXN/año |
| **Desviación de costo** | Σ wᵢ (Costo real / Monto facturado − 1): sobrecosto por incidencias, no calidad y penalizaciones |
| **Riesgo de contratación** | Escala 0-100: 100 − promedio de auditoría + criticidad (Alta 10 / Media 5) + proveedor único (10) + sin ISO (5) + 2 × no conformidades. Bajo < 20 ≤ Moderado < 30 ≤ Alto |
| **Riesgo financiero** | Volatilidad σ, VaR y CVaR paramétricos al 95%, spread de riesgo ponderado, tasa del proveedor, beta |
| **Costo real por giro** | Asignación × (1 − rendimiento esperado) frente al costo de referencia, más el histórico facturado/real/referencia |
| **Correlación y regresión** | Matriz de correlación (por giro o por proveedor) y regresión MCO contra el índice: α, β, R², p-valor, tracking error, information ratio y beta individual |

Índices de referencia disponibles: índice de mercado equiponderado de los 100 proveedores, índice ponderado por monto de contrato y tasa de referencia mensual.

## 5. Metodología

1. **Rendimiento del activo:** `r = (Costo ref. mercado − Costo total real) / Costo ref. mercado`.
2. **Estimación:** μ = media mensual; Σ = covarianza con *shrinkage* de **Ledoit-Wolf**. Hay más proveedores (100) que meses (36), así que la covarianza muestral es singular y el shrinkage la estabiliza.
3. **Optimización (SLSQP):** `min wᵀΣw` s.a. `wᵀμ = r*`, `Σw = 1`, `w_min ≤ wᵢ ≤ w_max` y, de forma opcional, límites por giro.
4. **Frontera eficiente:** se barre r* entre el portafolio de mínima varianza y el de máximo rendimiento. Máximo Sharpe = `max (wᵀμ − r_f)/σ`, con r_f = tasa de referencia / 12.
5. **Monte Carlo:** nube de portafolios aleatorios (Dirichlet) coloreada por Sharpe.

El rendimiento se reporta **mensual** y no se anualiza ×12, porque es un porcentaje de ahorro sobre el gasto. El ahorro anual en pesos es presupuesto × wᵀμ.

## 6. Ejecución local

```bash
git clone https://github.com/<usuario>/<repo>.git
cd <repo>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 7. Despliegue en Streamlit Community Cloud

1. Sube `app.py`, `requirements.txt`, `README.md`, `.streamlit/config.toml` y, si quieres, el Excel a un repositorio de GitHub.
2. Entra a [share.streamlit.io](https://share.streamlit.io), elige **New app**, selecciona el repositorio, la rama y `app.py` como archivo principal.
3. Da clic en **Deploy**.

Si la base contiene información confidencial, no la subas al repositorio público: súbela desde la barra lateral cada vez que uses la app.

## 8. Personalización

- **Colores:** diccionario `C` al inicio de `app.py` y `.streamlit/config.toml`.
- **Ponderaciones del riesgo de contratación:** función `build_master`.
- **Rangos de tasa y monto:** funciones `bucket_tasa` y `bucket_monto`.

---
*Herramienta de análisis. Los resultados dependen de la calidad de los datos y no constituyen recomendación financiera.*
