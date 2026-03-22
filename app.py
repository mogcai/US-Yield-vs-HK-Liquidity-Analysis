import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import xmltodict
import platform

# --- 解決 Matplotlib 中文顯示問題 ---
def set_matplot_zh_font():
    system_os = platform.system()
    if system_os == "Windows":
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei'] # 微軟正黑體
    elif system_os == "Darwin": # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
    else: # Linux (Streamlit Cloud 預設環境)
        # Streamlit Cloud 沒安裝中文字體時，最穩妥的方法是改用英文標籤，
        # 或安裝特定字體包。這裡先設定通用支援。
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans'] 
    
    # 解決座標軸負號顯示為方塊的問題
    plt.rcParams['axes.unicode_minus'] = False

set_matplot_zh_font()

# --- 網頁配置 ---
st.set_page_config(page_title="Global Interest Rate Comparison", layout="wide")
st.title("🌐 全球利率走勢動態對比工具")
st.markdown("比較美國國債收益率、香港 HIBOR 與澳門 MAIBOR 的實時走勢。")

# --- 數據抓取函數 ---

@st.cache_data(ttl=86400)
def get_df_us(year):
    try:
        us_url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}'
        response = requests.get(us_url, timeout=10)
        dict_data_us = xmltodict.parse(response.content)
        entries = dict_data_us['feed'].get('entry', [])
        if not entries: return pd.DataFrame()
        if not isinstance(entries, list): entries = [entries]
        dict_us = {}
        properties = entries[0]['content']['m:properties'].keys()
        for key in properties:
            clean_key = key.replace('d:', '')
            dict_us[clean_key] = [i['content']['m:properties'][key].get('#text', None) for i in entries]
        df = pd.DataFrame(dict_us)
        df['Date'] = pd.to_datetime(df['NEW_DATE'])
        df.set_index('Date', inplace=True)
        cols = [c for c in df.columns if 'BC_' in c]
        df[cols] = df[cols].apply(pd.to_numeric)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_hk_hibor(year):
    try:
        url = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily'
        params = {'segment': 'hibor.fixing', 'from': f'{year}-01-01', 'to': f'{year}-12-31', 'pagesize': 500}
        response = requests.get(url, params=params, timeout=10)
        records = response.json()['result']['records']
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df['Date'] = pd.to_datetime(df['end_of_day'])
        df.set_index('Date', inplace=True)
        df = df.rename(columns={'ir_1m': 'hibor_1m', 'ir_3m': 'hibor_3m'})
        for col in ['hibor_1m', 'hibor_3m']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_df_mo(year):
    try:
        url = 'https://www.amcm.gov.mo/api/v1.0/cms/financial_info'
        headers = {'User-Agent': 'Mozilla/5.0'}
        payload = {"QueryType": "Maibor", "Begin": int(f"{year}0101"), "End": int(f"{year}1231")}
        response = requests.get(url, params=payload, headers=headers, timeout=10)
        data = response.json()
        if 'data' not in data or not data['data']: return pd.DataFrame()
        df = pd.DataFrame(data['data'])
        df['Date'] = pd.to_datetime(df['date'])
        df.set_index('Date', inplace=True)
        df['oneMonth'] = pd.to_numeric(df['oneMonth'].str.replace('%', ''), errors='coerce')
        return df
    except: return pd.DataFrame()

# --- 側邊欄設定 ---
st.sidebar.header("⚙️ 篩選條件")

country_options = ["美國 (US Treasury)", "香港 (HK HIBOR)", "澳門 (MO MAIBOR)"]
selected_countries = st.sidebar.multiselect("選擇顯示地區", country_options, default=country_options)

current_year = datetime.today().year
year_options = list(range(current_year, current_year - 5, -1))
selected_years = st.sidebar.multiselect("選擇顯示年份", year_options, default=[current_year])

tenor_map = {
    "1 Month (1個月)": {"US": "BC_1MONTH", "HK": "hibor_1m", "MO": "oneMonth"},
    "3 Month (3個月)": {"US": "BC_3MONTH", "HK": "hibor_3m", "MO": None}
}
selected_tenor = st.sidebar.selectbox("選擇利率期限", list(tenor_map.keys()))

# --- 數據處理 ---
if selected_years and selected_countries:
    with st.spinner('正在同步數據...'):
        df_us, df_hk, df_mo = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        if "美國 (US Treasury)" in selected_countries:
            df_us = pd.concat([get_df_us(y) for y in selected_years])
        if "香港 (HK HIBOR)" in selected_countries:
            df_hk = pd.concat([get_df_hk_hibor(y) for y in selected_years])
        if "澳門 (MO MAIBOR)" in selected_countries:
            df_mo = pd.concat([get_df_mo(y) for y in selected_years])

    # 過濾年份
    if not df_us.empty: df_us = df_us[df_us.index.year.isin(selected_years)].sort_index()
    if not df_hk.empty: df_hk = df_hk[df_hk.index.year.isin(selected_years)].sort_index()
    if not df_mo.empty: df_mo = df_mo[df_mo.index.year.isin(selected_years)].sort_index()

    # --- 繪圖 ---
    if not (df_us.empty and df_hk.empty and df_mo.empty):
        st.subheader(f"走勢分析: {selected_tenor}")
        fig, ax = plt.subplots(figsize=(12, 5))
        
        us_col = tenor_map[selected_tenor]["US"]
        hk_col = tenor_map[selected_tenor]["HK"]
        mo_col = tenor_map[selected_tenor]["MO"]

        if "美國 (US Treasury)" in selected_countries and not df_us.empty:
            ax.plot(df_us.index, df_us[us_col], label="美國國債 (US Treasury)", color='#1f77b4', linewidth=2)
        
        if "香港 (HK HIBOR)" in selected_countries and not df_hk.empty:
            ax.plot(df_hk.index, df_hk[hk_col], label="香港 HIBOR", color='#d62728', linestyle='--')
        
        if "澳門 (MO MAIBOR)" in selected_countries and mo_col and not df_mo.empty:
            ax.plot(df_mo.index, df_mo[mo_col], label="澳門 MAIBOR", color='#2ca02c', alpha=0.8)

        all_dates = []
        if not df_us.empty: all_dates.extend([df_us.index.min(), df_us.index.max()])
        if not df_hk.empty: all_dates.extend([df_hk.index.min(), df_hk.index.max()])
        if not df_mo.empty: all_dates.extend([df_mo.index.min(), df_mo.index.max()])
        if all_dates: ax.set_xlim(min(all_dates), max(all_dates))

        ax.set_ylabel("利率 (%)")
        ax.set_title(f"多地利率比較 ({selected_tenor})") # 這裡現在可以顯示中文了
        ax.legend()
        ax.grid(True, alpha=0.2)
        st.pyplot(fig)

        # 摘要卡片
        st.write("### 🧮 最新利率摘要")
        m_cols = st.columns(len(selected_countries))
        idx = 0
        if "美國 (US Treasury)" in selected_countries and not df_us.empty:
            m_cols[idx].metric("美國 (US)", f"{df_us[us_col].iloc[-1]:.3f}%")
            idx += 1
        if "香港 (HK HIBOR)" in selected_countries and not df_hk.empty:
            m_cols[idx].metric("香港 (HK)", f"{df_hk[hk_col].iloc[-1]:.3f}%")
            idx += 1
        if "澳門 (MO MAIBOR)" in selected_countries and not df_mo.empty:
            m_cols[idx].metric("澳門 (MO)", f"{df_mo['oneMonth'].iloc[-1]:.3f}%")
            idx += 1
    else:
        st.warning("⚠️ 無有效數據。")
else:
    st.info("💡 請在左側選單選擇參數。")