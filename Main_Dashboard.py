import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Staking",
    page_icon="https://pbs.twimg.com/profile_images/1877235283755778048/4nlylmxm_400x400.jpg",
    layout="wide"
)

st.title("📊Axelar Staking")

st.markdown("""
The AXL token is the native cryptocurrency of the Axelar network, a decentralized blockchain interoperability platform designed to 
connect multiple blockchains, enabling seamless cross-chain communication and asset transfers. Staking AXL tokens involves locking 
them in the Axelar network to support its operations and security, in return for earning rewards.
""")

# --- Snowflake Connection ---
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
end_date = st.date_input("End Date", value=pd.to_datetime("2025-06-01"))

# --- Query Functions ---------------------------------------------------------------------------------------
# --- Row 10: Total Amounts Staked, Unstaked, and Net Staked ---

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

# --- Load Data ----------------------------------------------------------------------------------------
staking_totals = load_staking_totals(start_date, end_date)

# ------------------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Amount Staked", f"{staking_totals['total_staked']:,} AXL")
col2.metric("Total Amount UnStaked", f"{staking_totals['total_unstaked']:,} AXL")
col3.metric("Total Amount Net Staked", f"{staking_totals['total_net_staked']:,} AXL")
