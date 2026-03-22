import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import xmltodict
import json

# 設定網頁標題
st.set_page_config(page_title="US vs HK vs MO Yield Comparison", layout="wide")
st.title("🌐 三地利率走勢對比：美國 (Treasury) vs 香港 (HIBOR) vs 澳門 (MAIBOR)")

# --- 數據抓取函數 ---

@st.cache_data(ttl=3600)
def get_df_us(year):
    """獲取美國國債收益率"""
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url)
        dict_data_us = xmltodict.parse(response.content)
        
        dict_us = dict()
        properties = dict_data_us['feed']['entry'][0]['content']['m:properties'].keys()
        
        for key in properties:
            try:
                clean_key = key.replace('d:', '')
                dict_us[clean_key] = [i['content']['m:properties'][key]['#text'] for i in dict_data_us['feed']['entry']]
            except: pass
        
        df = pd.DataFrame(dict_us)
        df['Date'] = pd.to_datetime(df['NEW_DATE'])
        df.set_index('Date', inplace=True)
        cols = [c for c in df.columns if 'BC_' in c]
        df[cols] = df[cols].apply(pd.to_numeric)
        return df
    except Exception as e:
        st.error(f"美國數據獲取失敗: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_hk_hibor():
    """獲取香港 HIBOR 利率"""
    try:
        # 獲取最近一年的 HIBOR 數據
        hk_url = 'https://api.hkma.gov.hk/public/market-data-and-statistics/interest-rates-and-exchange-rates/hibor-fixing-daily?pagesize=500'
        response = requests.get(hk_url)
        data = response.json()
        records = data['result']['records']
        df = pd.DataFrame(records)
        df['Date'] = pd.to_datetime(df['end_of_date'])
        df.set_index('Date', inplace=True)
        # 確保數值正確
        for col in ['hibor_1m', 'hibor_3m', 'hibor_1w']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.sort_index()
    except Exception as e:
        st.error(f"香港 HIBOR 獲取失敗: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_mo(year):
    """獲取澳門 MAIBOR 利率"""
    try:
        url = 'https://www.amcm.gov.mo/api/v1.0/cms/financial_info'
        headers = {'User-Agent': 'Mozilla/5.0'}
        today = datetime.today().strftime('%Y%m%d')
        end = today if year == datetime.today().year else f'{year}1231'
        payload = {"QueryType": "Maibor", "Begin": int(f"{year}0101"), "End": int(end)}
        
        response = requests.get(url, params=payload, headers=headers)
        df = pd.DataFrame(response.json()['data'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        # 轉為百分比數值 (例如 5.1% -> 5.1)
        df['oneMonth'] = pd.to_numeric(df['oneMonth'].str.replace('%', ''), errors='coerce')
        return df.sort_index()
    except Exception as e:
        st.error(f"澳門數據獲取失敗: {e}")
        return pd.DataFrame()

# --- 側邊欄設定 ---
st.sidebar.header("🔍 分析參數")
current_year = datetime.today().year
selected_years = st.sidebar.multiselect("選擇年份", [current_year-2, current_year-1, current_year], default=[current_year-1, current_year])

# 定義期限對應關係
tenor_map = {
    "1 Month (1個月)": {"US": "BC_1MONTH", "HK": "hibor_1m", "MO": "oneMonth"},
    "3 Month (3個月)": {"US": "BC_3MONTH", "HK": "hibor_3m", "MO": None} # 澳門API通常提供1M
}
selected_tenor = st.sidebar.selectbox("選擇利率期限", list(tenor_map.keys()))

# --- 數據加載 ---
with st.spinner('同步三地官方 API 數據中...'):
    df_us = pd.concat([get_df_us(y) for y in selected_years]) if selected_years else pd.DataFrame()
    df_mo = pd.concat([get_df_mo(y) for y in selected_years]) if selected_years else pd.DataFrame()
    df_hk = get_df_hk_hibor()

# --- 視覺化圖表 ---

st.subheader(f"三地利率走勢圖 ({selected_tenor})")

if not df_us.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 獲取對應欄位名稱
    us_col = tenor_map[selected_tenor]["US"]
    hk_col = tenor_map[selected_tenor]["HK"]
    mo_col = tenor_map[selected_tenor]["MO"]

    # 繪製美國
    ax.plot(df_us.index, df_us[us_col], label=f"US Treasury ({us_col})", linewidth=2)
    
    # 繪製香港
    if not df_hk.empty and hk_col in df_hk.columns:
        # 過濾日期以符合選擇年份
        df_hk_filtered = df_hk[df_hk.index.year.isin(selected_years)]
        ax.plot(df_hk_filtered.index, df_hk_filtered[hk_col], label=f"HK HIBOR ({hk_col})", linestyle='--')

    # 繪製澳門
    if mo_col and not df_mo.empty:
        ax.plot(df_mo.index, df_mo[mo_col], label=f"Macau MAIBOR (1M)", alpha=0.7)

    ax.set_ylabel("利率 (%)")
    ax.set_title(f"US vs HK vs MO Interest Rates")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    st.pyplot(fig)

    # 數據比較表格
    st.write("### 最新利率數值比較")
    latest_data = {
        "地區": ["美國 (US)", "香港 (HK)", "澳門 (MO)"],
        "最新利率 (%)": [
            f"{df_us[us_col].iloc[-1]:.4f}%" if not df_us.empty else "N/A",
            f"{df_hk[hk_col].iloc[-1]:.4f}%" if not df_hk.empty else "N/A",
            f"{df_mo[mo_col].iloc[-1]:.4f}%" if mo_col and not df_mo.empty else "N/A"
        ]
    }
    st.table(pd.DataFrame(latest_data))

else:
    st.info("請在左側選擇年份以顯示圖表。")

st.markdown("---")
st.caption("數據來源：美國財政部, 香港金融管理局 (HKMA), 澳門金融管理局 (AMCM)")