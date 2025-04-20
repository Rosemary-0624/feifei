import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests
import oss2
from io import BytesIO


def load_data_from_oss():
    """从阿里云 OSS 加载数据"""
    # 阿里云 OSS 配置
    auth = oss2.Auth(
        st.secrets["ali_oss"]["access_key_id"],
        st.secrets["ali_oss"]["access_key_secret"]
    )
    bucket = oss2.Bucket(
        auth,
        st.secrets["ali_oss"]["endpoint"],
        st.secrets["ali_oss"]["bucket_name"]
    )
    
    # 读取数据
    sleep_obj = bucket.get_object('sleep_data.xlsx')
    feeding_obj = bucket.get_object('feeding_data.xlsx')
    
    sleep_df = pd.read_excel(BytesIO(sleep_obj.read()), parse_dates=['日期'])
    feeding_df = pd.read_excel(BytesIO(feeding_obj.read()), parse_dates=['日期'])
    
    return sleep_df, feeding_df


def filter_data_by_date_range(df, start_date, end_date):
    """按日期范围筛选数据"""
    return df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]


def create_detailed_chart(sleep_df, feeding_df):
    """创建详细的睡眠和喂奶记录图"""
    # 获取所有唯一日期并排序
    all_dates = sorted(set(sleep_df['日期'].dt.date) | set(feeding_df['日期'].dt.date))
    
    # 创建y轴标签
    y_labels = []
    for date in all_dates:
        y_labels.extend([f"{date} 睡眠", f"{date} 喂奶"])
    
    # 创建参考日期（用于将所有时间映射到同一天）
    ref_date = datetime.date(2000, 1, 1)
    
    fig = go.Figure()
    
    # 修改睡眠记录部分
    for _, row in sleep_df.iterrows():
        try:
            date = row['日期'].date()
            start_time = row['入睡'].time() if isinstance(row['入睡'], datetime.datetime) else row['入睡']
            end_time = row['睡醒'].time() if isinstance(row['睡醒'], datetime.datetime) else row['睡醒']
            
            if start_time and end_time:
                # 将时间映射到参考日期
                start_dt = datetime.datetime.combine(ref_date, start_time)
                end_dt = datetime.datetime.combine(ref_date, end_time)
                
                # 处理跨夜情况
                if end_dt < start_dt:
                    end_dt = datetime.datetime.combine(ref_date + datetime.timedelta(days=1), end_time)
                
                duration = row['总睡眠时间（mins）'] / 60  # 转换为小时
                
                # 关键修改：使用两个时间点创建横道
                fig.add_trace(go.Scatter(
                    x=[start_dt, end_dt],
                    y=[f"{date} 睡眠", f"{date} 睡眠"],
                    mode='lines',
                    line=dict(
                        color='rgb(68, 114, 196)',
                        width=20,  # 增加线的宽度使其看起来像横道
                    ),
                    name='睡眠',
                    text=f"{duration:.1f}h",
                    showlegend=False,
                    hoverinfo="text"
                ))
        except Exception as e:
            st.write(f"处理睡眠数据出错: {str(e)}")
            continue

    # 添加喂奶记录（彩色圆点）
    colors = {
        '亲喂': 'rgb(255, 182, 193)',  # 粉色
        '配方奶': 'rgb(255, 192, 0)',  # 金黄色
        '母乳瓶喂': 'rgb(173, 216, 230)'  # 浅蓝色
    }
    
    # 为每种喂奶类型只创建一个图例
    for feeding_type, color in colors.items():
        df_type = feeding_df[feeding_df['哺乳类型'] == feeding_type]
        if not df_type.empty:
            # 创建所有数据点
            dates = df_type['日期'].dt.date
            times = df_type['哺乳时间'].apply(lambda x: x.time() if isinstance(x, datetime.datetime) else x)
            amounts = df_type['奶量(ml)']
            
            # 将时间映射到参考日期
            x_values = [datetime.datetime.combine(ref_date, t) for t in times]
            y_values = [f"{d} 喂奶" for d in dates]
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='markers',
                name=feeding_type,
                marker=dict(
                    size=[max(8, min(20, a/10)) if pd.notna(a) else 8 for a in amounts],
                    color=color,
                    symbol='circle'
                ),
                text=[f"{feeding_type}: {a}ml" if pd.notna(a) else feeding_type for a in amounts],
                hoverinfo="text"
            ))

    # 更新布局
    fig.update_layout(
        title="睡眠和喂奶记录",
        height=max(600, len(y_labels) * 30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(
            categoryarray=y_labels,
            categoryorder='array',
            ticktext=y_labels,
            tickvals=y_labels,
            autorange="reversed"
        ),
        xaxis=dict(
            type='date',
            tickformat="%H",  # 只显示小时数
            dtick="H1",      # 每小时显示一个刻度
            ticktext=[str(i) for i in range(24)],  # 0-23小时
            tickvals=[
                datetime.datetime.combine(ref_date, datetime.time(i, 0))
                for i in range(24)
            ],
            range=[
                datetime.datetime.combine(ref_date, datetime.time(0, 0)),
                datetime.datetime.combine(ref_date + datetime.timedelta(days=1), datetime.time(0, 0))
            ],
            gridcolor='rgba(128,128,128,0.2)',
            showgrid=True,
            tickmode='array'  # 使用自定义刻度
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig


def create_daily_stats_charts(sleep_df, feeding_df):
    """创建每日统计图表"""
    # 计算每日总睡眠时长
    daily_sleep = sleep_df.groupby('日期')['总睡眠时间（mins）'].sum().reset_index()
    daily_sleep['总睡眠时间(小时)'] = daily_sleep['总睡眠时间（mins）'] / 60
    
    # 计算每日总奶量
    daily_milk = feeding_df.groupby('日期')['奶量(ml)'].sum().reset_index()
    
    # 创建两个折线图
    fig = make_subplots(rows=2, cols=1, subplot_titles=('每日睡眠时长', '每日奶量'))
    
    # 睡眠时长折线图
    fig.add_trace(
        go.Scatter(
            x=daily_sleep['日期'],
            y=daily_sleep['总睡眠时间(小时)'],
            mode='lines+markers+text',  # 添加文本模式
            name='睡眠时长(小时)',
            line=dict(color='rgb(68, 114, 196)'),
            text=[f'{x:.1f}h' for x in daily_sleep['总睡眠时间(小时)']],  # 格式化为1位小数
            textposition='top center',  # 文本位置
            textfont=dict(size=10)  # 文本字体大小
        ),
        row=1, col=1
    )
    
    # 奶量折线图
    fig.add_trace(
        go.Scatter(
            x=daily_milk['日期'],
            y=daily_milk['奶量(ml)'],
            mode='lines+markers+text',  # 添加文本模式
            name='奶量(ml)',
            line=dict(color='rgb(255, 192, 0)'),
            text=[f'{int(x)}ml' for x in daily_milk['奶量(ml)']],  # 格式化为整数
            textposition='top center',  # 文本位置
            textfont=dict(size=10)  # 文本字体大小
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        height=800, 
        showlegend=True,
        # 更新y轴格式
        yaxis=dict(
            tickformat='.1f',  # 睡眠时长显示1位小数
            title='睡眠时长(小时)'
        ),
        yaxis2=dict(
            tickformat='d',  # 奶量显示整数
            title='奶量(ml)'
        )
    )
    
    return fig


def load_data_from_github():
    """从 GitHub 加载数据"""
    # GitHub raw 文件链接
    sleep_url = "https://raw.githubusercontent.com/Rosemary-0624/feifei/main/data/sleep_data.csv"
    feeding_url = "https://raw.githubusercontent.com/Rosemary-0624/feifei/main/data/feeding_data.csv"
    
    try:
        # 读取数据
        sleep_df = pd.read_csv(sleep_url, parse_dates=['日期'])
        feeding_df = pd.read_csv(feeding_url, parse_dates=['日期'])
        
        return sleep_df, feeding_df
    except Exception as e:
        st.error(f"从GitHub加载数据失败: {str(e)}")
        return None, None


def main():
    st.title("婴儿睡眠和喂奶记录")
    
    # 添加页面配置以优化移动端显示
    st.set_page_config(
        page_title="婴儿睡眠和喂奶记录",
        page_icon="👶",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 添加自定义 CSS 以优化移动端显示
    st.markdown("""
        <style>
        .reportview-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-right: 1rem;
            padding-left: 1rem;
            margin: 0 auto;
        }
        .stPlotlyChart {
            width: 100%;
            height: auto !important;
        }
        @media (max-width: 768px) {
            .reportview-container {
                padding: 1rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    
    try:
        # 从 GitHub 加载数据
        sleep_df, feeding_df = load_data_from_github()
        if sleep_df is None or feeding_df is None:
            st.error("无法加载数据，请检查数据源")
            return
        
        # 日期范围选择
        st.subheader("选择数据显示范围")
        date_range = st.radio(
            "选择时间范围",
            ["近一周", "近半月", "近一月", "全部数据", "自定义范围"]
        )
        
        # 确定日期范围
        end_date = sleep_df['日期'].max()
        if date_range == "近一周":
            start_date = end_date - pd.Timedelta(days=7)
        elif date_range == "近半月":
            start_date = end_date - pd.Timedelta(days=15)
        elif date_range == "近一月":
            start_date = end_date - pd.Timedelta(days=30)
        elif date_range == "全部数据":
            start_date = sleep_df['日期'].min()
        else:  # 自定义范围
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("开始日期", 
                                         value=end_date - pd.Timedelta(days=7))
            with col2:
                end_date = st.date_input("结束日期", value=end_date)
            start_date = pd.Timestamp(start_date)
            end_date = pd.Timestamp(end_date)
        
        # 过滤数据
        sleep_df_filtered = filter_data_by_date_range(sleep_df, start_date, end_date)
        feeding_df_filtered = filter_data_by_date_range(feeding_df, start_date, end_date)
        
        # 显示图表
        st.plotly_chart(create_detailed_chart(sleep_df_filtered, feeding_df_filtered))
        st.plotly_chart(create_daily_stats_charts(sleep_df_filtered, feeding_df_filtered))

    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")


if __name__ == "__main__":
    main()
