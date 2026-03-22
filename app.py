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
    """獲取美國國債收益率 (XML)"""
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url, timeout=10)
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
def get_df_hk_hibor(years):
    """使用新的 MSB API 獲取香港 HIBOR 利率"""
    try:
        if not years: return pd.DataFrame()
        start_date = f"{min(years)}-01-01"
        end_date = f"{max(years)}-12-31"
        
        # 新的 API 連結 (Monthly Statistical Bulletin)
        hk_url = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily'
        params = {
            'segment': 'hibor.fixing',
            'from': start_date,
            'to': end_date,
            'pagesize': 1000  # 確保抓取足夠多的數據
        }
        
        response = requests.get(hk_url, params=params, timeout=10)
        data = response.json()
        records = data['result']['records']
        
        df = pd.DataFrame(records)
        # 注意：此 API 欄位名為 end_of_day 而非 end_of_date
        df['Date'] = pd.to_datetime(df['end_of_day'])
        df.set_index('Date', inplace=True)
        
        # 欄位映射：將 ir_1m 轉化為我們程式中使用的名稱
        df = df.rename(columns={
            'ir_1m': 'hibor_1m',
            'ir_3m': 'hibor_3m'
        })
        
        # 轉換數值型態
        for col in ['hibor_1m', 'hibor_3m']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.sort_index()
    except Exception as e:
        st.error(f"香港 HIBOR (新 API) 獲取失敗: {e}")
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
        
        # 修正：使用 params 傳遞 GET 參數
        response = requests.get(url, params=payload, headers=headers, timeout=10)
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
# 配合新 API 的欄位名 (ir_1m 已在函數中 rename 為 hibor_1m)
tenor_map = {
    "1 Month (1個月)": {"US": "BC_1MONTH", "HK": "hibor_1m", "MO": "oneMonth"},
    "3 Month (3個月)": {"US": "BC_3MONTH", "HK": "hibor_3m", "MO": None}
}
selected_tenor = st.sidebar.selectbox("選擇利率期限", list(tenor_map.keys()))

# --- 數據加載 ---
with st.spinner('同步三地官方 API 數據中...'):
    # 美國數據
    df_us = pd.concat([get_df_us(y) for y in selected_years]) if selected_years else pd.DataFrame()
    # 澳門數據
    df_mo = pd.concat([get_df_mo(y) for y in selected_years]) if selected_years else pd.DataFrame()
    # 香港數據 (新 API 支持日期範圍，只需調用一次)
    df_hk = get_df_hk_hibor(selected_years)

# --- 視覺化圖表 ---

st.subheader(f"三地利率走勢圖 ({selected_tenor})")

if not df_us.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    us_col = tenor_map[selected_tenor]["US"]
    hk_col = tenor_map[selected_tenor]["HK"]
    mo_col = tenor_map[selected_tenor]["MO"]

    # 1. 繪製美國 (藍色實線)
    ax.plot(df_us.index, df_us[us_col], label=f"US Treasury ({us_col})", color='tab:blue', linewidth=2)
    
    # 2. 繪製香港 (紅色虛線)
    if not df_hk.empty and hk_col in df_hk.columns:
        ax.plot(df_hk.index, df_hk[hk_col], label=f"HK HIBOR ({hk_col})", color='tab:red', linestyle='--')

    # 3. 繪製澳門 (綠色點線)
    if mo_col and not df_mo.empty:
        ax.plot(df_mo.index, df_mo[mo_col], label=f"Macau MAIBOR (1M)", color='tab:green', alpha=0.8)

    ax.set_ylabel("利率 (%)")
    ax.set_title(f"Comparison of US, HK and MO Rates ({selected_tenor})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    st.pyplot(fig)

    # 數據比較表格
    st.write("### 最新利率數值比較")
    latest_data = []
    if not df_us.empty: latest_data.append({"地區": "美國 (US)", "最新利率": f"{df_us[us_col].iloc[-1]:.4f}%"})
    if not df_hk.empty: latest_data.append({"地區": "香港 (HK)", "最新利率": f"{df_hk[hk_col].iloc[-1]:.4f}%"})
    if not df_mo.empty and mo_col: latest_data.append({"地區": "澳門 (MO)", "最新利率": f"{df_mo[mo_col].iloc[-1]:.4f}%"})
    
    st.table(pd.DataFrame(latest_data))

else:
    st.info("請在左側選擇年份以顯示圖表。")

st.markdown("---")
st.caption(f"數據最後同步時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")