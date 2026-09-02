import streamlit as st
import pandapower as pp
import pandapower.networks as pn

# --- PAGE SETUP ---
st.set_page_config(page_title="PhD Grid Simulator", layout="wide")

# Load the IEEE 39-Bus System
# We use st.cache_data so we don't reload the base network on every single click
@st.cache_data
def load_base_network():
    return pn.case39()

base_net = load_base_network()
import copy
net = copy.deepcopy(base_net)

# --- HEADER & EXPLANATION ---
st.title("🌍 IEEE 39-Bus Grid Control Center")
st.markdown("""
**Welcome to the New England Benchmark Grid.** This is a highly complex, 39-bus power system used in PhD-level stability research. 
Use the controls below to act as the Grid Operator. Can you keep the lights on during a heatwave, or will you cause a cascading blackout?
""")

with st.expander("📖 The Real-Life Physics: What are you looking at?"):
    st.markdown("""
    *   **Line Loading (>100%):** If a transmission line pushes too much power, the physical metal heats up, expands, and sags into trees. Relays will automatically "trip" (disconnect) the line to prevent a fire. This forces the power to reroute, potentially overloading other lines and causing a cascading blackout.
    *   **Voltage Collapse (<0.95 pu):** When demand is too high and there isn't enough reactive power, voltages drop. This causes lights to dim (brownouts) and industrial motors to overheat and stall. If it drops too low, the whole grid collapses.
    *   **N-1 Contingency:** A reliable grid must survive the unexpected loss of at least 1 major component (like a tree falling on a line).
    """)

# --- INTERACTIVE CONTROL PANEL ---
st.sidebar.header("🎛️ Grid Control Panel")
st.sidebar.markdown("Test the grid's limits.")

# 1. Load Scaling (Simulating a Heatwave)
st.sidebar.subheader("1. Weather / Demand")
load_scale = st.sidebar.slider("Global Power Demand", min_value=0.5, max_value=2.0, value=1.0, step=0.05, 
                               help="1.0 is normal demand. 1.5 is an extreme summer heatwave where everyone turns on AC.")
net.load['p_mw'] *= load_scale
net.load['q_mvar'] *= load_scale

# 2. Line Faults (Simulating a Storm)
st.sidebar.subheader("2. Disaster Events")
trip_line_1 = st.sidebar.checkbox("⚡ Snap Line 15 (Major Artery)")
trip_line_2 = st.sidebar.checkbox("⚡ Snap Line 22 (Industrial Feed)")

if trip_line_1:
    net.line.at[15, 'in_service'] = False
if trip_line_2:
    net.line.at[22, 'in_service'] = False

# --- SOLVER ENGINE ---
st.header("📊 Real-Time Grid Status")

try:
    # Run the Newton-Raphson Load Flow
    pp.runpp(net, algorithm='nr')
    
    # Calculate System Health Metrics
    max_loading = net.res_line['loading_percent'].max()
    min_voltage = net.res_bus['vm_pu'].min()
    
    # Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Grid Status", "Stable 🟢" if max_loading < 100 else "Emergency 🔴")
    col2.metric("Max Line Load", f"{max_loading:.1f}%", f"{100 - max_loading:.1f}% margin")
    col3.metric("Lowest Voltage", f"{min_voltage:.3f} pu", "Warning if < 0.95")
    
    if max_loading > 100:
        st.error(f"🚨 **WARNING: THERMAL OVERLOAD.** Transmission lines are overheating and at risk of melting or sagging into trees. Reroute power immediately!")
    if min_voltage < 0.95:
        st.warning(f"⚠️ **WARNING: UNDERVOLTAGE.** Customers are experiencing brownouts. Risk of voltage collapse.")

    # Show Data Tables with highlighting
    st.subheader("Critical Component Monitor")
    tab1, tab2 = st.tabs(["Transmission Lines", "Substation Voltages"])
    
    with tab1:
        st.markdown("Lines exceeding 90% capacity are highlighted.")
        # Filter and style lines
        lines_df = net.res_line[['p_from_mw', 'q_from_mvar', 'loading_percent']]
        st.dataframe(lines_df.style.highlight_between(left=90.0, right=1000.0, subset=['loading_percent'], color='#ff4d4d'), use_container_width=True)
        
    with tab2:
        st.markdown("Voltages dropping below 0.95 per-unit are highlighted.")
        # Filter and style buses
        bus_df = net.res_bus[['vm_pu', 'va_degree', 'p_mw', 'q_mvar']]
        st.dataframe(bus_df.style.highlight_between(left=0.0, right=0.95, subset=['vm_pu'], color='#ffcc00'), use_container_width=True)

except pp.LoadflowNotConverged:
    st.error("💥 **CATASTROPHIC GRID COLLAPSE!** 💥")
    st.markdown("""
    **The Newton-Raphson algorithm failed to converge.** 
    
    In real life, this means the physics equations of the grid have broken down. The system could not find a stable state to balance generation and demand. 
    
    *Result: Widespread regional blackout. The protective relays have shut down all power plants to save the physical machinery from ripping itself apart.*
    """)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Northeast_Blackout_of_2003.jpg/800px-Northeast_Blackout_of_2003.jpg", caption="Satellite image of a real regional blackout.")