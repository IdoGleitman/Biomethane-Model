import streamlit as st
import pandas as pd
import numpy_financial as npf

st.set_page_config(page_title="Custom Biogas Builder", layout="wide")

# --- 1. SIDEBAR: GLOBAL SETTINGS ---
with st.sidebar:
    st.header("Project Financials")
    capex = st.number_input("Total CAPEX ($)", value=5000000)
    # NEW: Editable Base OPEX field
    base_opex = st.number_input("Annual Fixed OPEX ($)", value=180000, help="Labor, Insurance, Maintenance")
    variable_opex_rate = st.slider("Variable OPEX ($/m3 raw biogas)", 0.05, 0.25, 0.11)
    
    st.header("Market Rates")
    gas_price = st.number_input("Gas Sale Price ($/m3)", value=1.05)
    co2_price = st.number_input("CO2 Sale Price ($/ton)", value=45.0)

# --- 2. MAIN UI: CUSTOM FEEDSTOCK BUILDER ---
st.title("🚜 Custom Biomethane Plant Builder")
st.write("Define your own feedstocks below. Set cost to **negative** for Gate Fees (Income).")

# We create 4 slots for custom feedstocks
rows = []
st.subheader("Feedstock Inventory")
head1, head2, head3, head4, head5 = st.columns([2, 1, 1, 1, 1])
head1.write("**Feedstock Name**")
head2.write("**Tons/yr**")
head3.write("**Yield (m3/t)**")
head4.write("**CH4 %**")
head5.write("**Cost ($/t)**")

# Create 4 rows of inputs
for i in range(4):
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
    name = c1.text_input(f"Name {i+1}", value=f"Feedstock {i+1}", key=f"n{i}")
    tons = c2.number_input(f"Tons", value=0, key=f"t{i}")
    yield_val = c3.number_input(f"Yield", value=100, key=f"y{i}")
    methane = c4.slider(f"CH4%", 40, 75, 55, key=f"m{i}") / 100
    cost = c5.number_input(f"Cost", value=0.0, key=f"c{i}")
    
    if tons > 0:
        rows.append({'tons': tons, 'yield': yield_val, 'ch4': methane, 'cost': cost})

# --- 3. UPDATED CALCULATION ENGINE ---
total_raw_m3 = sum(r['tons'] * r['yield'] for r in rows)
total_ch4_m3 = sum(r['tons'] * r['yield'] * r['ch4'] for r in rows) * 0.98
total_co2_tons = (total_raw_m3 - (total_ch4_m3/0.98)) * 0.00198 * 0.90

# P&L Breakdown
rev_gas = total_ch4_m3 * gas_price
rev_co2 = total_co2_tons * co2_price

# Split Feedstock logic: Income (Gate Fees) vs Expense (Purchases)
gate_fee_income = sum(abs(r['tons'] * r['cost']) for r in rows if r['cost'] < 0)
feedstock_expense = sum(r['tons'] * r['cost'] for r in rows if r['cost'] > 0)

# OPEX logic: Fixed (from slider) + Variable (based on gas volume)
var_opex_total = total_raw_m3 * variable_opex_rate
total_opex = base_opex + var_opex_total

ebitda = (rev_gas + rev_co2 + gate_fee_income) - (feedstock_expense + total_opex)

# --- 4. THE CLEAN P&L VIEW ---
st.divider()
st.subheader("📊 Annual Profit & Loss (PnL)")

pnl_data = {
    "Revenue Streams": ["Biomethane Sales", "CO2 Sales", "Gate Fee Income", "**Gross Revenue**"],
    "Value ($)": [rev_gas, rev_co2, gate_fee_income, (rev_gas + rev_co2 + gate_fee_income)],
    "Operating Expenses": ["Feedstock Purchases", "Fixed Plant OPEX", "Variable OPEX (Power/Maint)", "**Total Expenses**"],
    "Cost ($)": [-feedstock_expense, -base_opex, -var_opex_total, -(feedstock_expense + total_opex)]
}

# Displaying as two clean columns
col_rev, col_exp = st.columns(2)
with col_rev:
    df_rev = pd.DataFrame({"Item": pnl_data["Revenue Streams"], "Amount": pnl_data["Value ($)"]})
    st.dataframe(df_rev.style.format({"Amount": "${:,.0f}"}), use_container_width=True, hide_index=True)

with col_exp:
    df_exp = pd.DataFrame({"Item": pnl_data["Operating Expenses"], "Amount": pnl_data["Cost ($)"]})
    st.dataframe(df_exp.style.format({"Amount": "${:,.0f}"}), use_container_width=True, hide_index=True)

st.metric("FINAL ANNUAL EBITDA", f"${ebitda:,.0f}", delta=f"{ (ebitda/capex)*100:.1f}% Yield on CAPEX")
