import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import xmltodict
import json
import io

# 設定網頁標題
st.set_page_config(page_title="US Yield vs HK Liquidity Analysis", layout="wide")
st.title("📈 美國國債收益率 vs 香港銀行體系結餘分析")

# --- 數據抓取函數 ---

@st.cache_data(ttl=3600)  # 快取數據 1 小時，避免重複請求
def get_df_us(year):
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url)
        us_data = response.content
        dict_data_us = xmltodict.parse(us_data)
        
        dict_us = dict()
        # 獲取屬性列表
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
        # 轉換數值型態
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

# --- 側邊欄控制 ---
st.sidebar.header("設定")
selected_years = st.sidebar.multiselect("選擇美國數據年份", [2022, 2023, 2024], default=[2022, 2023])
us_tenor = st.sidebar.selectbox("選擇美國債券期限", ["BC_2YEAR", "BC_10YEAR", "BC_3MONTH", "BC_1MONTH"], index=0)

# --- 主程式邏輯 ---

# 載入數據
with st.spinner('正在獲取最新數據...'):
    # 獲取美國數據
    if selected_years:
        df_us_list = [get_df_us(y) for y in selected_years]
        df_us_all = pd.concat(df_us_list)
    else:
        df_us_all = pd.DataFrame()

    # 獲取香港數據
    df_hk_all = get_df_hk()

    # 載入澳門 MAIBOR 數據 (如果有的話)
    # 注意：在雲端部署時，你需要確保此 Excel 檔案也在 GitHub 倉庫中
    try:
        df_mo = pd.read_excel('amcm.maibor.November-1-2022.to.xlsx')
        df_mo.set_index('日期', inplace=True)
        df_mo.index = pd.to_datetime(df_mo.index)
        df_mo.sort_index(inplace=True)
        has_mo_data = True
    except:
        has_mo_data = False

# --- 圖表顯示 ---

if not df_us_all.empty and not df_hk_all.empty:
    st.subheader(f"美國 {us_tenor} 收益率 vs 香港銀行體系總結餘")
    
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # 繪製美國收益率 (左軸)
    color = 'tab:blue'
    ax1.set_xlabel('Date')
    ax1.set_ylabel(f'US Yield ({us_tenor}) %', color=color)
    ax1.plot(df_us_all.index, df_us_all[us_tenor].astype(float), color=color, label=f"US {us_tenor}")
    ax1.tick_params(axis='y', labelcolor=color)

    # 繪製香港總結餘 (右軸)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('HK Aggregate Balance (Mio HKD)', color=color)
    ax2.plot(df_hk_all.index, df_hk_all['forecast_aggregate_bal_u'], color=color, label="HK Agg Balance", linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    st.pyplot(fig)

    # 數據表格
    col1, col2 = st.columns(2)
    with col1:
        st.write("美國國債數據 (最新)", df_us_all[[us_tenor]].tail())
    with col2:
        st.write("香港流動性數據 (最新)", df_hk_all[['forecast_aggregate_bal_u']].tail())

else:
    st.warning("請在側邊欄選擇年份或檢查網路連線。")

if has_mo_data:
    st.subheader("澳門 MAIBOR 數據參考")
    st.line_chart(df_mo.iloc[:, 0]) # 假設第一欄是主要利率import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import xmltodict
import json
import io

# 設定網頁標題
st.set_page_config(page_title="US Yield vs HK Liquidity Analysis", layout="wide")
st.title("📈 美國國債收益率 vs 香港銀行體系結餘分析")

# --- 數據抓取函數 ---

@st.cache_data(ttl=3600)  # 快取數據 1 小時，避免重複請求
def get_df_us(year):
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url)
        us_data = response.content
        dict_data_us = xmltodict.parse(us_data)
        
        dict_us = dict()
        # 獲取屬性列表
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
        # 轉換數值型態
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

# --- 側邊欄控制 ---
st.sidebar.header("設定")
selected_years = st.sidebar.multiselect("選擇美國數據年份", [2022, 2023, 2024], default=[2022, 2023])
us_tenor = st.sidebar.selectbox("選擇美國債券期限", ["BC_2YEAR", "BC_10YEAR", "BC_3MONTH", "BC_1MONTH"], index=0)

# --- 主程式邏輯 ---

# 載入數據
with st.spinner('正在獲取最新數據...'):
    # 獲取美國數據
    if selected_years:
        df_us_list = [get_df_us(y) for y in selected_years]
        df_us_all = pd.concat(df_us_list)
    else:
        df_us_all = pd.DataFrame()

    # 獲取香港數據
    df_hk_all = get_df_hk()

    # 載入澳門 MAIBOR 數據 (如果有的話)
    # 注意：在雲端部署時，你需要確保此 Excel 檔案也在 GitHub 倉庫中
    try:
        df_mo = pd.read_excel('amcm.maibor.November-1-2022.to.xlsx')
        df_mo.set_index('日期', inplace=True)
        df_mo.index = pd.to_datetime(df_mo.index)
        df_mo.sort_index(inplace=True)
        has_mo_data = True
    except:
        has_mo_data = False

# --- 圖表顯示 ---

if not df_us_all.empty and not df_hk_all.empty:
    st.subheader(f"美國 {us_tenor} 收益率 vs 香港銀行體系總結餘")
    
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # 繪製美國收益率 (左軸)
    color = 'tab:blue'
    ax1.set_xlabel('Date')
    ax1.set_ylabel(f'US Yield ({us_tenor}) %', color=color)
    ax1.plot(df_us_all.index, df_us_all[us_tenor].astype(float), color=color, label=f"US {us_tenor}")
    ax1.tick_params(axis='y', labelcolor=color)

    # 繪製香港總結餘 (右軸)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('HK Aggregate Balance (Mio HKD)', color=color)
    ax2.plot(df_hk_all.index, df_hk_all['forecast_aggregate_bal_u'], color=color, label="HK Agg Balance", linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    st.pyplot(fig)

    # 數據表格
    col1, col2 = st.columns(2)
    with col1:
        st.write("美國國債數據 (最新)", df_us_all[[us_tenor]].tail())
    with col2:
        st.write("香港流動性數據 (最新)", df_hk_all[['forecast_aggregate_bal_u']].tail())

else:
    st.warning("請在側邊欄選擇年份或檢查網路連線。")

if has_mo_data:
    st.subheader("澳門 MAIBOR 數據參考")
    st.line_chart(df_mo.iloc[:, 0]) # 假設第一欄是主要利率