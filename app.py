import streamlit as st
import pandas as pd

st.set_page_config(page_title="Audit Automation Demo", layout="wide")

st.title("Audit Automation Demo")
st.subheader("Revenue & Trade Receivables Workflow Prototype")

st.write(
    "Upload CY/PY GL and TB files to generate a basic audit workflow demo."
)

st.header("1. Upload Data")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Current Year")
    uploaded_cy_gl = st.file_uploader("Upload Current Year GL", type=["csv", "xlsx"], key="cy_gl")
    uploaded_cy_tb = st.file_uploader("Upload Current Year TB", type=["csv", "xlsx"], key="cy_tb")

with col2:
    st.subheader("Prior Year")
    uploaded_py_gl = st.file_uploader("Upload Prior Year GL", type=["csv", "xlsx"], key="py_gl")
    uploaded_py_tb = st.file_uploader("Upload Prior Year TB", type=["csv", "xlsx"], key="py_tb")

uploaded_mapping = st.file_uploader("Upload Mapping File", type=["csv", "xlsx"], key="mapping")


def read_file(file):
    if file is None:
        return None
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


cy_gl_df = read_file(uploaded_cy_gl)
py_gl_df = read_file(uploaded_py_gl)
cy_tb_df = read_file(uploaded_cy_tb)
py_tb_df = read_file(uploaded_py_tb)
mapping_df = read_file(uploaded_mapping)


st.header("2. Uploaded Data Preview")

if cy_gl_df is not None:
    st.success("Current Year GL uploaded successfully")
    st.dataframe(cy_gl_df.head(20), use_container_width=True)

if py_gl_df is not None:
    st.success("Prior Year GL uploaded successfully")
    st.dataframe(py_gl_df.head(20), use_container_width=True)

if cy_tb_df is not None:
    st.success("Current Year TB uploaded successfully")
    st.dataframe(cy_tb_df.head(20), use_container_width=True)

if py_tb_df is not None:
    st.success("Prior Year TB uploaded successfully")
    st.dataframe(py_tb_df.head(20), use_container_width=True)

if mapping_df is not None:
    st.success("Mapping file uploaded successfully")
    st.dataframe(mapping_df.head(20), use_container_width=True)


st.header("3. Demo Output")

if (
    cy_gl_df is not None
    and py_gl_df is not None
    and cy_tb_df is not None
    and py_tb_df is not None
    and mapping_df is not None
):
    st.success("All required files uploaded. Ready to run audit workflow.")
    st.info(
        "Next step: generate CY vs PY financials, analytical review, risk indicators and sample selection."
    )
else:
    st.warning("Please upload CY GL, PY GL, CY TB, PY TB and mapping files to continue.")
