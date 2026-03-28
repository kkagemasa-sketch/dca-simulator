import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="積立シミュレーター", layout="wide")

# =============================================================================
# CSS — ダークチャコール + ゴールドアクセント
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');

/* 全体 */
.stApp {
    background: #1e1e24 !important;
    font-family: 'Noto Sans JP', sans-serif !important;
}

/* ヘッダー */
.app-header {
    text-align: center;
    padding: 20px 0 28px 0;
}
.app-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #e2b96f;
    margin-bottom: 4px;
}
.app-header .sub {
    color: #8a857e;
    font-size: 0.85rem;
}
.app-header .line {
    width: 60px;
    height: 2px;
    background: #e2b96f;
    margin: 12px auto 0;
    border-radius: 1px;
}

/* カード */
.card {
    background: #282830;
    border-radius: 12px;
    padding: 18px 22px 10px;
    border-left: 4px solid var(--accent, #e2b96f);
}
.card h3 {
    font-size: 0.95rem;
    font-weight: 700;
    margin: 0 0 6px 0;
    color: var(--accent, #e2b96f);
}
.card.lump   { --accent: #5dade2; }
.card.dca    { --accent: #eb8a60; }
.card.cmp    { --accent: #a78bfa; }

/* セクション見出し */
.sec {
    font-size: 1rem;
    font-weight: 700;
    color: #e8e4de;
    margin: 32px 0 14px 0;
    padding-left: 14px;
    border-left: 4px solid #e2b96f;
}

/* リスク指標 */
.risk-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}
.risk-label {
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 8px;
}
.risk-label.lump { color: #5dade2; }
.risk-label.dca  { color: #eb8a60; }
.risk-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}
.rcard {
    background: #2f2f38;
    border-radius: 10px;
    padding: 14px 10px;
    text-align: center;
}
.rcard .rl { font-size: 0.75rem; color: #8a857e; margin-bottom: 6px; }
.rcard .rv { font-size: 1.15rem; font-weight: 700; }
.rcard .rv.good { color: #5dd39e; }
.rcard .rv.warn { color: #e2b96f; }
.rcard .rv.bad  { color: #ef6f6c; }
.rcard .rd { font-size: 0.65rem; color: #6b6760; margin-top: 6px; line-height: 1.4; }

/* 初期画面 */
.init { text-align: center; padding: 80px 20px; }
.init p { color: #6b6760; font-size: 1rem; line-height: 2; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ヘッダー
# =============================================================================
st.markdown("""
<div class="app-header">
    <h1>積立シミュレーター</h1>
    <div class="sub">一括投資 vs 積立投資の効果を比較</div>
    <div class="line"></div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# プリセット銘柄
# =============================================================================
PRESETS = {
    "自分で入力": "",
    "S&P500 (^GSPC)": "^GSPC",
    "日経225 (^N225)": "^N225",
    "TOPIX (1306.T)": "1306.T",
    "全世界株 VT": "VT",
    "米国株 VTI": "VTI",
    "S&P500 VOO": "VOO",
    "NASDAQ100 QQQ": "QQQ",
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "eMAXIS Slim 全世界 (2559.T)": "2559.T",
}
PERIOD_OPTIONS = {"1年": 1, "5年": 5, "10年": 10, "15年": 15, "20年": 20}

# 歴史的イベント
EVENTS = {
    "ITバブル崩壊": "2000-03-01",
    "同時多発テロ": "2001-09-01",
    "リーマンショック": "2008-09-01",
    "欧州債務危機": "2011-08-01",
    "チャイナショック": "2015-08-01",
    "コロナショック": "2020-03-01",
    "ウクライナ侵攻": "2022-02-01",
}

# =============================================================================
# 設定パネル（メインエリア上部）
# =============================================================================
with st.container():
    s1, s2, s3, s4 = st.columns([2, 2, 2, 1])

    with s1:
        st.markdown("**銘柄**")
        preset = st.selectbox("プリセット", list(PRESETS.keys()), label_visibility="collapsed")
        if preset == "自分で入力":
            ticker = st.text_input("ティッカー", value="^GSPC", help="Yahoo Financeのティッカーを入力")
        else:
            ticker = PRESETS[preset]
        compare_mode = st.checkbox("銘柄を比較する")
        if compare_mode:
            preset2 = st.selectbox("比較銘柄", [k for k in PRESETS.keys() if k != "自分で入力"], index=3)
            ticker2 = PRESETS[preset2]

    with s2:
        st.markdown("**投資期間**")
        period_label = st.radio(
            "期間", list(PERIOD_OPTIONS.keys()), index=2, horizontal=True, label_visibility="collapsed",
        )
        period_years = PERIOD_OPTIONS[period_label]
        end_date = datetime.now()
        start_date = end_date - relativedelta(years=period_years)
        st.caption(f"{start_date.strftime('%Y/%m')} ~ {end_date.strftime('%Y/%m')}")

    with s3:
        st.markdown("**投資金額**")
        investment_str = st.text_input(
            "総投資額", value="1,200,000", label_visibility="collapsed",
            help="数字を入力（カンマは自動付与）",
        )
        try:
            total_investment = int(investment_str.replace(",", "").replace("，", "").strip())
            if total_investment < 10000:
                total_investment = 10000
        except ValueError:
            total_investment = 1200000
            st.warning("数字を入力してください")
        st.caption(f"総投資額: **{total_investment:,.0f}**")
        frequency = st.radio("積立頻度", ["月次", "年次"], horizontal=True)
        months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))
        if frequency == "月次":
            periodic_amount = total_investment / months
            st.caption(f"月々: **{periodic_amount:,.0f}**")
        else:
            periodic_amount = total_investment / max(1, period_years)
            st.caption(f"年間: **{periodic_amount:,.0f}**")

    with s4:
        st.markdown("**オプション**")
        show_events = st.checkbox("歴史イベント", value=True)
        st.markdown("")
        run_sim = st.button("実行", type="primary", use_container_width=True)

st.divider()


# =============================================================================
# 計算関数
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_price_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)
    if data.empty:
        return None
    monthly = data["Close"].resample("ME").last().dropna()
    if hasattr(monthly, "columns"):
        monthly = monthly.squeeze()
    return monthly


def simulate_lump_sum(prices, total_investment):
    initial_price = prices.iloc[0]
    shares = total_investment / initial_price
    records = []
    for date, price in prices.items():
        value = shares * price
        records.append({
            "日付": date, "株価": price,
            "購入口数": shares if date == prices.index[0] else 0,
            "累計口数": shares, "投資額累計": total_investment,
            "評価額": value, "損益": value - total_investment,
            "損益率(%)": (value / total_investment - 1) * 100,
        })
    return pd.DataFrame(records)


def simulate_dca(prices, total_investment, frequency):
    if frequency == "月次":
        n_periods = len(prices)
        periodic_amount = total_investment / n_periods
    else:
        years = max(1, (prices.index[-1].year - prices.index[0].year))
        periodic_amount = total_investment / years

    cumulative_shares = 0
    cumulative_invested = 0
    records = []
    invest_years_done = set()

    for date, price in prices.items():
        purchased = 0
        if frequency == "月次":
            purchased = periodic_amount / price
            cumulative_shares += purchased
            cumulative_invested += periodic_amount
        else:
            year = date.year
            if year not in invest_years_done:
                invest_years_done.add(year)
                purchased = periodic_amount / price
                cumulative_shares += purchased
                cumulative_invested += periodic_amount

        value = cumulative_shares * price
        records.append({
            "日付": date, "株価": price,
            "購入口数": purchased, "累計口数": cumulative_shares,
            "投資額累計": cumulative_invested, "評価額": value,
            "損益": value - cumulative_invested if cumulative_invested > 0 else 0,
            "損益率(%)": (value / cumulative_invested - 1) * 100 if cumulative_invested > 0 else 0,
        })
    return pd.DataFrame(records)


def calc_cagr(start_val, end_val, years):
    if start_val <= 0 or years <= 0:
        return 0
    return ((end_val / start_val) ** (1 / years) - 1) * 100


def calc_risk_metrics(df):
    values = df["評価額"].values
    invested = df["投資額累計"].values

    # 最大ドローダウン
    peak = np.maximum.accumulate(values)
    drawdowns = (values - peak) / peak * 100
    max_drawdown = drawdowns.min()

    # 元本割れ月数
    underwater_months = int(np.sum(values < invested))
    total_months = len(values)

    # シャープレシオ（株価ベースの月次リターンで計算）
    monthly_returns = pd.Series(values).pct_change().dropna()
    if len(monthly_returns) < 2:
        return max_drawdown, underwater_months, total_months, 0
    annual_return = monthly_returns.mean() * 12
    annual_vol = monthly_returns.std() * np.sqrt(12)
    sharpe = (annual_return / annual_vol) if annual_vol > 0 else 0

    # 回復期間（最大下落の底からピーク水準に戻るまでの月数）
    dd_bottom_idx = np.argmin(drawdowns)
    peak_at_bottom = peak[dd_bottom_idx]
    recovery_months = None  # None = 未回復
    for i in range(dd_bottom_idx + 1, len(values)):
        if values[i] >= peak_at_bottom:
            recovery_months = i - dd_bottom_idx
            break

    return max_drawdown, underwater_months, total_months, sharpe, recovery_months


# =============================================================================
# Plotlyテーマ
# =============================================================================
BG = "#1e1e24"
CHART_LAYOUT = dict(
    plot_bgcolor=BG,
    paper_bgcolor=BG,
    font=dict(family="Noto Sans JP, sans-serif", color="#b0aca6", size=12),
    xaxis=dict(gridcolor="#33333a", zeroline=False, tickfont=dict(size=11, color="#8a857e")),
    yaxis=dict(gridcolor="#33333a", zeroline=False, tickformat=",", tickfont=dict(size=11, color="#8a857e")),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
        font=dict(size=12, color="#c0bdb7"),
    ),
    margin=dict(l=60, r=20, t=40, b=40),
    hovermode="x unified",
    modebar=dict(
        bgcolor="rgba(0,0,0,0)",
        color="#8a857e",
        activecolor="#e2b96f",
    ),
)

LUMP_COLOR = "#5dade2"
DCA_COLOR = "#eb8a60"
INVESTED_COLOR = "#5dd39e"
COMPARE_COLOR = "#a78bfa"


# =============================================================================
# メイン処理
# =============================================================================
if run_sim:
    with st.spinner("データを取得中..."):
        prices = fetch_price_data(ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        prices2 = None
        if compare_mode:
            prices2 = fetch_price_data(ticker2, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    if prices is None or len(prices) == 0:
        st.error("データを取得できませんでした。ティッカーシンボルと期間を確認してください。")
    else:
        lump_df = simulate_lump_sum(prices, total_investment)
        dca_df = simulate_dca(prices, total_investment, frequency)
        freq_label = "積立（月次）" if frequency == "月次" else "積立（年次）"

        final_lump = lump_df.iloc[-1]
        final_dca = dca_df.iloc[-1]

        lump_cagr = calc_cagr(total_investment, final_lump["評価額"], period_years)
        dca_cagr = calc_cagr(total_investment, final_dca["評価額"], period_years)

        lump_dd, lump_uw, lump_total, lump_sharpe, lump_recovery = calc_risk_metrics(lump_df)
        dca_dd, dca_uw, dca_total, dca_sharpe, dca_recovery = calc_risk_metrics(dca_df)

        # =====================================================================
        # サマリーカード
        # =====================================================================
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f'<div class="card lump"><h3>一括投資 ― {ticker}</h3></div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("総投資額", f"{final_lump['投資額累計']:,.0f}")
            m2.metric("最終評価額", f"{final_lump['評価額']:,.0f}")
            m3.metric("年平均利回り", f"{lump_cagr:+.1f}%")
            m4, m5 = st.columns(2)
            m4.metric("損益", f"{final_lump['損益']:,.0f}", delta=f"{final_lump['損益']:+,.0f}")
            m5.metric("リターン", f"{final_lump['損益率(%)']:.1f}%", delta=f"{final_lump['損益率(%)']:+.1f}%")

        with col2:
            st.markdown(f'<div class="card dca"><h3>{freq_label} ― {ticker}</h3></div>', unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("総投資額", f"{final_dca['投資額累計']:,.0f}")
            m2.metric("最終評価額", f"{final_dca['評価額']:,.0f}")
            m3.metric("年平均利回り", f"{dca_cagr:+.1f}%")
            m4, m5 = st.columns(2)
            m4.metric("損益", f"{final_dca['損益']:,.0f}", delta=f"{final_dca['損益']:+,.0f}")
            m5.metric("リターン", f"{final_dca['損益率(%)']:.1f}%", delta=f"{final_dca['損益率(%)']:+.1f}%")

        # =====================================================================
        # リスク指標
        # =====================================================================
        st.markdown('<div class="sec">リスク指標</div>', unsafe_allow_html=True)

        def rc(val, t):
            if t == "dd":
                return "bad" if val < -15 else ("warn" if val < -5 else "good")
            elif t == "uw":
                ratio = val[0] / val[1] if val[1] > 0 else 0
                return "bad" if ratio > 0.5 else ("warn" if ratio > 0.2 else "good")
            elif t == "rec":
                if val is None:
                    return "bad"
                return "bad" if val > 24 else ("warn" if val > 6 else "good")
            return "good" if val > 1 else ("warn" if val > 0.5 else "bad")

        def fmt_recovery(months):
            if months is None:
                return "未回復"
            if months >= 12:
                return f"{months // 12}年{months % 12}ヶ月"
            return f"{months}ヶ月"

        # リスク指標カード（Streamlit popoverで解説付き）
        def render_risk_row(label_class, label_text, dd_val, uw_val, uw_total, sharpe_val, recovery_val):
            st.markdown(f'<div class="risk-label {label_class}">{label_text}</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown(f"""<div class="rcard">
                    <div class="rl">最大下落率</div>
                    <div class="rv {rc(dd_val,'dd')}">{dd_val:.1f}%</div>
                    <div class="rd">最高値からの最大下落幅<br>小さいほど安定</div>
                </div>""", unsafe_allow_html=True)
                with st.popover("最大下落率とは？"):
                    st.markdown("""
**最大下落率**は、投資期間中に評価額が最高値からどれだけ下がったかを表します。

`最大下落率 = (最安値 − 最高値) / 最高値 × 100`

例えば **-30%** なら、最高値100万円のときに70万円まで下がった瞬間があったことを意味します。

| 数値 | 評価 |
|------|------|
| -5%以内 | 安定 |
| -5%〜-15% | 普通 |
| -15%超 | 大きな下落 |

0%に近いほどリスクが低いことを示します。
""")

            with c2:
                st.markdown(f"""<div class="rcard">
                    <div class="rl">元本割れ月数</div>
                    <div class="rv {rc((uw_val, uw_total),'uw')}">{uw_val} / {uw_total}ヶ月</div>
                    <div class="rd">投資額を下回った期間<br>少ないほど安心</div>
                </div>""", unsafe_allow_html=True)
                with st.popover("元本割れ月数とは？"):
                    st.markdown("""
**元本割れ月数**は、評価額が投資額を**下回っていた月数**です。

例: 「12 / 240ヶ月」→ 20年のうち12ヶ月だけ元本割れ → 95%の期間はプラス

| 割合 | 評価 |
|------|------|
| 20%以下 | 安心 |
| 20%〜50% | 我慢が必要な時期あり |
| 50%超 | 半分以上マイナス |

積立投資は序盤に元本割れしやすいですが、長期で回復する傾向があります。
""")

            with c3:
                st.markdown(f"""<div class="rcard">
                    <div class="rl">投資効率</div>
                    <div class="rv {rc(sharpe_val,'sharpe')}">{sharpe_val:.2f}</div>
                    <div class="rd">リスクあたりのリターン<br>1.0以上なら優秀</div>
                </div>""", unsafe_allow_html=True)
                with st.popover("投資効率とは？"):
                    st.markdown("""
**投資効率（シャープレシオ）**は、リスクに対してどれだけ効率よくリターンを得られたかの指標です。

`投資効率 = 年間リターン / 年間の値動きの大きさ`

| 数値 | 評価 |
|------|------|
| 1.0以上 | 優秀 |
| 0.5〜1.0 | 普通 |
| 0.5未満 | 効率が悪い |

**具体例:**
- 銘柄A: リターン10%、値動き10% → 投資効率 **1.0**
- 銘柄B: リターン10%、値動き20% → 投資効率 **0.5**

同じリターンでもBは値動きが激しい分「効率が悪い」と判断されます。つまり**同じリターンなら値動きが小さい方が良い投資**です。
""")

            with c4:
                st.markdown(f"""<div class="rcard">
                    <div class="rl">回復期間</div>
                    <div class="rv {rc(recovery_val,'rec')}">{fmt_recovery(recovery_val)}</div>
                    <div class="rd">最大下落からの回復<br>短いほど安心</div>
                </div>""", unsafe_allow_html=True)
                with st.popover("回復期間とは？"):
                    st.markdown("""
**回復期間**は、最大下落の底値から元の水準に戻るまでにかかった期間です。

例: 「1年6ヶ月」→ 最大下落後、元に戻るまで1年半。この間ずっと含み損。

| 期間 | 評価 |
|------|------|
| 6ヶ月以内 | 一時的な調整 |
| 6ヶ月〜2年 | 我慢が必要 |
| 2年超・未回復 | 忍耐力が試される |

「未回復」は選択期間内でまだ最高値に戻っていないことを意味します。積立NISAでも暴落後の回復に数年かかることがあり、その間に売ると損が確定します。
""")

        rcol1, rcol2 = st.columns(2)
        with rcol1:
            render_risk_row("lump", "一括投資", lump_dd, lump_uw, lump_total, lump_sharpe, lump_recovery)
        with rcol2:
            render_risk_row("dca", "積立投資", dca_dd, dca_uw, dca_total, dca_sharpe, dca_recovery)

        # =====================================================================
        # 資産推移チャート（アニメーション付き）
        # =====================================================================
        st.markdown('<div class="sec">資産推移</div>', unsafe_allow_html=True)

        n_points = len(lump_df)
        n_frames = min(30, n_points)
        frame_indices = np.linspace(1, n_points, n_frames, dtype=int)

        frames = []
        for idx in frame_indices:
            frame_data = [
                go.Scatter(
                    x=lump_df["日付"].iloc[:idx], y=lump_df["評価額"].iloc[:idx],
                    name="一括投資", line=dict(color=LUMP_COLOR, width=2.5),
                    fill="tozeroy", fillcolor="rgba(93,173,226,0.08)",
                ),
                go.Scatter(
                    x=dca_df["日付"].iloc[:idx], y=dca_df["評価額"].iloc[:idx],
                    name=freq_label, line=dict(color=DCA_COLOR, width=2.5),
                ),
                go.Scatter(
                    x=dca_df["日付"].iloc[:idx], y=dca_df["投資額累計"].iloc[:idx],
                    name="投資額累計", line=dict(color=INVESTED_COLOR, width=1.5, dash="dash"),
                ),
            ]
            frames.append(go.Frame(data=frame_data, name=str(idx)))

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=lump_df["日付"], y=lump_df["評価額"],
                    name="一括投資", line=dict(color=LUMP_COLOR, width=2.5),
                    fill="tozeroy", fillcolor="rgba(93,173,226,0.08)",
                    hovertemplate="%{x|%Y/%m}<br>%{y:,.0f}<extra>一括投資</extra>",
                ),
                go.Scatter(
                    x=dca_df["日付"], y=dca_df["評価額"],
                    name=freq_label, line=dict(color=DCA_COLOR, width=2.5),
                    hovertemplate="%{x|%Y/%m}<br>%{y:,.0f}<extra>" + freq_label + "</extra>",
                ),
                go.Scatter(
                    x=dca_df["日付"], y=dca_df["投資額累計"],
                    name="投資額累計", line=dict(color=INVESTED_COLOR, width=1.5, dash="dash"),
                    hovertemplate="%{x|%Y/%m}<br>%{y:,.0f}<extra>投資額累計</extra>",
                ),
            ],
            frames=frames,
        )
        fig.update_layout(
            **CHART_LAYOUT,
            height=480,
            updatemenus=[dict(
                type="buttons", showactive=False,
                x=0.0, y=1.15,
                font=dict(color="#e8e4de"),
                buttons=[
                    dict(label="  再生  ", method="animate",
                         args=[None, {"frame": {"duration": 80, "redraw": True}, "fromcurrent": True}]),
                    dict(label="  リセット  ", method="animate",
                         args=[[frames[0].name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]),
                ],
            )],
        )
        # 歴史イベント縦線
        if show_events:
            chart_start = lump_df["日付"].iloc[0]
            chart_end = lump_df["日付"].iloc[-1]
            event_colors = ["#ef6f6c", "#e2b96f", "#a78bfa", "#5dade2", "#eb8a60", "#5dd39e", "#c792ea"]
            for i, (name, date_str) in enumerate(EVENTS.items()):
                edate = pd.Timestamp(date_str)
                if chart_start <= edate <= chart_end:
                    color = event_colors[i % len(event_colors)]
                    fig.add_vline(
                        x=edate, line_dash="dot", line_color=color, line_width=1.5, opacity=0.7,
                    )
                    fig.add_annotation(
                        x=edate, y=1.0, yref="paper",
                        text=name, showarrow=False,
                        font=dict(size=10, color=color),
                        textangle=-90, xanchor="left", yanchor="top",
                        xshift=4,
                    )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})

        # =====================================================================
        # 複数銘柄比較
        # =====================================================================
        if compare_mode and prices2 is not None and len(prices2) > 0:
            st.markdown('<div class="sec">銘柄比較</div>', unsafe_allow_html=True)

            lump_df2 = simulate_lump_sum(prices2, total_investment)
            dca_df2 = simulate_dca(prices2, total_investment, frequency)
            final_lump2 = lump_df2.iloc[-1]
            final_dca2 = dca_df2.iloc[-1]

            lump_cagr2 = calc_cagr(total_investment, final_lump2["評価額"], period_years)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="card lump"><h3>{ticker}</h3></div>', unsafe_allow_html=True)
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("一括リターン", f"{final_lump['損益率(%)']:.1f}%")
                mc2.metric("積立リターン", f"{final_dca['損益率(%)']:.1f}%")
                mc3.metric("年平均利回り", f"{lump_cagr:+.1f}%")
            with c2:
                st.markdown(f'<div class="card cmp"><h3>{ticker2}</h3></div>', unsafe_allow_html=True)
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("一括リターン", f"{final_lump2['損益率(%)']:.1f}%")
                mc2.metric("積立リターン", f"{final_dca2['損益率(%)']:.1f}%")
                mc3.metric("年平均利回り", f"{lump_cagr2:+.1f}%")

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(
                x=lump_df["日付"], y=lump_df["評価額"] / total_investment,
                name=f"{ticker} 一括", line=dict(color=LUMP_COLOR, width=2),
                hovertemplate="%{x|%Y/%m}<br>倍率: %{y:.2f}x<extra></extra>",
            ))
            fig_comp.add_trace(go.Scatter(
                x=lump_df2["日付"], y=lump_df2["評価額"] / total_investment,
                name=f"{ticker2} 一括", line=dict(color=COMPARE_COLOR, width=2),
                hovertemplate="%{x|%Y/%m}<br>倍率: %{y:.2f}x<extra></extra>",
            ))
            fig_comp.add_hline(y=1.0, line_dash="dash", line_color="rgba(255,255,255,0.1)")
            fig_comp.update_layout(
                **CHART_LAYOUT, height=380,
                yaxis_title="投資倍率", yaxis_tickformat=".1f",
            )
            st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})

        # =====================================================================
        # 開始タイミング比較
        # =====================================================================
        with st.expander("開始タイミングの影響 ― 始めた時期で結果はどう変わる？", expanded=False):
            st.caption("同じ銘柄・同じ金額・同じ期間でも、投資を始めた年が違うだけで結果が大きく変わります。")
            timing_colors = ["#5dade2", "#eb8a60", "#5dd39e", "#a78bfa", "#e2b96f"]
            fig_timing = go.Figure()
            offsets = [0, 1, 2, 3, 4]  # 0=現在の設定, 1~4年前にずらす

            timing_results = []
            for offset in offsets:
                t_end = end_date - relativedelta(years=offset)
                t_start = t_end - relativedelta(years=period_years)
                t_prices = fetch_price_data(ticker, t_start.strftime("%Y-%m-%d"), t_end.strftime("%Y-%m-%d"))
                if t_prices is not None and len(t_prices) > 1:
                    t_dca = simulate_dca(t_prices, total_investment, frequency)
                    label = f"{t_start.strftime('%Y')}年開始"
                    final_return = t_dca.iloc[-1]["損益率(%)"]
                    timing_results.append((label, final_return))
                    # X軸を経過月数に統一
                    months_elapsed = list(range(len(t_dca)))
                    fig_timing.add_trace(go.Scatter(
                        x=months_elapsed, y=t_dca["評価額"],
                        name=f"{label}（{final_return:+.1f}%）",
                        line=dict(color=timing_colors[offset % len(timing_colors)], width=2),
                        hovertemplate="経過%{{x}}ヶ月<br>評価額: %{{y:,.0f}}<extra>{label}</extra>",
                    ))

            # 投資額累計の参考線
            if len(timing_results) > 0:
                t_dca_ref = simulate_dca(prices, total_investment, frequency)
                fig_timing.add_trace(go.Scatter(
                    x=list(range(len(t_dca_ref))), y=t_dca_ref["投資額累計"],
                    name="投資額累計", line=dict(color="#6b6760", width=1.5, dash="dash"),
                ))

            fig_timing.update_layout(
                **CHART_LAYOUT, height=400,
                xaxis_title="経過月数", yaxis_title="評価額",
            )
            st.plotly_chart(fig_timing, use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})

            if timing_results:
                best = max(timing_results, key=lambda x: x[1])
                worst = min(timing_results, key=lambda x: x[1])
                diff = best[1] - worst[1]
                st.markdown(f"""
                <div class="rcard" style="margin-top: 8px; text-align: left; padding: 16px 20px;">
                    <div class="rd" style="font-size: 0.85rem; color: #c0bdb7; line-height: 1.8;">
                        最もリターンが高い: <strong style="color: #5dd39e;">{best[0]}（{best[1]:+.1f}%）</strong><br>
                        最もリターンが低い: <strong style="color: #ef6f6c;">{worst[0]}（{worst[1]:+.1f}%）</strong><br>
                        開始時期の違いだけで <strong style="color: #e2b96f;">{diff:.1f}%</strong> の差がつきました。
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # =====================================================================
        # 出口リスク
        # =====================================================================
        with st.expander("出口リスク ― いつ売るかで結果が変わる", expanded=False):
            st.caption("各月時点で全額売却した場合の損益率です。売り時を間違えると、積立でも大きな損失になります。")
            exit_tab1, exit_tab2 = st.tabs(["一括投資", freq_label])

            def make_exit_chart(df, chart_name):
                pnl_pct = df["損益率(%)"].values
                colors = ["#5dd39e" if v >= 0 else "#ef6f6c" for v in pnl_pct]
                fig_exit = go.Figure()
                fig_exit.add_trace(go.Bar(
                    x=df["日付"], y=pnl_pct,
                    marker_color=colors,
                    hovertemplate="%{x|%Y/%m}<br>損益率: %{y:.1f}%<extra></extra>",
                ))
                fig_exit.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1)
                fig_exit.update_layout(
                    **CHART_LAYOUT, height=350,
                    yaxis_title="損益率（%）", yaxis_ticksuffix="%",
                    showlegend=False,
                )
                return fig_exit

            with exit_tab1:
                st.plotly_chart(make_exit_chart(lump_df, "一括"), use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})
                neg_months_l = int((lump_df["損益率(%)"] < 0).sum())
                st.markdown(f'<div class="rd" style="font-size:0.82rem; color:#8a857e; text-align:center;">'
                            f'全{len(lump_df)}ヶ月中 <strong style="color:#ef6f6c;">{neg_months_l}ヶ月</strong> が売却損（赤）'
                            f'</div>', unsafe_allow_html=True)

            with exit_tab2:
                st.plotly_chart(make_exit_chart(dca_df, "積立"), use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})
                neg_months_d = int((dca_df["損益率(%)"] < 0).sum())
                st.markdown(f'<div class="rd" style="font-size:0.82rem; color:#8a857e; text-align:center;">'
                            f'全{len(dca_df)}ヶ月中 <strong style="color:#ef6f6c;">{neg_months_d}ヶ月</strong> が売却損（赤）'
                            f'</div>', unsafe_allow_html=True)

        # =====================================================================
        # 株価推移
        # =====================================================================
        with st.expander("株価推移", expanded=False):
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(
                x=prices.index, y=prices.values,
                name=ticker, line=dict(color=LUMP_COLOR, width=1.5),
                fill="tozeroy", fillcolor="rgba(93,173,226,0.06)",
                hovertemplate="%{x|%Y/%m}<br>%{y:,.2f}<extra></extra>",
            ))
            if compare_mode and prices2 is not None:
                fig_price.add_trace(go.Scatter(
                    x=prices2.index, y=prices2.values,
                    name=ticker2, line=dict(color=COMPARE_COLOR, width=1.5),
                    yaxis="y2",
                    hovertemplate="%{x|%Y/%m}<br>%{y:,.2f}<extra></extra>",
                ))
                fig_price.update_layout(
                    yaxis2=dict(
                        overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)", tickformat=",",
                        tickfont=dict(color=COMPARE_COLOR, size=10),
                    ),
                )
            fig_price.update_layout(**CHART_LAYOUT, height=300, yaxis_title="")
            st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]})

        # =====================================================================
        # 詳細データ
        # =====================================================================
        with st.expander("詳細データ", expanded=False):
            tab1, tab2 = st.tabs(["一括投資", freq_label])

            def format_table(df):
                display_df = df.copy()
                display_df["日付"] = display_df["日付"].dt.strftime("%Y-%m")
                for col in ["株価", "投資額累計", "評価額", "損益"]:
                    display_df[col] = display_df[col].map(lambda x: f"{x:,.0f}")
                display_df["購入口数"] = display_df["購入口数"].map(lambda x: f"{x:.4f}")
                display_df["累計口数"] = display_df["累計口数"].map(lambda x: f"{x:.4f}")
                display_df["損益率(%)"] = display_df["損益率(%)"].map(lambda x: f"{x:.2f}%")
                return display_df

            with tab1:
                st.dataframe(format_table(lump_df), use_container_width=True, hide_index=True)
            with tab2:
                st.dataframe(format_table(dca_df), use_container_width=True, hide_index=True)
else:
    st.markdown("""
    <div class="init">
        <p>上の設定を入力し<br><strong>実行</strong> を押してください</p>
    </div>
    """, unsafe_allow_html=True)
