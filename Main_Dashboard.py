import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config: Tab Title & Icon -------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelar Staking",
    page_icon="https://pbs.twimg.com/profile_images/1877235283755778048/4nlylmxm_400x400.jpg",
    layout="wide"
)

# --- Title with Logo ---------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://axelarscan.io/logos/chains/axelarnet.svg" alt="Axelar Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Axelar Staking</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Info Box --------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color: #ffc6a0; padding: 15px; border-radius: 10px; border: 1px solid #ffd700;">
        The AXL token is the native cryptocurrency of the Axelar network, a decentralized blockchain interoperability platform designed to 
connect multiple blockchains, enabling seamless cross-chain communication and asset transfers. Staking AXL tokens involves locking 
them in the Axelar network to support its operations and security, in return for earning rewards.
    </div>
    """,
    unsafe_allow_html=True
)

st.info(
    "📊Charts initially display data for a default time range. Select a custom range to view results for your desired period."

)

st.info(
    "⏳On-chain data retrieval may take a few moments. Please wait while the results load."
)

# --- Snowflake Connection --------------------------------------------------------------------------------------------------
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
)

# --- Time Frame & Period Selection ---
start_date = st.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("2025-06-30"))

# --- Query Functions ---------------------------------------------------------------------------------------
# --- Row 1: Total Amounts Staked, Unstaked, and Net Staked ---

@st.cache_data
def load_staking_totals(start_date, end_date):
    query = f"""
        WITH delegate AS (
            SELECT
                TRUNC(block_timestamp, 'week') AS date,
                SUM(amount / POW(10, 6)) AS amount_staked
            FROM axelar.gov.fact_staking
            WHERE action = 'delegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
            GROUP BY 1
        ),
        undelegate AS (
            SELECT
                TRUNC(block_timestamp, 'week') AS date,
                SUM(amount / POW(10, 6)) AS amount_unstaked
            FROM axelar.gov.fact_staking
            WHERE action = 'undelegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
            GROUP BY 1
        ),
        final AS (
            SELECT a.date,
                   amount_staked,
                   amount_unstaked,
                   amount_staked - amount_unstaked AS net
            FROM delegate a
            LEFT OUTER JOIN undelegate b
              ON a.date = b.date
        )
        SELECT
            ROUND(SUM(amount_staked), 2) AS total_staked,
            ROUND(SUM(amount_unstaked), 2) AS total_unstaked,
            ROUND(SUM(net), 2) AS total_net_staked
        FROM final
    """
    return pd.read_sql(query, conn).iloc[0]

@st.cache_data
def load_staking_stats(start_date, end_date):
    query = f"""
        WITH tab1 AS (
            SELECT
                COUNT(DISTINCT tx_id) AS "Stakes",
                COUNT(DISTINCT delegator_address) AS "Stakers",
                ROUND(AVG(amount / POW(10, 6)), 2) AS "Average Staked Tokens per Txn",
                ROUND(COUNT(DISTINCT tx_id)::numeric / NULLIF(COUNT(DISTINCT delegator_address), 0)) AS "Avg Stakes per User",
                ROUND(SUM(amount / POW(10, 6)) / NULLIF(COUNT(DISTINCT delegator_address), 0), 2) AS "Avg Staked per User"
            FROM axelar.gov.fact_staking
            WHERE action = 'delegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
        ),
        tab2 AS (
            SELECT
                COUNT(DISTINCT tx_id) AS "UnStakes"
            FROM axelar.gov.fact_staking
            WHERE action = 'undelegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
        )
        SELECT * FROM tab1, tab2;
    """
    df = pd.read_sql(query, conn)
    df.columns = df.columns.str.lower()
    return df.iloc[0]

@st.cache_data
def load_weekly_stake_activity(start_date, end_date):
    query = f"""
        SELECT
          TRUNC(block_timestamp,'week') AS "Date",
          CASE 
               WHEN action = 'delegate' THEN 'Stake'
               WHEN action = 'undelegate' THEN 'UnStake'
               ELSE 'Other'
          END AS "Action Type",
          COUNT(DISTINCT tx_id) AS "Txns Count",
          COUNT(DISTINCT delegator_address) AS "Users Count"
        FROM axelar.gov.fact_staking
        WHERE action IN ('delegate', 'undelegate')
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1,2
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_weekly_net_stake(start_date, end_date):
    query = f"""
        WITH delegate AS (
            SELECT
                TRUNC(block_timestamp, 'week') AS date,
                SUM(amount / POW(10, 6)) AS amount_staked
            FROM axelar.gov.fact_staking
            WHERE action = 'delegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
            GROUP BY 1
        ),
        undelegate AS (
            SELECT
                TRUNC(block_timestamp, 'week') AS date,
                SUM(amount / POW(10, 6)) * -1 AS amount_unstaked
            FROM axelar.gov.fact_staking
            WHERE action = 'undelegate'
              AND TX_SUCCEEDED = 'TRUE'
              AND block_timestamp::date >= '{start_date}'
              AND block_timestamp::date <= '{end_date}'
            GROUP BY 1
        )
        SELECT
            a.date AS "Date",
            ROUND(amount_staked, 2) AS "Staked Amount",
            ROUND(amount_unstaked, 2) AS "UnStaked Amount",
            ROUND((amount_staked + amount_unstaked), 2) AS "Net Staked Amount"
        FROM delegate a
        LEFT OUTER JOIN undelegate b ON a.date = b.date
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_action_type_share(start_date, end_date):
    query = f"""
        SELECT
          CASE
              WHEN action = 'delegate' THEN 'Stake'
              WHEN action = 'undelegate' THEN 'UnStake'
              ELSE 'Other'
          END AS "Action Type",
          COUNT(DISTINCT tx_id) AS "Txns Count",
          COUNT(DISTINCT delegator_address) AS "Users Count",
          ROUND((SUM(amount) / POW(10, 6)), 2) AS "Volume"
        FROM axelar.gov.fact_staking
        WHERE action IN ('delegate', 'undelegate')
          AND block_timestamp::date >= '{start_date}'
          AND block_timestamp::date <= '{end_date}'
        GROUP BY 1
    """
    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------
staking_totals = load_staking_totals(start_date, end_date)
staking_stats = load_staking_stats(start_date, end_date)
stake_activity = load_weekly_stake_activity(start_date, end_date)
weekly_net_stake = load_weekly_net_stake(start_date, end_date)
action_share = load_action_type_share(start_date, end_date)
# ------------------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
staking_totals.index = staking_totals.index.str.lower()

col1, col2, col3 = st.columns(3)
col1.metric("Total Amount Staked", f"{staking_totals['total_staked']:,} AXL")
col2.metric("Total Amount UnStaked", f"{staking_totals['total_unstaked']:,} AXL")
col3.metric("Total Amount Net Staked", f"{staking_totals['total_net_staked']:,} AXL")

# --- Row 2 ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Number of Stakes", f"{staking_stats['stakes']:,}")
col2.metric("Total Number of Stakers", f"{staking_stats['stakers']:,}")
col3.metric("Total Number of UnStakes", f"{staking_stats['unstakes']:,}")

# --- Row 3 ---
col4, col5, col6 = st.columns(3)
col4.metric("Average Staked Amount (per Txn)", f"{staking_stats['average staked tokens per txn']:,} AXL")
col5.metric("Average Staked Amount (per User)", f"{staking_stats['avg staked per user']:,} AXL")
col6.metric("Average Number of Stakes per User", f"{staking_stats['avg stakes per user']:,}")

# --- Row 4 ---
# --- chart 1 ---
fig1 = px.line(
    stake_activity,
    x="Date",
    y="Txns Count",
    color="Action Type",
    markers=True,
    title="Weekly Number of Transactions: Stake vs. UnStake"
)

# --- chart 2 ---
fig2 = px.line(
    stake_activity,
    x="Date",
    y="Users Count",
    color="Action Type",
    markers=True,
    title="Weekly Number of Users: Stake vs. UnStake"
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

# --- Row 5 --------
fig = go.Figure()

# --- Staked Amount (Bar) ---
fig.add_trace(go.Bar(
    x=weekly_net_stake["Date"],
    y=weekly_net_stake["Staked Amount"],
    name="Staked Amount",
    marker_color="green",
    yaxis="y1"
))

# --- UnStaked Amount (Bar) ---
fig.add_trace(go.Bar(
    x=weekly_net_stake["Date"],
    y=weekly_net_stake["UnStaked Amount"],
    name="UnStaked Amount",
    marker_color="red",
    yaxis="y1"
))

# --- Net Staked Amount (Line, Secondary Y-axis) ---
fig.add_trace(go.Scatter(
    x=weekly_net_stake["Date"],
    y=weekly_net_stake["Net Staked Amount"],
    name="Net Staked Amount",
    mode="lines+markers",
    line=dict(color="blue", width=2),
    yaxis="y2"
))

fig.update_layout(
    title="Weekly Net Staked Volume ($AXL)",
    barmode="group",
    yaxis=dict(title="($AXL)"),
    yaxis2=dict(title="($AXL)", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(title="Date"),
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# -- Row 6 ------

# --- Donut Chart: Share of Transactions ---
fig_txns = px.pie(
    action_share,
    names="Action Type",
    values="Txns Count",
    title="Share of Transactions",
    hole=0.5,
    color="Action Type",
    color_discrete_map={"Stake": "green", "UnStake": "red"}
)

# --- Donut Chart: Share of Volume ---
fig_volume = px.pie(
    action_share,
    names="Action Type",
    values="Volume",
    title="Share of Volume ($AXL)",
    hole=0.5,
    color="Action Type",
    color_discrete_map={"Stake": "green", "UnStake": "red"}
)

# --- Bar Chart: Share of Users ---
fig_users = px.bar(
    action_share,
    x="Action Type",
    y="Users Count",
    title="Share of Users",
    text="Users Count",
    color="Action Type",
    color_discrete_map={"Stake": "green", "UnStake": "red"}
)
fig_users.update_traces(texttemplate='%{text}', textposition='outside')
fig_users.update_layout(yaxis_title="Users Count")

col1, col2, col3 = st.columns(3)
col1.plotly_chart(fig_txns, use_container_width=True)
col2.plotly_chart(fig_volume, use_container_width=True)
col3.plotly_chart(fig_users, use_container_width=True)

