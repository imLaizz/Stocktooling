"""
台股 K 線與均線分析（Streamlit）
資料來源：Yahoo Finance（上市：.TW，上櫃：.TWO）
"""

from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


def normalize_code(raw: str) -> str:
    s = raw.strip()
    digits = re.sub(r"\D", "", s)
    return digits[-4:] if len(digits) >= 4 else digits


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tw_stock_history(symbol: str) -> pd.DataFrame:
    t = yf.Ticker(symbol)
    df = t.history(period="1y", auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    return df.sort_index()


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA5"] = out["Close"].rolling(window=5, min_periods=1).mean()
    out["MA20"] = out["Close"].rolling(window=20, min_periods=1).mean()
    out["MA60"] = out["Close"].rolling(window=60, min_periods=1).mean()
    return out


def build_figure(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA5"],
            mode="lines",
            name="MA5",
            line=dict(color="#ff9800", width=1.2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA20"],
            mode="lines",
            name="MA20",
            line=dict(color="#2196f3", width=1.2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA60"],
            mode="lines",
            name="MA60",
            line=dict(color="#9c27b0", width=1.2),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="價格（TWD）",
        template="plotly_white",
        height=640,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_yaxes(tickformat=".2f", separatethousands=True)
    return fig


def main() -> None:
    st.set_page_config(page_title="台股分析", layout="wide")
    st.title("台股分析")
    st.caption("近一年日線 K 線與 5 / 20 / 60 日均線（資料來源：Yahoo Finance）")

    with st.sidebar:
        st.header("查詢")
        code_input = st.text_input("股號（4 位數字）", value="2330", help="例如：2330（台積電）")
        market = st.radio("市場別", ("上市 TWSE（.TW）", "上櫃 TPEx（.TWO）"), index=0)
        run = st.button("載入資料", type="primary")

    suffix = ".TW" if market.startswith("上市") else ".TWO"
    code = normalize_code(code_input)

    if not code or len(code) != 4:
        st.warning("請輸入 4 位數字股號。")
        return

    symbol = f"{code}{suffix}"

    if run:
        st.session_state["query_symbol"] = symbol

    sym = st.session_state.get("query_symbol")
    if sym is None:
        st.info("請在側欄輸入股號後按「載入資料」。")
        return

    with st.spinner(f"正在取得 {sym} 近一年資料…"):
        raw = fetch_tw_stock_history(sym)

    if raw.empty:
        st.error(
            f"無法取得 {sym} 的資料。請確認股號、上市/上櫃是否正確，或稍後再試。"
        )
        return

    data = add_moving_averages(raw)
    name = sym
    try:
        info = yf.Ticker(sym).info
        if isinstance(info, dict) and info.get("longName"):
            name = str(info["longName"])
    except Exception:
        pass

    st.subheader(f"{name}（{sym}）")
    c1, c2, c3, c4 = st.columns(4)
    last = data["Close"].iloc[-1]
    prev = data["Close"].iloc[-2] if len(data) > 1 else last
    chg = last - prev
    chg_pct = (chg / prev * 100) if prev else 0.0
    c1.metric("最新收盤", f"{last:.2f}")
    c2.metric("漲跌", f"{chg:+.2f}", f"{chg_pct:+.2f}%")
    c3.metric("MA5", f"{data['MA5'].iloc[-1]:.2f}")
    c4.metric("MA20 / MA60", f"{data['MA20'].iloc[-1]:.2f} / {data['MA60'].iloc[-1]:.2f}")

    fig = build_figure(data, f"{sym} — 近一年日線")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("原始資料預覽（最近 10 筆）"):
        show_cols = ["Open", "High", "Low", "Close", "Volume", "MA5", "MA20", "MA60"]
        preview = data[show_cols].tail(10).copy()
        for c in ("Open", "High", "Low", "Close", "MA5", "MA20", "MA60"):
            preview[c] = preview[c].round(2)
        preview["Volume"] = preview["Volume"].round(0).astype(int)
        st.dataframe(preview, use_container_width=True)


if __name__ == "__main__":
    main()
