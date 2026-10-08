# -*- coding: utf-8 -*-
"""
주식 주가 비교 보기 (Streamlit 앱)
- 종목 코드를 최대 2개까지 입력해 나란히 비교합니다.
- 기간(1개월·6개월·1년·5년)을 버튼으로 고를 수 있습니다.
- yfinance로 주가를 가져와 plotly 꺾은선 그래프와 지표 카드로 보여줍니다.
"""

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go


# ------------------------------------------------------------
# 1. 페이지 기본 설정 (반드시 다른 streamlit 명령보다 먼저 나와야 해요)
#    - 두 종목을 나란히 놓으려고 화면을 넓게(wide) 써요.
# ------------------------------------------------------------
st.set_page_config(
    page_title="내 주식 주가 비교하기",
    page_icon="📈",
    layout="wide",
)

# ------------------------------------------------------------
# 2. 따뜻한 톤을 위한 간단한 꾸밈(CSS)
#    - 배경은 크림색, 글자는 짙은 갈색, 지표 카드는 연한 노란색
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #FFF6DC; }
    .stApp h1, .stApp h2, .stApp h3,
    .stApp p, .stApp label, .stApp span, .stApp li { color: #4A3B20; }
    h1 { color: #8A5A00 !important; }
    div[data-testid="stMetric"] {
        background-color: #FFE9A8;
        border: 2px solid #F5C842;
        border-radius: 16px;
        padding: 16px 20px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 3. 기간 선택에 쓰는 값
#    - 왼쪽: 화면에 보이는 이름 / 오른쪽: yfinance에 전달하는 기간 값
# ------------------------------------------------------------
PERIODS = {
    "1개월": "1mo",
    "6개월": "6mo",
    "1년": "1y",
    "5년": "5y",
}

# 종목별 그래프 선 색 (첫 번째: 주황, 두 번째: 청록)
LINE_COLORS = ["#E08A00", "#2A7F8E"]

# ------------------------------------------------------------
# 4. 제목과 간단한 설명
# ------------------------------------------------------------
st.title("📈 내 주식 주가 비교하기")
st.write(
    "종목 코드를 입력하면 주가 흐름을 그래프로 보여 드려요. "
    "두 번째 칸까지 입력하면 두 종목을 나란히 비교할 수 있어요. "
    "한국 주식은 코드 뒤에 `.KS`(코스피) 또는 `.KQ`(코스닥)를 붙여 주세요."
)

# ------------------------------------------------------------
# 5. 종목 입력창 2개 (나란히)
#    - 두 번째 칸을 비우면 한 종목만 보여 줘요.
# ------------------------------------------------------------
input_col1, input_col2 = st.columns(2)
with input_col1:
    code1 = st.text_input(
        "종목 1 (필수)",
        value="005930.KS",
        help="예: 005930.KS (삼성전자), AAPL (애플), TSLA (테슬라)",
        key="code1",
    )
with input_col2:
    code2 = st.text_input(
        "종목 2 (비교할 종목, 비워도 돼요)",
        value="AAPL",
        help="비교하지 않으려면 이 칸을 비워 주세요.",
        key="code2",
    )
st.caption("예시: 005930.KS (삼성전자) · AAPL (애플) · TSLA (테슬라)")

# 앞뒤 공백을 지우고 대문자로 바꾼 뒤, 비어 있는 칸은 빼요 (aapl -> AAPL)
codes = [c.strip().upper() for c in (code1, code2) if c.strip()]

# ------------------------------------------------------------
# 6. 기간 선택 버튼 (1개월 · 6개월 · 1년 · 5년)
#    - 최신 스트림릿은 버튼 모양(segmented_control)을 쓰고,
#      없는 버전에서는 가로 라디오 버튼으로 대신해요.
# ------------------------------------------------------------
if hasattr(st, "segmented_control"):
    period_label = st.segmented_control(
        "기간 선택",
        options=list(PERIODS.keys()),
        default="1년",
        key="period",
    )
else:
    period_label = st.radio(
        "기간 선택",
        options=list(PERIODS.keys()),
        index=2,
        horizontal=True,
        key="period",
    )

# 선택한 버튼을 다시 눌러 해제하면 값이 비어 버려요. 그럴 땐 1년으로 되돌려요.
if not period_label:
    period_label = "1년"
period_value = PERIODS[period_label]


# ------------------------------------------------------------
# 7. 주가 데이터를 가져오는 함수
#    - @st.cache_data: 같은 종목·기간은 1시간 동안 다시 요청하지 않고
#      저장해 둔 값을 써요. (요청이 너무 잦으면 야후에서 막을 수 있어요)
#    - 오류가 나거나 데이터가 비면 예외를 던져서, 그 결과는 저장되지 않게 했어요.
# ------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(ticker_code, period):
    """주가(DataFrame)와 통화 단위(문자열)를 돌려줍니다."""
    ticker = yf.Ticker(ticker_code)
    df = ticker.history(period=period)

    if df is None or df.empty:
        raise ValueError("데이터가 비어 있어요")

    # 통화(KRW, USD 등)는 가져오지 못해도 앱이 멈추지 않게 try로 감싸요
    try:
        currency = ticker.fast_info["currency"]
    except Exception:
        currency = ""
    return df, currency


def format_price(value, currency):
    """통화에 맞게 가격을 보기 좋은 문자열로 바꿔요."""
    if currency == "KRW":
        return f"{value:,.0f}원"       # 원화는 소수점 없이
    if currency == "USD":
        return f"${value:,.2f}"        # 달러는 소수점 2자리
    suffix = f" {currency}" if currency else ""
    return f"{value:,.2f}{suffix}"     # 그 외 통화


# ------------------------------------------------------------
# 8. 입력값 확인 → 종목별로 데이터 불러오기
# ------------------------------------------------------------
if not codes:
    st.info("위 입력창에 종목 코드를 한 개 이상 입력해 주세요.")
    st.stop()  # 여기서 아래 코드는 실행하지 않고 멈춰요

results = []  # 불러오기에 성공한 종목들을 여기에 모아요
for code in codes:
    try:
        with st.spinner(f"{code} 주가를 불러오는 중이에요..."):
            data, currency = load_data(code, period_value)
    except ValueError:
        # 데이터가 비어 있으면 코드가 잘못된 경우가 많아요
        st.warning(
            f"'{code}' 종목의 주가를 찾지 못했어요. "
            "코드를 다시 확인해 주세요. (한국 주식은 .KS 또는 .KQ가 필요해요)"
        )
        continue
    except Exception:
        st.error(
            f"'{code}' 주가를 불러오지 못했어요. 잠시 후 다시 시도해 주세요. "
            "(요청이 너무 많으면 일시적으로 막힐 수 있어요.)"
        )
        continue

    # 종가(Close)만 사용해요. 결측치는 지우고, 시간대 정보는 없애서 날짜만 남겨요.
    prices = data["Close"].dropna()
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    if len(prices) < 2:
        st.warning(f"'{code}'은(는) 비교할 만큼 데이터가 충분하지 않아요.")
        continue

    results.append({"code": code, "prices": prices, "currency": currency})

# 하나도 성공하지 못했다면 여기서 멈춰요
if not results:
    st.stop()

# ------------------------------------------------------------
# 9. 위쪽 지표 카드 (종목마다 현재가 · 기간 등락률)
#    - 현재가: 가장 최근 종가
#    - 등락률: (최근 종가 ÷ 기간 첫 종가 - 1) × 100
# ------------------------------------------------------------
st.subheader(f"📌 {period_label} 기준 요약")
top_cols = st.columns(len(results))

for col, item in zip(top_cols, results):
    prices = item["prices"]
    currency = item["currency"]

    current_price = float(prices.iloc[-1])
    first_price = float(prices.iloc[0])
    change_amount = current_price - first_price
    change_rate = (current_price / first_price - 1) * 100

    # 등락 금액 앞에 부호를 붙여요 (스트림릿은 '-'로 시작하면 빨간 아래 화살표로 보여 줘요)
    sign = "-" if change_amount < 0 else ""
    delta_text = sign + format_price(abs(change_amount), currency)

    with col:
        st.markdown(f"**{item['code']}**")
        m1, m2 = st.columns(2)
        with m1:
            st.metric(
                label="현재가 (최근 종가)",
                value=format_price(current_price, currency),
            )
        with m2:
            st.metric(
                label=f"{period_label} 등락률",
                value=f"{change_rate:+.2f}%",
                delta=delta_text,
            )

# ------------------------------------------------------------
# 10. plotly 꺾은선 그래프
#     - 종목이 1개: 종가(가격)를 그대로 그려요.
#     - 종목이 2개: 가격 단위가 달라(원, 달러 등) 한 그래프에 그대로 그리면
#       비교가 어려워요. 그래서 '시작일 대비 등락률(%)'로 바꿔 그려요.
# ------------------------------------------------------------
compare_mode = len(results) >= 2

fig = go.Figure()
for i, item in enumerate(results):
    prices = item["prices"]
    color = LINE_COLORS[i % len(LINE_COLORS)]

    if compare_mode:
        # 첫날 값을 0%로 맞추고, 이후 얼마나 올랐는지/내렸는지를 계산해요
        y_values = (prices / float(prices.iloc[0]) - 1) * 100
        hover = "%{x|%Y-%m-%d}<br>등락률: %{y:+.2f}%<extra>" + item["code"] + "</extra>"
    else:
        y_values = prices
        hover = "%{x|%Y-%m-%d}<br>종가: %{y:,.2f}<extra>" + item["code"] + "</extra>"

    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=y_values.values,
            mode="lines",
            name=item["code"],
            line=dict(color=color, width=3),
            hovertemplate=hover,
        )
    )

if compare_mode:
    chart_title = f"{' vs '.join(r['code'] for r in results)} · {period_label} 등락률 비교"
    y_title = "시작일 대비 등락률 (%)"
    fig.add_hline(y=0, line_dash="dot", line_color="#8F7B4D")  # 0% 기준선
else:
    cur = results[0]["currency"]
    chart_title = f"{results[0]['code']} · 최근 {period_label} 주가"
    y_title = f"종가 ({cur})" if cur else "종가"

fig.update_layout(
    title=chart_title,
    xaxis_title="날짜",
    yaxis_title=y_title,
    template="plotly_white",
    paper_bgcolor="#FFF6DC",   # 그래프 바깥 배경 (크림색)
    plot_bgcolor="#FFFDF5",    # 그래프 안쪽 배경
    font=dict(color="#4A3B20", size=14),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=10, r=10, t=80, b=10),
)

st.plotly_chart(fig, width="stretch")

if compare_mode:
    st.caption(
        "두 종목은 가격 단위가 달라서, 시작일 가격을 0%로 맞춘 등락률로 비교했어요."
    )

# ------------------------------------------------------------
# 11. 그래프 아래 지표 카드 (최고가 · 최저가 · 평균가)
#     - 선택한 기간의 종가를 기준으로 계산해요.
# ------------------------------------------------------------
st.subheader(f"📊 {period_label} 동안의 최고가 · 최저가 · 평균가")
bottom_cols = st.columns(len(results))

for col, item in zip(bottom_cols, results):
    prices = item["prices"]
    currency = item["currency"]

    high_price = float(prices.max())
    low_price = float(prices.min())
    avg_price = float(prices.mean())
    high_date = prices.idxmax().strftime("%Y-%m-%d")  # 최고가를 기록한 날
    low_date = prices.idxmin().strftime("%Y-%m-%d")   # 최저가를 기록한 날

    with col:
        st.markdown(f"**{item['code']}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                label=f"최고가 ({high_date})",
                value=format_price(high_price, currency),
            )
        with c2:
            st.metric(
                label=f"최저가 ({low_date})",
                value=format_price(low_price, currency),
            )
        with c3:
            st.metric(
                label="평균가",
                value=format_price(avg_price, currency),
            )

# ------------------------------------------------------------
# 12. 안내 문구
# ------------------------------------------------------------
st.caption(
    "※ 데이터 출처: Yahoo Finance (yfinance). 최고가·최저가·평균가는 하루 끝 종가 기준이에요. "
    "시세가 지연될 수 있으며, 투자 판단의 참고용일 뿐 투자 조언이 아니에요."
)
