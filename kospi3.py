import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="KOSPI 주도주 스크리너", layout="wide")
st.title("📊 KOSPI 지수 대비 상대적 강세 주도주 스크리너")
st.caption("봇 차단 회피 헤더 및 복리 누적 캡처 연산 알고리즘이 적용된 대시보드입니다.")

# 오늘 기준 18개월 전 자동 계산
today = datetime.today()
default_start = today - relativedelta(months=18)

st.sidebar.header("🔍 분석 조건 설정")
start_date = st.sidebar.date_input("조회 시작일", default_start)
end_date = st.sidebar.date_input("조회 종료일", today)
top_n = st.sidebar.slider("추출 종목 수", 5, 30, 15)

if st.sidebar.button("🚀 스크리닝 시작", type="primary"):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    with st.spinner("야후 금융 서버 보안벽을 우회하여 데이터를 수집 중입니다..."):
        
        # [봇 차단 해결 패치] 실제 사람이 브라우저로 접근하는 것처럼 헤더 위장 주입
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        yf.set_proxy_headers(headers)
        
        # 코스피 지수 수집
        try:
            # yfinance 내부 세션에 헤더 자동 녹아들도록 처리
            ticker = yf.Ticker('^KS11')
            kospi_data = ticker.history(start=start_str, end=end_str, progress=False)
            
            if kospi_data.empty:
                st.error("야후 서버 응답이 비어있습니다. 잠시 후 다시 시도해 주세요.")
                st.stop()
                
            kospi = kospi_data[['Close']].copy()
            kospi.columns = ['KOSPI']
        except Exception as e:
            st.error(f"지수 수집 실패 (야후 보안 장벽 발생): {e}")
            st.stop()
            
        # 상장 목록 확보
        try:
            kospi_list = fdr.StockListing('KOSPI').head(100) # 시총 상위 100개
        except:
            st.error("거래소 종목 정보를 읽어오지 못했습니다.")
            st.stop()
            
        master_df = kospi.copy()
        stock_names = {}
        
        progress_bar = st.progress(0)
        for idx, row in kospi_list.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                # 개별 종목 주가도 동일하게 브라우저 위장 세션 수집
                s_ticker = yf.Ticker(f"{code}.KS")
                stock_data = s_ticker.history(start=start_str, end=end_str, progress=False)
                if not stock_data.empty:
                    df_stock = stock_data[['Close']].copy()
                    df_stock.columns = [code]
                    master_df = master_df.join(df_stock, how='left')
                    stock_names[code] = name
            except:
                continue
            progress_bar.progress((idx + 1) / len(kospi_list))
            
        # 인덱스 제거 및 결측치 보정
        master_df.index = master_df.index.date
        master_df = master_df.ffill()
        returns_df = master_df.pct_change().dropna()
        
        bench_ret = returns_df['KOSPI']
        bench_cum = (1 + bench_ret).prod() - 1
        
        results = []
        for code in returns_df.columns:
            if code == 'KOSPI': continue
            stock_ret = returns_df[code]
            if stock_ret.isnull().sum() > (len(returns_df) * 0.2): continue
            
            stock_cum = (1 + stock_ret).prod() - 1
            alpha = stock_cum - bench_cum
            win_rate = (np.sum(stock_ret > bench_ret) / len(bench_ret)) * 100
            
            down_mask = bench_ret < 0
            if down_mask.sum() > 0:
                downside_capture = (((1 + stock_ret[down_mask]).prod() - 1) / ((1 + bench_ret[down_mask]).prod() - 1)) * 100
            else:
                downside_capture = np.nan
                
            if alpha > 0:
                results.append({
                    '종목코드': code,
                    '종목명': stock_names.get(code, code),
                    '종목수익률(%)': round(float(stock_cum * 100), 1),
                    '초과수익률(%p)': round(float(alpha * 100), 1),
                    '지수이긴확률(%)': round(float(win_rate), 1),
                    '하락장방어력(%)': round(float(downside_capture), 1) if not np.isnan(downside_capture) else 0
                })
                
        if results:
            df_res = pd.DataFrame(results).sort_values(by='초과수익률(%p)', ascending=False).head(top_n)
            st.success(f"분석 완료! 해당 기간 코스피 수익률은 **{round(bench_cum*100, 1)}%** 입니다.")
            st.subheader(f"🏆 초과 수익률 상위 {top_n} 주도주 리스트")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            csv = df_res.to_csv(index=False).encode('euc-kr')
            st.download_button(label="📥 분석 결과 엑셀(CSV) 다운로드", data=csv, file_name="주도주_스크리닝_결과.csv", mime="text/csv")
        else:
            st.warning("설정하신 기간 동안 지수 성과를 상회한 주도주가 존재하지 않습니다.")
