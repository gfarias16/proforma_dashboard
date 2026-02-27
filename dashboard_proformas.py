
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard - Proformas 2026", layout="wide")

@st.cache_data
def load_data(xlsx_path: str):
    df = pd.read_excel(xlsx_path, sheet_name="master_services")
    # ensure types
    for col in ["DATA", "DATA N.F.", "MES_CONTABIL_DT"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["VALOR BRUTO BRL  - PF","VALOR BRUTO USD","VALOR FATURADO BRL","VALOR LÍQUIDO BRL","IMPOSTOS","%"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["CLIENTE","STATUS","BU","AREA"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan", np.nan)
    return df

def money(v):
    if pd.isna(v): 
        return "—"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("📊 Proformas 2026 — Dashboard (RCAL/SCAL/GEOCHEMISTRY/GEOLOGY/STORAGE-LOGISTC/PRODUCT SALES)")

xlsx_path = st.sidebar.text_input("Caminho do arquivo consolidado (.xlsx)", "PROFORMAS_2026_master_clean_dashboard_data.xlsx")
df = load_data(xlsx_path)

# Sidebar filters
st.sidebar.markdown("## Filtros")
def multiselect(col, label):
    if col not in df.columns: 
        return None
    opts = sorted([x for x in df[col].dropna().unique().tolist() if str(x).strip() != ""])
    return st.sidebar.multiselect(label, opts, default=opts)

f_area   = multiselect("AREA", "Área")
f_status = multiselect("STATUS", "Status")
f_mes    = multiselect("MES_CONTABIL", "Mês contábil")
f_bu     = multiselect("BU", "BU")
f_cli    = multiselect("CLIENTE", "Cliente")

f = df.copy()
for col, sel in [("AREA", f_area), ("STATUS", f_status), ("MES_CONTABIL", f_mes), ("BU", f_bu), ("CLIENTE", f_cli)]:
    if sel is not None and len(sel) > 0 and col in f.columns:
        f = f[f[col].isin(sel)]

# KPIs
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Linhas", f"{len(f):,}".replace(",", "."))
c2.metric("Proformas únicas", f"{f['PROFORMA'].nunique():,}".replace(",", ".") if "PROFORMA" in f else "—")
c3.metric("Clientes únicos", f"{f['CLIENTE'].nunique():,}".replace(",", ".") if "CLIENTE" in f else "—")
c4.metric("Bruto (BRL)", money(f["VALOR BRUTO BRL  - PF"].sum(min_count=1) if "VALOR BRUTO BRL  - PF" in f else np.nan))
c5.metric("Bruto (USD)", money(f["VALOR BRUTO USD"].sum(min_count=1) if "VALOR BRUTO USD" in f else np.nan))
c6.metric("Líquido (BRL)", money(f["VALOR LÍQUIDO BRL"].sum(min_count=1) if "VALOR LÍQUIDO BRL" in f else np.nan))

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Financeiro", "Operacional", "Dados (tabela)"])

with tab1:
    left, right = st.columns([1.2, 1])

    with left:
        if "MES_CONTABIL_DT" in f.columns and "VALOR BRUTO BRL  - PF" in f.columns:
            ts = (f.dropna(subset=["MES_CONTABIL_DT"])
                    .groupby(pd.Grouper(key="MES_CONTABIL_DT", freq="MS"))["VALOR BRUTO BRL  - PF"]
                    .sum()
                    .reset_index())
            fig = px.line(ts, x="MES_CONTABIL_DT", y="VALOR BRUTO BRL  - PF", markers=True, title="Bruto (BRL) por mês contábil")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não encontrei colunas suficientes para série temporal (MES_CONTABIL_DT + VALOR BRUTO BRL).")

    with right:
        if "AREA" in f.columns and "VALOR BRUTO BRL  - PF" in f.columns:
            area = f.groupby("AREA")["VALOR BRUTO BRL  - PF"].sum().reset_index().sort_values("VALOR BRUTO BRL  - PF", ascending=False)
            fig = px.bar(area, x="AREA", y="VALOR BRUTO BRL  - PF", title="Bruto (BRL) por área")
            st.plotly_chart(fig, use_container_width=True)
        if "STATUS" in f.columns:
            stt = f["STATUS"].value_counts(dropna=False).reset_index()
            stt.columns=["STATUS","qtd"]
            fig = px.pie(stt, names="STATUS", values="qtd", title="Distribuição por status")
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    a, b = st.columns(2)
    with a:
        if "CLIENTE" in f.columns and "VALOR BRUTO BRL  - PF" in f.columns:
            top = (f.groupby("CLIENTE")["VALOR BRUTO BRL  - PF"].sum()
                     .reset_index()
                     .sort_values("VALOR BRUTO BRL  - PF", ascending=False)
                     .head(15))
            fig = px.bar(top, x="CLIENTE", y="VALOR BRUTO BRL  - PF", title="Top 15 clientes por Bruto (BRL)")
            fig.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Colunas CLIENTE e VALOR BRUTO BRL  - PF não encontradas.")

    with b:
        cols = [c for c in ["VALOR BRUTO BRL  - PF","IMPOSTOS","VALOR LÍQUIDO BRL"] if c in f.columns]
        if len(cols) >= 2:
            x = st.selectbox("Eixo X", cols, index=0)
            y = st.selectbox("Eixo Y", cols, index=1)
            fig = px.scatter(f, x=x, y=y, color="AREA" if "AREA" in f.columns else None,
                             hover_data=["CLIENTE","PROFORMA","STATUS"] if all(c in f.columns for c in ["CLIENTE","PROFORMA","STATUS"]) else None,
                             title=f"Relação: {x} vs {y}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Poucas colunas numéricas para gráfico de dispersão.")

    st.markdown("### Alerta de consistência")
    if "VALOR LÍQUIDO BRL" in f.columns and "VALOR BRUTO BRL  - PF" in f.columns and "IMPOSTOS" in f.columns:
        # regra aproximada: liquido ≈ bruto - impostos (pode variar pelo negócio)
        check = f.dropna(subset=["VALOR BRUTO BRL  - PF","IMPOSTOS","VALOR LÍQUIDO BRL"]).copy()
        if len(check):
            check["delta"] = check["VALOR LÍQUIDO BRL"] - (check["VALOR BRUTO BRL  - PF"] - check["IMPOSTOS"])
            worst = check.reindex(check["delta"].abs().sort_values(ascending=False).index).head(10)
            st.dataframe(worst[["AREA","PROFORMA","CLIENTE","MES_CONTABIL","VALOR BRUTO BRL  - PF","IMPOSTOS","VALOR LÍQUIDO BRL","delta","STATUS"]], use_container_width=True)
        else:
            st.info("Sem linhas completas para checagem (Bruto/Impostos/Líquido).")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        if "BU" in f.columns and "VALOR BRUTO BRL  - PF" in f.columns:
            bu = f.groupby("BU")["VALOR BRUTO BRL  - PF"].sum().reset_index().sort_values("VALOR BRUTO BRL  - PF", ascending=False)
            fig = px.bar(bu, x="BU", y="VALOR BRUTO BRL  - PF", title="Bruto (BRL) por BU")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Colunas BU e/ou VALOR BRUTO BRL não encontradas.")

    with c2:
        # aging simples (dias desde DATA)
        if "DATA" in f.columns:
            today = pd.Timestamp.today().normalize()
            tmp = f.dropna(subset=["DATA"]).copy()
            tmp["aging_dias"] = (today - tmp["DATA"]).dt.days
            fig = px.histogram(tmp, x="aging_dias", title="Aging (dias desde DATA)", nbins=30)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Coluna DATA não encontrada para aging.")

with tab4:
    st.markdown("### Dados filtrados")
    st.dataframe(f, use_container_width=True, height=520)

    st.download_button(
        "Baixar CSV (dados filtrados)",
        f.to_csv(index=False).encode("utf-8"),
        file_name="proformas_filtradas.csv",
        mime="text/csv"
    )

st.caption("Dica: se o app não achar o arquivo, coloque o caminho correto no campo da sidebar.")
