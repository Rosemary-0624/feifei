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
        # 读取数据
        sleep_df = pd.read_csv(sleep_url, parse_dates=['日期'])
        feeding_df = pd.read_csv(feeding_url, parse_dates=['日期'])
        
        # 确保时间列的格式正确
        for df in [sleep_df, feeding_df]:
            for col in df.columns:
                if '时间' in col or '入睡' in col or '睡醒' in col:
                    df[col] = pd.to_datetime(df[col]).dt.time
        
        return sleep_df, feeding_df
    except Exception as e:
        st.error(f"从GitHub加载数据失败: {str(e)}")
        return None, None

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
    
    # 添加睡眠记录（蓝色横道）
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
                
                # 修改：使用线段来表示每段睡眠
                fig.add_trace(go.Scatter(
                    x=[start_dt, end_dt],
                    y=[f"{date} 睡眠", f"{date} 睡眠"],
                    mode='lines',
                    line=dict(
                        color='rgb(68, 114, 196)',
                        width=20,
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
            tickformat="%H",
            dtick="H1",
            ticktext=[str(i) for i in range(24)],
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
            tickmode='array'
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
            mode='lines+markers+text',
            name='睡眠时长(小时)',
            line=dict(color='rgb(68, 114, 196)'),
            text=[f'{x:.1f}h' for x in daily_sleep['总睡眠时间(小时)']],
            textposition='top center',
            textfont=dict(size=10)
        ),
        row=1, col=1
    )
    
    # 奶量折线图
    fig.add_trace(
        go.Scatter(
            x=daily_milk['日期'],
            y=daily_milk['奶量(ml)'],
            mode='lines+markers+text',
            name='奶量(ml)',
            line=dict(color='rgb(255, 192, 0)'),
            text=[f'{int(x)}ml' for x in daily_milk['奶量(ml)']],
            textposition='top center',
            textfont=dict(size=10)
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        height=800,
        showlegend=True,
        yaxis=dict(
            tickformat='.1f',
            title='睡眠时长(小时)'
        ),
        yaxis2=dict(
            tickformat='d',
            title='奶量(ml)'
        )
    )
    
    return fig

def main():
    st.title("婴儿睡眠和喂奶记录")
    
    try:
        # 从 GitHub 加载数据
        sleep_df, feeding_df = load_data_from_github()
        
        if sleep_df is None or feeding_df is None:
            st.error("无法加载数据，请检查数据源")
            return
            
        # 创建详细图表
        st.subheader("详细记录")
        detailed_chart = create_detailed_chart(sleep_df, feeding_df)
        st.plotly_chart(detailed_chart, use_container_width=True)
        
        # 创建每日统计图表
        st.subheader("每日统计")
        daily_stats = create_daily_stats_charts(sleep_df, feeding_df)
        st.plotly_chart(daily_stats, use_container_width=True)
        
    except Exception as e:
        st.error(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
