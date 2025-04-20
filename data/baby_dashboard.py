import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="婴儿睡眠和喂奶记录",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_data_from_github():
    """从 GitHub 加载数据"""
    # GitHub raw 文件链接
    base_url = "https://raw.githubusercontent.com/Rosemary-0624/feifei/main/data"
    sleep_url = f"{base_url}/sleep_data.csv"
    feeding_url = f"{base_url}/feeding_data.csv"
    
    try:
        # 读取睡眠数据
        sleep_df = pd.read_csv(sleep_url, sep='\t', encoding='utf-8')  # 使用制表符分隔
        feeding_df = pd.read_csv(feeding_url, sep='\t', encoding='utf-8')  # 使用制表符分隔
        
        # 重命名列
        sleep_df.columns = ['日期', '入睡', '睡醒', '总睡眠时间（mins）']
        feeding_df.columns = ['日期', '哺乳类型', '哺乳时间', '奶量(ml)']
        
        # 转换日期列
        sleep_df['日期'] = pd.to_datetime(sleep_df['日期'])
        feeding_df['日期'] = pd.to_datetime(feeding_df['日期'])
        
        # 转换时间列
        def parse_time(time_str):
            if pd.isna(time_str):
                return None
            try:
                # 处理 HH:MM 格式
                if ':' in str(time_str):
                    parts = str(time_str).split(':')
                    if len(parts) == 2:
                        time_str = f"{time_str}:00"
                    return datetime.datetime.strptime(time_str, '%H:%M:%S').time()
                return None
            except Exception:
                return None
        
        # 处理睡眠数据的时间列
        sleep_df['入睡'] = sleep_df['入睡'].apply(parse_time)
        sleep_df['睡醒'] = sleep_df['睡醒'].apply(parse_time)
        
        # 处理喂奶数据的时间列
        feeding_df['哺乳时间'] = feeding_df['哺乳时间'].apply(parse_time)
        
        # 确保数值列为数值类型
        sleep_df['总睡眠时间（mins）'] = pd.to_numeric(sleep_df['总睡眠时间（mins）'], errors='coerce')
        feeding_df['奶量(ml)'] = pd.to_numeric(feeding_df['奶量(ml)'], errors='coerce')
        
        # 打印调试信息
        st.write("睡眠数据列名:", sleep_df.columns.tolist())
        st.write("喂奶数据列名:", feeding_df.columns.tolist())
        st.write("睡眠数据示例:", sleep_df.head())
        st.write("喂奶数据示例:", feeding_df.head())
        
        return sleep_df, feeding_df
    except Exception as e:
        st.error(f"从GitHub加载数据失败: {str(e)}")
        return None, None

# ... [其余代码保持不变] ...
