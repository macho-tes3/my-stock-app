# -*- coding: utf-8 -*-
"""
주식 1년 주가 보기 (Streamlit 앱)
- 종목 코드를 입력하면 yfinance로 최근 1년 주가를 가져와
  plotly 꺾은선 그래프와 지표 카드(현재가, 1년 등락률)로 보여줍니다.
"""

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go


# ------------------------------------------------------------
# 1. 페이지 기본 설정 (반드시 다른 streamlit 명령보다 먼저 나와야 해요)
# ------------------------------------------------------------
st.set_page_config(
    page_title="내 주식 1년 주가 보기",
    page_icon="📈",
    layout="centered",
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
    div[data-testid="stMetricValue"] { font-size: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 3. 제목과 간단한 설명
# ------------------------------------------------------------
st.title("📈 내 주식 1년 주가 보기")
st.write(
    "종목 코드를 입력하면 최근 1년 동안의 주가 흐름을 그래프로 보여 드려요. "
    "한국 주식은 코드 뒤에 `.KS`(코스피) 또는 `.KQ`(코스닥)를 붙여 주세요."
)

# ------------------------------------------------------------
# 4. 종목 입력창
# ------------------------------------------------------------
code = st.text_input(
    "종목 코드를 입력하세요",
    value="005930.KS",
    help="예: 005930.KS (삼성전자), AAPL (애플), TSLA (테슬라)",
)
# 앞뒤 공백을 지우고 대문자로 바꿔요 (aapl -> AAPL)
code = code.strip().upper()
st.caption("예시: 005930.KS (삼성전자) · AAPL (애플) · TSLA (테슬라)")


# ------------------------------------------------------------
# 5. 주가 데이터를 가져오는 함수
#    - @st.cache_data: 같은 종목을 1시간 동안 다시 요청하지 않고 저장해 둔 값을 써요.
#      (요청이 너무 잦으면 야후 쪽에서 막을 수 있어서 꼭 필요해요)
# ------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(ticker_code):
    """최근 1년 주가(DataFrame)와 통화 단위(문자열)를 돌려줍니다."""
    ticker = yf.Ticker(ticker_code)
    df = ticker.history(period="1y")  # 최근 1년치 일별 주가

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
# 6. 입력값 확인 → 데이터 불러오기 → 화면 그리기
# ------------------------------------------------------------
if not code:
    st.info("위 입력창에 종목 코드를 입력해 주세요.")
    st.stop()  # 여기서 아래 코드는 실행하지 않고 멈춰요

try:
    with st.spinner("주가를 불러오는 중이에요..."):
        data, currency = load_data(code)
except Exception:
    st.error(
        "주가를 불러오지 못했어요. 인터넷 연결이나 잠시 후 다시 시도해 주세요. "
        "(요청이 너무 많으면 일시적으로 막힐 수 있어요.)"
    )
    st.stop()

# 데이터가 비어 있으면 코드가 잘못된 경우가 많아요
if data is None or data.empty:
    st.warning(
        f"'{code}' 종목의 주가를 찾지 못했어요. "
        "코드를 다시 확인해 주세요. (한국 주식은 .KS 또는 .KQ가 필요해요)"
    )
    st.stop()

# 종가(Close)만 사용해요. 결측치는 지우고, 시간대 정보는 없애서 날짜만 남겨요.
prices = data["Close"].dropna()
if prices.index.tz is not None:
    prices.index = prices.index.tz_localize(None)

if len(prices) < 2:
    st.warning("비교할 만큼 데이터가 충분하지 않아요. 다른 종목을 입력해 보세요.")
    st.stop()

# ------------------------------------------------------------
# 7. 지표 계산
#    - 현재가: 가장 최근 종가
#    - 1년 등락률: (최근 종가 ÷ 1년 전 첫 종가 - 1) × 100
# ------------------------------------------------------------
current_price = float(prices.iloc[-1])
first_price = float(prices.iloc[0])
change_amount = current_price - first_price
change_rate = (current_price / first_price - 1) * 100

# ------------------------------------------------------------
# 8. 지표 카드 2개 (현재가, 1년 등락률)
# ------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.metric(
        label="현재가 (최근 종가)",
        value=format_price(current_price, currency),
    )
with col2:
    st.metric(
        label="1년 등락률",
        value=f"{change_rate:+.2f}%",
        # 위/아래 화살표와 색은 화면에서 자동으로 표시돼요
        delta=format_price(abs(change_amount), currency)
        if change_amount >= 0
        else "-" + format_price(abs(change_amount), currency),
    )

# ------------------------------------------------------------
# 9. plotly 꺾은선 그래프
# ------------------------------------------------------------
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=prices.index,
        y=prices.values,
        mode="lines",
        name="종가",
        line=dict(color="#E08A00", width=3),   # 따뜻한 주황색 선
        hovertemplate="%{x|%Y-%m-%d}<br>종가: %{y:,.2f}<extra></extra>",
    )
)
fig.update_layout(
    title=f"{code} 최근 1년 주가",
    xaxis_title="날짜",
    yaxis_title=f"종가 ({currency})" if currency else "종가",
    template="plotly_white",
    paper_bgcolor="#FFF6DC",   # 그래프 바깥 배경 (크림색)
    plot_bgcolor="#FFFDF5",    # 그래프 안쪽 배경
    font=dict(color="#4A3B20", size=14),
    hovermode="x unified",
    margin=dict(l=10, r=10, t=60, b=10),
)

st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------
# 10. 안내 문구
# ------------------------------------------------------------
st.caption(
    "※ 데이터 출처: Yahoo Finance (yfinance). 시세가 지연될 수 있으며, "
    "투자 판단의 참고용일 뿐 투자 조언이 아니에요."
)
