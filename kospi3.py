import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="KOSPI 주도주 스크리너", layout="wide")
st.title("📊 KOSPI 지수 대비 상대적 강세 주도주 스크리너")
st.caption("표준 브라우저 위장 헤더 세션 및 복리 누적 캡처 연산 알고리즘이 적용된 대시보드입니다.")

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
    
    with st.spinner("금융 서버 보안벽을 조율하여 데이터를 안전하게 수집 중입니다..."):
        
        # [수정 완결 패치] requests 세션을 직접 생성하고 헤더를 주입하는 웹 표준 방식
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 코스피 지수 수집 (위에서 만든 위장 세션을 내부 인자로 강제 매칭)
        try:
            kospi_data = yf.download('^KS11', start=start_str, end=end_str, progress=False, session=session)
            
            if kospi_data.empty:
                st.error("서버 응답이 비어있습니다. 날짜 설정을 다시 확인해 주세요.")
                st.stop()
                
            if isinstance(kospi_data.columns, pd.MultiIndex):
                kospi = pd.DataFrame(kospi_data['Close']['^KS11'])
            else:
                kospi = kospi_data[['Close']]
            kospi.columns = ['KOSPI']
        except Exception as e:
            st.error(f"지수 수집 실패: {e}")
            st.stop()
            
        # 상장 목록 확보
        try:
            kospi_list = fdr.StockListing('KOSPI').head(100) # 시총 상위 100개 대형주 중심
        except:
            st.error("거래소 종목 정보를 읽어오지 못했습니다.")
            st.stop()
            
        master_df = kospi.copy()
        stock_names = {}
        
        # 개별 종목 주가 축적
        progress_bar = st.progress(0)
        for idx, row in kospi_list.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                # 개별 종목 수집 시에도 동일한 브라우저 세션을 연동하여 다이렉트 통과
                stock_data = yf.download(f"{code}.KS", start=start_str, end=end_str, progress=False, session=session)
                if not stock_data.empty:
                    if isinstance(stock_data.columns, pd.MultiIndex):
                        df_stock = pd.DataFrame(stock_data['Close'][f"{code}.KS"])
                    else:
                        df_stock = stock_data[['Close']]
                    df_stock.columns = [code]
                    master_df = master_df.join(df_stock, how='left')
                    stock_names[code] = name
            except:
                continue
            progress_bar.progress((idx + 1) / len(kospi_list))
            
        # 인덱스 데이트 정산 및 결측치 보정
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
