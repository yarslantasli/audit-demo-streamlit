import streamlit as st
import pandas as pd
from pypdf import PdfReader
import re

st.set_page_config(page_title="Audit Automation Demo", layout="wide")

st.title("Audit Automation Demo")
st.subheader("Revenue & Trade Receivables Workflow Prototype")

st.write(
    "Upload CY/PY GL, CY/PY TB and Mapping files to generate a basic audit workflow demo."
)

# -----------------------------
# Helper functions
# -----------------------------

def read_file(file):
    if file is None:
        return None
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


def format_amount(x):
    try:
        return f"£{x:,.0f}"
    except Exception:
        return x


def get_balance_column(df, year_type):
    if year_type == "CY":
        possible_cols = ["CY_Balance", "Balance", "Amount"]
    else:
        possible_cols = ["PY_Balance", "Balance", "Amount"]

    for col in possible_cols:
        if col in df.columns:
            return col

    return None


# -----------------------------
# 1. Upload Data
# -----------------------------

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

cy_gl_df = read_file(uploaded_cy_gl)
py_gl_df = read_file(uploaded_py_gl)
cy_tb_df = read_file(uploaded_cy_tb)
py_tb_df = read_file(uploaded_py_tb)
mapping_df = read_file(uploaded_mapping)


# -----------------------------
# 2. Uploaded Data Preview
# -----------------------------

st.header("2. Uploaded Data Preview")

if cy_gl_df is not None:
    st.success("Current Year GL uploaded successfully")
    st.dataframe(cy_gl_df.head(10), use_container_width=True)

if py_gl_df is not None:
    st.success("Prior Year GL uploaded successfully")
    st.dataframe(py_gl_df.head(10), use_container_width=True)

if cy_tb_df is not None:
    st.success("Current Year TB uploaded successfully")
    st.dataframe(cy_tb_df.head(10), use_container_width=True)

if py_tb_df is not None:
    st.success("Prior Year TB uploaded successfully")
    st.dataframe(py_tb_df.head(10), use_container_width=True)

if mapping_df is not None:
    st.success("Mapping file uploaded successfully")
    st.dataframe(mapping_df.head(10), use_container_width=True)


# -----------------------------
# 3. Run Audit Workflow
# -----------------------------

st.header("3. Run Audit Workflow")

all_files_uploaded = (
    cy_gl_df is not None
    and py_gl_df is not None
    and cy_tb_df is not None
    and py_tb_df is not None
    and mapping_df is not None
)

if not all_files_uploaded:
    st.warning("Please upload CY GL, PY GL, CY TB, PY TB and mapping files to continue.")
    st.stop()

st.success("All required files uploaded. Audit workflow is ready.")

run_workflow = st.button("Run Audit Workflow")

if run_workflow:

    # -----------------------------
    # Financials / Movement
    # -----------------------------

    st.header("4. CY vs PY Financial Movement")

    cy_balance_col = get_balance_column(cy_tb_df, "CY")
    py_balance_col = get_balance_column(py_tb_df, "PY")

    if cy_balance_col is None or py_balance_col is None:
        st.error("Could not identify CY/PY balance columns. Please check TB files.")
        st.stop()

    cy_tb = cy_tb_df.copy()
    py_tb = py_tb_df.copy()

    cy_tb = cy_tb.rename(columns={cy_balance_col: "CY_Balance"})
    py_tb = py_tb.rename(columns={py_balance_col: "PY_Balance"})

    movement = (
        mapping_df[["Account_Code", "Account_Name", "FS_Line", "Statement", "Audit_Area"]]
        .merge(cy_tb[["Account_Code", "CY_Balance"]], on="Account_Code", how="left")
        .merge(py_tb[["Account_Code", "PY_Balance"]], on="Account_Code", how="left")
    )

    movement["CY_Balance"] = movement["CY_Balance"].fillna(0)
    movement["PY_Balance"] = movement["PY_Balance"].fillna(0)
    movement["Movement"] = movement["CY_Balance"] - movement["PY_Balance"]

    movement["Movement_%"] = movement.apply(
        lambda row: 0 if row["PY_Balance"] == 0 else row["Movement"] / abs(row["PY_Balance"]),
        axis=1,
    )

    fs_movement = (
        movement.groupby(["FS_Line", "Statement", "Audit_Area"], as_index=False)
        .agg({"CY_Balance": "sum", "PY_Balance": "sum", "Movement": "sum"})
    )

    fs_movement["Movement_%"] = fs_movement.apply(
        lambda row: 0 if row["PY_Balance"] == 0 else row["Movement"] / abs(row["PY_Balance"]),
        axis=1,
    )

    st.dataframe(
        fs_movement.style.format({
            "CY_Balance": "£{:,.0f}",
            "PY_Balance": "£{:,.0f}",
            "Movement": "£{:,.0f}",
            "Movement_%": "{:.1%}",
        }),
        use_container_width=True,
    )

    # -----------------------------
    # Quarterly Revenue Trend
    # -----------------------------

    st.header("5. Quarterly Revenue Trend")

    cy_gl = cy_gl_df.copy()
    py_gl = py_gl_df.copy()

    cy_gl["Date"] = pd.to_datetime(cy_gl["Date"])
    py_gl["Date"] = pd.to_datetime(py_gl["Date"])

    cy_gl = cy_gl.merge(mapping_df[["Account_Code", "FS_Line", "Audit_Area"]], on="Account_Code", how="left")
    py_gl = py_gl.merge(mapping_df[["Account_Code", "FS_Line", "Audit_Area"]], on="Account_Code", how="left")

    cy_revenue = cy_gl[cy_gl["Audit_Area"] == "Revenue"].copy()
    py_revenue = py_gl[py_gl["Audit_Area"] == "Revenue"].copy()

    cy_revenue["Quarter"] = "Q" + cy_revenue["Date"].dt.quarter.astype(str)
    py_revenue["Quarter"] = "Q" + py_revenue["Date"].dt.quarter.astype(str)

    cy_quarter = cy_revenue.groupby("Quarter", as_index=False)["Credit"].sum().rename(columns={"Credit": "CY_Revenue"})
    py_quarter = py_revenue.groupby("Quarter", as_index=False)["Credit"].sum().rename(columns={"Credit": "PY_Revenue"})

    quarter_trend = py_quarter.merge(cy_quarter, on="Quarter", how="outer").fillna(0)
    quarter_trend["Movement"] = quarter_trend["CY_Revenue"] - quarter_trend["PY_Revenue"]
    quarter_trend["Movement_%"] = quarter_trend.apply(
        lambda row: 0 if row["PY_Revenue"] == 0 else row["Movement"] / row["PY_Revenue"],
        axis=1,
    )

    st.dataframe(
        quarter_trend.style.format({
            "PY_Revenue": "£{:,.0f}",
            "CY_Revenue": "£{:,.0f}",
            "Movement": "£{:,.0f}",
            "Movement_%": "{:.1%}",
        }),
        use_container_width=True,
    )

    st.bar_chart(quarter_trend.set_index("Quarter")[["PY_Revenue", "CY_Revenue"]])

    # -----------------------------
    # Analytical Review Draft
    # -----------------------------

    st.header("6. Analytical Review Draft")

    revenue_row = fs_movement[fs_movement["Audit_Area"] == "Revenue"]
    ar_row = fs_movement[fs_movement["Audit_Area"] == "Trade Receivables"]

    if not revenue_row.empty:
        revenue_cy = revenue_row["CY_Balance"].iloc[0]
        revenue_py = revenue_row["PY_Balance"].iloc[0]
        revenue_mov = revenue_row["Movement"].iloc[0]
        revenue_mov_pct = revenue_row["Movement_%"].iloc[0]
    else:
        revenue_cy = revenue_py = revenue_mov = revenue_mov_pct = 0

    if not ar_row.empty:
        ar_cy = ar_row["CY_Balance"].iloc[0]
        ar_py = ar_row["PY_Balance"].iloc[0]
        ar_mov = ar_row["Movement"].iloc[0]
        ar_mov_pct = ar_row["Movement_%"].iloc[0]
    else:
        ar_cy = ar_py = ar_mov = ar_mov_pct = 0

    q4_row = quarter_trend[quarter_trend["Quarter"] == "Q4"]
    q4_comment = ""

    if not q4_row.empty:
        q4_cy = q4_row["CY_Revenue"].iloc[0]
        total_cy_rev = quarter_trend["CY_Revenue"].sum()
        q4_share = q4_cy / total_cy_rev if total_cy_rev != 0 else 0
        q4_comment = f" Q4 revenue represents approximately {q4_share:.1%} of total CY revenue, indicating seasonality or a year-end concentration of revenue."

    analytical_review_text = f"""
Revenue increased from {format_amount(revenue_py)} to {format_amount(revenue_cy)}, representing a movement of {format_amount(revenue_mov)} / {revenue_mov_pct:.1%}. 
Trade receivables increased from {format_amount(ar_py)} to {format_amount(ar_cy)}, representing a movement of {format_amount(ar_mov)} / {ar_mov_pct:.1%}.{q4_comment}

Based on the movement analysis, revenue and trade receivables should be considered key audit focus areas. 
Further audit procedures should consider revenue occurrence, cut-off and trade receivables recoverability.
"""

    st.info(analytical_review_text)

    # -----------------------------
    # Materiality - Basic Demo
    # -----------------------------

    st.header("7. Materiality - Basic Demo")

    total_revenue = abs(revenue_cy)
    materiality_revenue_1pct = total_revenue * 0.01
    performance_materiality = materiality_revenue_1pct * 0.75
    trivial_threshold = materiality_revenue_1pct * 0.05

    materiality_table = pd.DataFrame({
        "Metric": ["Revenue", "Overall Materiality - 1% of Revenue", "Performance Materiality - 75%", "Trivial Threshold - 5%"],
        "Amount": [total_revenue, materiality_revenue_1pct, performance_materiality, trivial_threshold],
    })

    st.dataframe(
        materiality_table.style.format({"Amount": "£{:,.0f}"}),
        use_container_width=True,
    )

    st.info(
        "For demo purposes, materiality has been calculated as 1% of revenue. "
        "In a real audit workflow, the system would calculate multiple benchmarks and the auditor would approve the final benchmark."
    )

    # -----------------------------
    # Risk Indicators
    # -----------------------------

    st.header("8. Risk Indicators")

    risk_indicators = []

    if abs(revenue_mov_pct) > 0.2:
        risk_indicators.append({
            "Area": "Revenue",
            "Indicator": f"Revenue movement is {revenue_mov_pct:.1%}",
            "Suggested Risk": "Revenue may be misstated due to significant fluctuation.",
            "Assertion": "Occurrence / Cut-off",
            "Suggested Procedure": "Perform revenue sample testing and year-end cut-off testing.",
        })

    if abs(ar_mov_pct) > abs(revenue_mov_pct):
        risk_indicators.append({
            "Area": "Trade Receivables",
            "Indicator": "Trade receivables increased faster than revenue.",
            "Suggested Risk": "Recoverability risk over receivables.",
            "Assertion": "Valuation",
            "Suggested Procedure": "Test aged receivables and inspect post-year-end cash receipts.",
        })

    manual_revenue_journals = cy_revenue[
        cy_revenue["Journal_Type"].astype(str).str.contains("Manual", case=False, na=False)
    ]

    if len(manual_revenue_journals) > 0:
        risk_indicators.append({
            "Area": "Revenue",
            "Indicator": f"{len(manual_revenue_journals)} manual revenue journal lines identified.",
            "Suggested Risk": "Manual postings to revenue may indicate management override or cut-off risk.",
            "Assertion": "Occurrence / Cut-off",
            "Suggested Procedure": "Select manual revenue journals for testing.",
        })

    risk_df = pd.DataFrame(risk_indicators)

    if risk_df.empty:
        st.success("No risk indicators identified based on the demo rules.")
    else:
        st.dataframe(risk_df, use_container_width=True)

    # -----------------------------
    # Sample Selection
    # -----------------------------

    st.header("9. Revenue Sample Selection")

    cy_revenue_samples = cy_revenue.copy()

    # Only credit revenue lines
    cy_revenue_samples = cy_revenue_samples[cy_revenue_samples["Credit"] > 0]

    high_value_samples = cy_revenue_samples.sort_values("Credit", ascending=False).head(5).copy()
    high_value_samples["Selection_Reason"] = "High value revenue item"

    manual_samples = cy_revenue_samples[
        cy_revenue_samples["Journal_Type"].astype(str).str.contains("Manual", case=False, na=False)
    ].head(5).copy()
    manual_samples["Selection_Reason"] = "Manual revenue journal"

    year_end_samples = cy_revenue_samples[
        cy_revenue_samples["Date"].dt.month == 12
    ].sort_values("Credit", ascending=False).head(5).copy()
    year_end_samples["Selection_Reason"] = "Year-end revenue cut-off"

    sample_df = pd.concat([high_value_samples, manual_samples, year_end_samples], ignore_index=True)
    sample_df = sample_df.drop_duplicates(subset=["Journal_ID", "Account_Code", "Amount"], keep="first")

    sample_columns = [
        "Journal_ID",
        "Date",
        "Account_Code",
        "Account_Name",
        "Description",
        "Customer",
        "Invoice_No",
        "Credit",
        "Journal_Type",
        "Selection_Reason",
    ]

    available_cols = [col for col in sample_columns if col in sample_df.columns]
    sample_df = sample_df[available_cols]

    st.dataframe(
        sample_df.style.format({"Credit": "£{:,.0f}"}),
        use_container_width=True,
    )

    st.success("Demo workflow completed.")
        # -----------------------------
    # Supporting Document Upload & Comparison
    # -----------------------------

    st.header("10. Supporting Document Upload & GL Comparison")

    st.write(
        "Upload fake invoice PDFs for the selected revenue samples. "
        "The system will extract invoice number, customer, date and net amount, then compare them to the GL sample."
    )

    uploaded_supporting_docs = st.file_uploader(
        "Upload Supporting Invoice PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="supporting_docs",
    )

    def extract_pdf_text(pdf_file):
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text

    def extract_invoice_fields(text):
        invoice_no = None
        customer = None
        invoice_date = None
        net_amount = None

        invoice_match = re.search(r"(INV-\d{2}-\d{5})", text)
        if invoice_match:
            invoice_no = invoice_match.group(1)

        customer_match = re.search(r"Customer:\s*(Customer\s+[A-Z])", text)
        if customer_match:
            customer = customer_match.group(1)

        date_match = re.search(r"Invoice Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
        if date_match:
            invoice_date = date_match.group(1)

        amount_match = re.search(r"Net Amount:\s*£?([0-9,]+(?:\.[0-9]{2})?)", text)
        if amount_match:
            net_amount = float(amount_match.group(1).replace(",", ""))

        return {
            "Extracted_Invoice_No": invoice_no,
            "Extracted_Customer": customer,
            "Extracted_Date": invoice_date,
            "Extracted_Net_Amount": net_amount,
        }

    if uploaded_supporting_docs:
        extraction_results = []

        for pdf_file in uploaded_supporting_docs:
            pdf_text = extract_pdf_text(pdf_file)
            extracted = extract_invoice_fields(pdf_text)
            extracted["Uploaded_File"] = pdf_file.name
            extraction_results.append(extracted)

        extracted_df = pd.DataFrame(extraction_results)

        st.subheader("Extracted Supporting Document Data")
        st.dataframe(extracted_df, use_container_width=True)

        comparison_df = sample_df.copy()

        comparison_df["Invoice_No_Clean"] = comparison_df["Invoice_No"].astype(str).str.strip()
        extracted_df["Extracted_Invoice_No_Clean"] = extracted_df["Extracted_Invoice_No"].astype(str).str.strip()

        comparison_df = comparison_df.merge(
            extracted_df,
            left_on="Invoice_No_Clean",
            right_on="Extracted_Invoice_No_Clean",
            how="left",
        )

        comparison_df["GL_Date"] = pd.to_datetime(comparison_df["Date"]).dt.date.astype(str)
        comparison_df["GL_Amount"] = comparison_df["Credit"].astype(float)

        comparison_df["Invoice_Number_Match"] = comparison_df["Invoice_No"] == comparison_df["Extracted_Invoice_No"]
        comparison_df["Customer_Match"] = comparison_df["Customer"] == comparison_df["Extracted_Customer"]
        comparison_df["Date_Match"] = comparison_df["GL_Date"] == comparison_df["Extracted_Date"]
        comparison_df["Amount_Match"] = comparison_df["GL_Amount"].round(2) == comparison_df["Extracted_Net_Amount"].round(2)

        comparison_df["Overall_Result"] = comparison_df.apply(
            lambda row: "No exception noted"
            if row["Invoice_Number_Match"]
            and row["Customer_Match"]
            and row["Date_Match"]
            and row["Amount_Match"]
            else "Exception / review required",
            axis=1,
        )

        display_cols = [
            "Journal_ID",
            "Invoice_No",
            "Customer",
            "GL_Date",
            "GL_Amount",
            "Extracted_Invoice_No",
            "Extracted_Customer",
            "Extracted_Date",
            "Extracted_Net_Amount",
            "Invoice_Number_Match",
            "Customer_Match",
            "Date_Match",
            "Amount_Match",
            "Overall_Result",
            "Uploaded_File",
        ]

        st.subheader("GL vs Supporting Document Comparison")
        st.dataframe(
            comparison_df[display_cols].style.format({
                "GL_Amount": "£{:,.0f}",
                "Extracted_Net_Amount": "£{:,.0f}",
            }),
            use_container_width=True,
        )

        st.subheader("Draft Workpaper Documentation")

        for _, row in comparison_df.iterrows():
            st.markdown(f"### Sample: {row['Journal_ID']} / {row['Invoice_No']}")

            if row["Overall_Result"] == "No exception noted":
                note = f"""
We inspected invoice {row['Extracted_Invoice_No']} for {row['Extracted_Customer']}, dated {row['Extracted_Date']}, with a net amount of £{row['Extracted_Net_Amount']:,.0f}. 
The invoice number, customer, date and amount agree to the selected GL revenue transaction. 
No exception noted.
"""
            else:
                issues = []

                if not row["Invoice_Number_Match"]:
                    issues.append("invoice number does not agree")
                if not row["Customer_Match"]:
                    issues.append("customer name does not agree")
                if not row["Date_Match"]:
                    issues.append("invoice date does not agree")
                if not row["Amount_Match"]:
                    issues.append("invoice amount does not agree")

                issue_text = ", ".join(issues)

                note = f"""
We inspected the supporting document uploaded for selected revenue transaction {row['Journal_ID']} / {row['Invoice_No']}. 
The system identified the following issue(s): {issue_text}. 
Auditor review is required to determine whether this represents a genuine exception or requires further client follow-up.
"""

            st.info(note)

    else:
        st.warning("No supporting invoice PDFs uploaded yet.")
    st.success("Demo workflow completed.")
