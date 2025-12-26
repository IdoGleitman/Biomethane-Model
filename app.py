import streamlit as st
import pandas as pd
import numpy_financial as npf
import matplotlib.pyplot as plt

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Biomethane Pro-Forma", layout="wide")

db = {
    "Cow Manure": {"yield": 45, "ch4": 0.55, "cost": -5.0}, 
    "Food Waste": {"yield": 150, "ch4": 0.62, "cost": -25.0},
    "Maize Silage": {"yield": 210, "ch4": 0.52, "cost": 45.0},
    "Industrial Fats": {"yield": 450, "ch4": 0.70, "cost": -10.0}
}

# --- 2. UI: SIDEBAR ---
with st.sidebar:
    st.header("Global Project Settings")
    gas_price = st.number_input("Biomethane Price ($/m3)", value=1.05)
    co2_price = st.number_input("CO2 Price ($/ton)", value=50.0)
    capex = st.number_input("Total CAPEX ($)", value=5000000, step=100000)
    
    st.header("Financing")
    debt_pct = st.slider("Debt Fraction (%)", 0, 80, 60) / 100
    interest_rate = st.slider("Interest Rate (%)", 3.0, 12.0, 7.0) / 100
    loan_years = st.slider("Loan Term (Years)", 5, 20, 10)

# --- 3. UI: MAIN PAGE ---
st.title("🌱 Biomethane Investment Assessment Tool")
st.subheader("Feedstock Configuration")

cols = st.columns(4)
active_data = []

# Dynamic Feedstock Rows
for i, name in enumerate(db.keys()):
    with cols[i]:
        enabled = st.checkbox(f"Use {name}", value=(i==0), key=f"en_{i}")
        if enabled:
            tons = st.number_input(f"Tons/yr", value=5000, key=f"t_{i}")
            cost = st.number_input(f"Cost $/t", value=db[name]['cost'], key=f"c_{i}")
            active_data.append({'tons': tons, 'cost': cost, 'yield': db[name]['yield'], 'ch4': db[name]['ch4']})

# --- 4. CALCULATION ENGINE ---
total_raw = sum(f['tons'] * f['yield'] for f in active_data)
total_ch4 = sum(f['tons'] * f['yield'] * f['ch4'] for f in active_data) * 0.98
total_co2 = (total_raw * 0.40) * 0.00198 * 0.90 

rev_gas = total_ch4 * gas_price
rev_co2 = total_co2 * co2_price
gate_fees = sum(abs(f['tons'] * f['cost']) for f in active_data if f['cost'] < 0)
purchase_costs = sum(f['tons'] * f['cost'] for f in active_data if f['cost'] > 0)

opex_base = 150000 + (total_raw * 0.12)
ebitda = (rev_gas + rev_co2 + gate_fees) - (opex_base + purchase_costs)

loan_amount = capex * debt_pct
annual_debt = npf.pmt(interest_rate, loan_years, -loan_amount) if loan_amount > 0 else 0
cash_flow = ebitda - annual_debt

# --- 5. RESULTS ---
st.divider()
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Annual EBITDA", f"${ebitda:,.0f}")
kpi2.metric("Project IRR", f"{npf.irr([-capex] + [ebitda]*15)*100:.2f}%")
kpi3.metric("Net Cash Flow", f"${cash_flow:,.0f}")

st.write("### Annual Profit & Loss Statement")
pnl = {
    "Revenue: Gas & CO2": rev_gas + rev_co2,
    "Revenue: Gate Fees": gate_fees,
    "Expenses: Feedstock & OPEX": -(purchase_costs + opex_base),
    "**EBITDA**": ebitda,
    "Debt Service": -annual_debt,
    "**Pre-Tax Cash Flow**": cash_flow
}
st.table(pd.Series(pnl, name="Amount ($)"))
