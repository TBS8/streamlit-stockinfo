import plotly.express as px
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diversification Tool", layout="wide")
st.title("📊 Investment Diversification Tool")

# Strategy definitions
strategy_weights = {
    "Puma": {"Property Lending (Low)": 1.0},
    "Time": {"Property Lending (High)": 0.5, "Renewables (Low)": 0.5},
    "Octopus": {"Company Investing (High)": 0.5, "Forestry (High)": 0.5},
    "Downing": {"Property Lending (Low)": 1/3, "Renewables (Low)": 1/3, "Forestry (High)": 1/3}
}

strategy_labels = {
    "Puma": "100% Property Lending (Low Risk)",
    "Time": "50% Property Lending (High Risk), 50% Renewables (Low Risk)",
    "Octopus": "50% Company Investing (High Risk), 50% Forestry (High Risk)",
    "Downing": "33% Property Lending (Low Risk), 33% Renewables (Low Risk), 33% Forestry (High Risk)"
}

def format_currency(val):
    return f"£{val:,.0f}"

def allocate_strategy(strategy_name, strategy_amount, total_investment):
    firms = []
    for firm, weights in strategy_weights.items():
        for strat in weights:
            base = strat.split(" (")[0]
            risk = "Low" if "Low" in strat else "High"
            if base == strategy_name:
                firms.append((firm, risk))

    base_weights = {}
    for firm, risk in firms:
        if firm == "Puma" and strategy_name == "Property Lending" and risk == "Low":
            base_weights[firm] = 1.15
        else:
            base_weights[firm] = 1.0

    total_weight = sum(base_weights.values())
    allocations = {firm: strategy_amount * (base_weights[firm] / total_weight) for firm in base_weights}

    max_puma = 0.5 * total_investment
    if allocations.get("Puma", 0) > max_puma:
        excess = allocations["Puma"] - max_puma
        allocations["Puma"] = max_puma
        others = [f for f in allocations if f != "Puma"]
        total_base = sum(base_weights[f] for f in others)
        for f in others:
            allocations[f] += excess * (base_weights[f] / total_base)

    exposure = {strategy_name: {"Low": 0, "High": 0}}
    for firm, risk in firms:
        exposure[strategy_name][risk] += allocations[firm]

    return allocations, exposure

def allocate_by_risk_options(risk_type, risk_amount, total_investment):
    options = []
    for firm, weights in strategy_weights.items():
        for strat in weights:
            base = strat.split(" (")[0]
            risk = "Low" if "Low" in strat else "High"
            if risk == risk_type:
                options.append((firm, base, risk))

    biased_options = []
    for firm, base, risk in options:
        if firm == "Puma" and base == "Property Lending" and risk == "Low":
            biased_options.append((firm, base, risk, 1.15))
        else:
            biased_options.append((firm, base, risk, 1.0))

    total_weight = sum(opt[3] for opt in biased_options)
    puma_weight = next((opt[3] for opt in biased_options if opt[0] == "Puma" and opt[1] == "Property Lending" and opt[2] == "Low"), 0)
    puma_allocation = risk_amount * (puma_weight / total_weight)
    puma_allocation = min(puma_allocation, 0.5 * total_investment)

    remaining_amount = risk_amount - puma_allocation
    other_options = [opt for opt in biased_options if not (opt[0] == "Puma" and opt[1] == "Property Lending" and opt[2] == "Low")]
    per_option = remaining_amount / len(other_options)

    allocation = {}
    strategy_exposure = {}

    for firm, base, risk, _ in biased_options:
        if firm == "Puma" and base == "Property Lending" and risk == "Low":
            alloc = puma_allocation
        else:
            alloc = per_option

        allocation[firm] = allocation.get(firm, 0) + alloc
        strategy_exposure.setdefault(base, {"Low": 0, "High": 0})
        strategy_exposure[base][risk] += alloc

    return allocation, strategy_exposure

# Mode selector with reset
mode = st.radio("Choose input mode", ["Product Exposure", "Risk Exposure"], key="mode_selector")
if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode
elif st.session_state.last_mode != mode:
    st.session_state.last_mode = mode
    st.rerun()

# Investment input
amount = st.number_input("Enter investment amount (£)", min_value=0.0, value=10000.0)

allocation = {}
strategy_exposure = {}

if mode == "Product Exposure":
    col1, col2 = st.columns(2)
    with col1:
        property_pct = st.number_input("Property Lending %", min_value=0, max_value=100, value=30)
        renewables_pct = st.number_input("Renewables %", min_value=0, max_value=100, value=30)
    with col2:
        company_pct = st.number_input("Company Investing %", min_value=0, max_value=100, value=20)
        forestry_pct = st.number_input("Forestry %", min_value=0, max_value=100, value=20)

    total_pct = property_pct + renewables_pct + company_pct + forestry_pct
    if total_pct > 100:
        st.error("Exposure percentages exceed 100%. Please adjust your inputs.")
    else:
        strategy_targets = {
            "Property Lending": property_pct / 100,
            "Renewables": renewables_pct / 100,
            "Company Investing": company_pct / 100,
            "Forestry": forestry_pct / 100
        }

        for strat, pct in strategy_targets.items():
            if pct > 0:
                strat_amount = amount * pct
                allocs, expo = allocate_strategy(strat, strat_amount, amount)
                for firm, val in allocs.items():
                    allocation[firm] = allocation.get(firm, 0) + val
                for base, risks in expo.items():
                    strategy_exposure.setdefault(base, {"Low": 0, "High": 0})
                    strategy_exposure[base]["Low"] += risks["Low"]
                    strategy_exposure[base]["High"] += risks["High"]

elif mode == "Risk Exposure":
    low_pct = st.number_input("Low Risk %", min_value=0, max_value=100, value=60)
    high_pct = 100 - low_pct
    st.write(f"High Risk %: {high_pct}%")

    low_amount = amount * (low_pct / 100)
    high_amount = amount * (high_pct / 100)

    low_allocs, low_expo = allocate_by_risk_options("Low", low_amount, amount)
    for firm, val in low_allocs.items():
        allocation[firm] = allocation.get(firm, 0) + val
    for strat, risks in low_expo.items():
        strategy_exposure.setdefault(strat, {"Low": 0, "High": 0})
        strategy_exposure[strat]["Low"] += risks["Low"]

    high_allocs, high_expo = allocate_by_risk_options("High", high_amount, amount)
    for firm, val in high_allocs.items():
        allocation[firm] = allocation.get(firm, 0) + val
    for strat, risks in high_expo.items():
        strategy_exposure.setdefault(strat, {"Low": 0, "High": 0})
        strategy_exposure[strat]["High"] += risks["High"]

# Output tables
if allocation:
    st.subheader("🏢 Firm Strategy Reference")

    reference_rows = []
    for firm, weights in strategy_weights.items():
        strategies = []
        for strat in weights:
            base = strat.split(" (")[0]
            risk = "Low" if "Low" in strat else "High"
            strategies.append(f"{base} ({risk} Risk)")
        reference_rows.append({
            "Firm": firm,
            "Strategies Offered": ", ".join(strategies)
        })

    reference_df = pd.DataFrame(reference_rows)
    reference_df = reference_df.sort_values(by="Firm").reset_index(drop=True)
    reference_df.index += 1  # Start numbering from 1
    reference_df.index.name = "#"

    st.dataframe(reference_df, use_container_width=True)

    st.subheader("📋 Firm Allocation")

    # Build firm-strategy mapping based on actual allocations
    firm_strategies = {}
    for firm, weights in strategy_weights.items():
        selected_strategies = []
        for strat in weights:
            base = strat.split(" (")[0]
            risk = "Low" if "Low" in strat else "High"
            # Only include strategies that received allocation
            if strategy_exposure.get(base, {}).get(risk, 0) > 0:
                selected_strategies.append(base)
        if selected_strategies:
            firm_strategies[firm] = ", ".join(sorted(set(selected_strategies)))

    firm_df = pd.DataFrame({
        "Firm": allocation.keys(),
        "£ Allocation": [format_currency(val) for val in allocation.values()],
        "Strategy": [firm_strategies.get(firm, "") for firm in allocation.keys()]
    })

    firm_df.loc["Total"] = {
        "Firm": "",
        "£ Allocation": format_currency(sum(allocation.values())),
        "Strategy": ""
    }

    st.dataframe(firm_df, use_container_width=True)


    st.subheader("📈 Strategy Exposure")

    rows = []
    total_investment = sum(allocation.values())

    # Only include strategies that received any allocation
    for strat, values in strategy_exposure.items():
        total = values["Low"] + values["High"]
        if total > 0:
            rows.append({
                "Strategy Type": strat,
                "Low Risk £": format_currency(values["Low"]),
                "High Risk £": format_currency(values["High"]),
                "Total £": format_currency(total),
                "% of Portfolio": f"{round((total / total_investment) * 100, 2)}%"
            })

    # Add total row
    rows.append({
        "Strategy Type": "Total",
        "Low Risk £": format_currency(sum(v["Low"] for v in strategy_exposure.values())),
        "High Risk £": format_currency(sum(v["High"] for v in strategy_exposure.values())),
        "Total £": format_currency(total_investment),
        "% of Portfolio": "100%"
    })

strategy_df = pd.DataFrame(rows)
st.dataframe(strategy_df, use_container_width=True)

# 🥧 Pie Chart: Firm Allocation
st.subheader("🥧 Firm Allocation Pie Chart")
pie_df = pd.DataFrame({
    "Firm": allocation.keys(),
    "Allocation": allocation.values()
})
fig_pie = px.pie(pie_df, names="Firm", values="Allocation", title="Firm Allocation Breakdown")
st.plotly_chart(fig_pie, use_container_width=True)

# 📊 Bar Graph: Strategy Exposure by Risk
st.subheader("📊 Strategy Exposure Bar Graph")
bar_rows = []
for strat, values in strategy_exposure.items():
    if values["Low"] > 0:
        bar_rows.append({"Strategy": strat, "Risk": "Low", "Amount": values["Low"]})
    if values["High"] > 0:
        bar_rows.append({"Strategy": strat, "Risk": "High", "Amount": values["High"]})

bar_df = pd.DataFrame(bar_rows)
fig_bar = px.bar(
    bar_df,
    x="Strategy",
    y="Amount",
    color="Risk",
    barmode="stack",  # ← this is the key change
    title="Strategy Exposure by Risk"
)
st.plotly_chart(fig_bar, use_container_width=True)
