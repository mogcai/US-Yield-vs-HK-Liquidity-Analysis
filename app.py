import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import xmltodict
import json

# 設定網頁標題
st.set_page_config(page_title="US vs HK vs MO Financial Analysis", layout="wide")
st.title("📈 跨區域金融數據分析：美國 vs 香港 vs 澳門")

# --- 數據抓取函數 ---

@st.cache_data(ttl=3600)
def get_df_us(year):
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url)
        us_data = response.content
        dict_data_us = xmltodict.parse(us_data)
        
        dict_us = dict()
        properties = dict_data_us['feed']['entry'][0]['content']['m:properties'].keys()
        
        for key in properties:
            try:
                clean_key = key.replace('d:', '')
                dict_us[clean_key] = [i['content']['m:properties'][key]['#text'] for i in dict_data_us['feed']['entry']]
            except:
                pass
        
        df_us = pd.DataFrame(dict_us)
        df_us['Date'] = [datetime.strptime(i, '%Y-%m-%dT%H:%M:%S') for i in df_us['NEW_DATE']]
        df_us.set_index('Date', inplace=True)
        cols = [c for c in df_us.columns if 'BC_' in c]
        df_us[cols] = df_us[cols].apply(pd.to_numeric)
        return df_us
    except Exception as e:
        st.error(f"獲取美國數據失敗: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_hk():
    try:
        hk_url = 'https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity'
        response = requests.get(hk_url)
        dict_data_hk = json.loads(response.content)
        records = dict_data_hk['result']['records']
        df_hk = pd.DataFrame(records)
        df_hk['Date'] = pd.to_datetime(df_hk['end_of_date'])
        df_hk.set_index('Date', inplace=True)
        df_hk.sort_index(inplace=True)
        return df_hk
    except Exception as e:
        st.error(f"獲取香港數據失敗: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_mo(year):
    try:
        url = r'https://www.amcm.gov.mo/api/v1.0/cms/financial_info'
        today = datetime.today().strftime('%Y%m%d')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        end = today if year == datetime.today().year else f'{year}1231'
        payload = {
            "QueryType": "Maibor",
            "Begin": int(f"{year}0101"),
            "End": int(end)
        }
        # 使用 requests.get 搭配 payload
        response = requests.get(url, params=payload, headers=headers)
        mo_data = response.json()
        
        df = pd.DataFrame(mo_data['data'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        # 清洗數據並轉換為數值 (百分比格式)
        df['oneMonth'] = pd.to_numeric(df['oneMonth'].str.replace('%', ''), errors='coerce') / 100
        return df
    except Exception as e:
        st.error(f"獲取澳門數據失敗: {e}")
        return pd.DataFrame()

# --- 側邊欄控制 ---
st.sidebar.header("📊 參數設定")
current_year = datetime.today().year
selected_years = st.sidebar.multiselect("選擇數據年份", [current_year-2, current_year-1, current_year], default=[current_year-1, current_year])
us_tenor = st.sidebar.selectbox("選擇美國債券期限", ["BC_2YEAR", "BC_10YEAR", "BC_3MONTH", "BC_1MONTH"], index=0)

# --- 數據加載邏輯 ---
with st.spinner('正在從各官方 API 獲取最新數據...'):
    # 美國與澳門數據 (按年份抓取並合併)
    df_us_all = pd.DataFrame()
    df_mo_all = pd.DataFrame()
    
    if selected_years:
        df_us_all = pd.concat([get_df_us(y) for y in selected_years])
        df_mo_all = pd.concat([get_df_mo(y) for y in selected_years])
    
    # 香港數據
    df_hk_all = get_df_hk()

# --- 圖表與展示 ---

if not df_us_all.empty:
    st.subheader(f"趨勢對比：US {us_tenor} vs Macau MAIBOR vs HK Liquidity")
    
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # 第一軸 (左軸)：顯示利率 (%)
    color1 = 'tab:blue'
    color2 = 'tab:green'
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Rate (%)', color='black')
    
    # 畫美國債
    ax1.plot(df_us_all.index, df_us_all[us_tenor].astype(float), color=color1, label=f"US {us_tenor} Yield")
    
    # 畫澳門 MAIBOR (乘以 100 以對應百分比顯示)
    if not df_mo_all.empty:
        ax1.plot(df_mo_all.index, df_mo_all['oneMonth'] * 100, color=color2, label="Macau MAIBOR (1M)", alpha=0.7)
    
    ax1.tick_params(axis='y')
    ax1.legend(loc='upper left')

    # 第二軸 (右軸)：顯示香港銀行結餘 (金額)
    if not df_hk_all.empty:
        ax2 = ax1.twinx()
        color3 = 'tab:red'
        ax2.set_ylabel('HK Aggregate Balance (Mio HKD)', color=color3)
        ax2.plot(df_hk_all.index, df_hk_all['forecast_aggregate_bal_u'], color=color3, label="HK Agg Balance", linestyle='--', alpha=0.5)
        ax2.tick_params(axis='y', labelcolor=color3)
        ax2.legend(loc='upper right')

    st.pyplot(fig)

    # 數據檢查區塊
    with st.expander("查看原始數據表格"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("🇺🇸 US Treasury", df_us_all[[us_tenor]].tail())
        with col2:
            st.write("🇲🇴 Macau MAIBOR", df_mo_all[['oneMonth']].tail())
        with col3:
            st.write("🇭🇰 HK Agg Balance", df_hk_all[['forecast_aggregate_bal_u']].tail())
else:
    st.info("請在側邊欄選擇年份以開始分析。")

st.markdown("---")
st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 數據來源: US Treasury, HKMA, AMCM")