import streamlit as st
import pandas as pd

st.set_page_config(page_title="Audit Automation Demo", layout="wide")

st.title("Audit Automation Demo")
st.subheader("Revenue & Trade Receivables Workflow Prototype")

st.write(
    "Upload GL and TB files to generate a basic audit workflow demo."
)

st.header("1. Upload Data")

uploaded_gl = st.file_uploader("Upload Current Year GL", type=["csv", "xlsx"])
uploaded_tb = st.file_uploader("Upload Current Year TB", type=["csv", "xlsx"])
uploaded_mapping = st.file_uploader("Upload Mapping File", type=["csv", "xlsx"])

def read_file(file):
    if file is None:
        return None
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

gl_df = read_file(uploaded_gl)
tb_df = read_file(uploaded_tb)
mapping_df = read_file(uploaded_mapping)

if gl_df is not None:
    st.success("GL uploaded successfully")
    st.dataframe(gl_df.head(20), use_container_width=True)

if tb_df is not None:
    st.success("TB uploaded successfully")
    st.dataframe(tb_df.head(20), use_container_width=True)

if mapping_df is not None:
    st.success("Mapping file uploaded successfully")
    st.dataframe(mapping_df.head(20), use_container_width=True)

st.header("2. Demo Output")

if gl_df is not None and tb_df is not None and mapping_df is not None:
    st.info("Next step: generate financials, analytical review, risk indicators and sample selection.")
else:
    st.warning("Please upload GL, TB and mapping files to continue.")
