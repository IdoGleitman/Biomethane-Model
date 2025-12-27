import streamlit as st
import pandas as pd
import numpy_financial as npf
import plotly.graph_objects as go # NEW: Using Plotly for better interactive charts

st.set_page_config(page_title="Biogas Investment Master", layout="wide")

# --- 1. SIDEBAR: PROJECT OVERHEAD ---
with st.sidebar:
    st.header("🏢 Acquisition & Construction")
    purchase_price = st.number_input("Plant Purchase Price ($)", value=2000000, step=100000)
    construction_capex = st.number_input("Retrofit/Construction CAPEX ($)", value=3000000, step=100000)
    total_investment = purchase_price + construction_capex
    st.info(f"Total Initial Investment: ${total_investment:,.0f}")

    st.header("⚙️ Operational Assumptions")
    fixed_opex = st.number_input("Annual Fixed OPEX ($)", value=180000)
    var_opex_rate = st.slider("Var OPEX ($/m3 raw gas)", 0.05, 0.25, 0.11)
    
    st.header("💰 Market Prices")
    gas_price = st.number_input("Gas Sale Price ($/m3)", value=1.05)
    co2_price = st.number_input("CO2 Sale Price ($/ton)", value=45.0)

# --- 2. MAIN: FEEDSTOCK BUILDER ---
st.title("🌱 Biomethane Project: Advanced Financial Model")
st.subheader("1. Feedstock Inventory & Yields")

rows = []
c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
c1.caption("Feedstock Name")
c2.caption("Tons/yr")
c3.caption("Yield (m3/t)")
c4.caption("CH4 %")
c5.caption("Cost ($/t)")

for i in range(4):
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    name = f1.text_input("", value=f"FS {i+1}", key=f"n{i}", label_visibility="collapsed")
    tons = f2.number_input("", value=5000 if i==0 else 0, key=f"t{i}", label_visibility="collapsed")
    y_val = f3.number_input("", value=100, key=f"y{i}", label_visibility="collapsed")
    m_pct = f4.number_input("", value=55, key=f"m{i}", label_visibility="collapsed") / 100
    f_cost = f5.number_input("", value=0.0, key=f"c{i}", label_visibility="collapsed")
    if tons > 0:
        rows.append({'tons': tons, 'yield': y_val, 'ch4': m_pct, 'cost': f_cost})

# --- 3. CORE CALCULATION ENGINE ---
def calculate_ebitda(g_p_adj, f_o_adj, v_o_r_adj, f_p_adj, total_inv_adj):
    """Calculates EBITDA based on adjusted inputs for sensitivity"""
    t_raw = sum(r['tons'] * r['yield'] for r in rows)
    t_ch4 = sum(r['tons'] * r['yield'] * r['ch4'] for r in rows) * 0.98
    t_co2 = (t_raw - (t_ch4/0.98)) * 0.00198 * 0.90
    
    rev = (t_ch4 * g_p_adj) + (t_co2 * co2_price) # CO2 price is not sensitive in this function
    
    f_costs_actual = sum(r['tons'] * (r['cost'] * f_p_adj) for r in rows)
    g_fees = abs(f_costs_actual) if f_costs_actual < 0 else 0
    p_costs = f_costs_actual if f_costs_actual > 0 else 0
    
    total_op = f_o_adj + (t_raw * v_o_r_adj) # Use adjusted fixed and var opex rate
    return (rev + g_fees) - (p_costs + total_op)

# Base Case for Calculations
base_ebitda = calculate_ebitda(gas_price, fixed_opex, var_opex_rate, 1.0, total_investment)

# --- 4. SENSITIVITY ANALYSIS ---
st.divider()
st.subheader("2. Sensitivity Analysis (EBITDA Impact)")

sens_range_pct = [-0.20, -0.10, 0, 0.10, 0.20]
sens_data = []

for pct in sens_range_pct:
    label = f"{pct*100:+.0f}%"
    sens_data.append({
        "Change": label,
        "Gas Price": calculate_ebitda(gas_price*(1+pct), fixed_opex, var_opex_rate, 1.0, total_investment),
        "Fixed OPEX": calculate_ebitda(gas_price, fixed_opex*(1+pct), var_opex_rate, 1.0, total_investment),
        "Var OPEX Rate": calculate_ebitda(gas_price, fixed_opex, var_opex_rate*(1+pct), 1.0, total_investment),
        "Feedstock Cost": calculate_ebitda(gas_price, fixed_opex, var_opex_rate, (1+pct), total_investment),
        "Total Investment (IRR Impact)": total_investment * (1+pct) # This impacts IRR, not directly EBITDA
    })

df_sens = pd.DataFrame(sens_data).set_index("Change")
st.table(df_sens.style.format("${:,.0f}"))


# --- 5. TORNADO CHART ---
st.subheader("3. Tornado Chart: Key Impact Factors on EBITDA")

# Calculate min/max EBITDA for each variable for the Tornado Chart
tornado_data = {}
# Base case (0% change) for comparison
base_ebitda_val = df_sens.loc['+0%']['Gas Price'] # All 0% values should be the same
for col in ['Gas Price', 'Fixed OPEX', 'Var OPEX Rate', 'Feedstock Cost']:
    ebitda_minus_20 = df_sens.loc['-20%'][col]
    ebitda_plus_20 = df_sens.loc['+20%'][col]
    impact_range = ebitda_plus_20 - ebitda_minus_20
    
    tornado_data[col] = {
        'min_ebitda': ebitda_minus_20,
        'max_ebitda': ebitda_plus_20,
        'impact_range': impact_range
    }

# Sort by impact range (descending)
sorted_tornado = sorted(tornado_data.items(), key=lambda item: item[1]['impact_range'], reverse=True)

labels = [item[0] for item in sorted_tornado]
# For the plot, we want the deviation from the base case
low_values = [base_ebitda_val - item[1]['min_ebitda'] for item in sorted_tornado]
high_values = [item[1]['max_ebitda'] - base_ebitda_val for item in sorted_tornado]

fig = go.Figure()

for i in range(len(labels)):
    fig.add_trace(go.Bar(
        y=[labels[i]],
        x=[-low_values[i]], # Negative for left side of chart (lower EBITDA)
        name=f'-20% {labels[i]}',
        orientation='h',
        marker_color='red'
    ))
    fig.add_trace(go.Bar(
        y=[labels[i]],
        x=[high_values[i]], # Positive for right side of chart (higher EBITDA)
        name=f'+20% {labels[i]}',
        orientation='h',
        marker_color='green'
    ))

fig.update_layout(
    barmode='relative',
    title='Tornado Chart: EBITDA Sensitivity (+/-20% Change)',
    xaxis_title='EBITDA Deviation from Base Case ($)',
    yaxis_title='Parameter',
    yaxis={'categoryorder':'total ascending'}, # Keep the largest impact at the top
    showlegend=False,
    height=400
)

st.plotly_chart(fig, use_container_width=True)


# --- 6. FINAL METRICS ---
st.divider()
col_pnl, col_met = st.columns([2, 1])

with col_pnl:
    st.write("### Project Summary (Base Case)")
    st.write(f"**Annual EBITDA:** ${base_ebitda:,.0f}")
    st.write(f"**Total Capital Outlay:** ${total_investment:,.0f}")

with col_met:
    # Need to handle potential for non-real IRR (e.g., all negative cash flows)
    irr = None
    try:
        irr = npf.irr([-total_investment] + [base_ebitda] * 15)
    except ValueError:
        pass # IRR calculation can fail if cash flows don't cross zero

    st.metric("Project IRR (15 yr)", f"{irr*100:.2f}%" if irr is not None else "N/A")
    st.metric("Simple Payback", f"{total_investment/base_ebitda:.1f} years" if base_ebitda > 0 else "N/A")
