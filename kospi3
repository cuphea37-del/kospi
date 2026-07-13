import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 스트림릿 메인 웹 레이아웃 기본 구성
st.set_page_config(page_title="KOSPI 주도주 스크리너", layout="wide")
st.title("📊 KOSPI 지수 대비 상대적 강세 주도주 스크리너")
st.caption("오늘 기준 18개월 데이터 자동 매칭 및 표준 연동 API가 적용된 클린 버전 대시보드입니다.")

# 오늘 날짜 기준 정밀 1년 반(18개월) 전 날짜 기본값 세팅
today = datetime.today()
default_start = today - relativedelta(months=18)

# 1. 사용자 입력 인터페이스 구성 (사이드바)
st.sidebar.header("🔍 분석 조건 설정")
start_date = st.sidebar.date_input("조회 시작일", default_start)
end_date = st.sidebar.date_input("조회 종료일", today)
top_n = st.sidebar.slider("추출 종목 수", 5, 30, 15)

if st.sidebar.button("🚀 스크리닝 시작", type="primary"):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    with st.spinner("서버에서 시장 데이터를 정상 수집 중입니다..."):
        
        # [표준화 변경 1] 보안 무력화 세션 제거 후 표준 암호화 통신(HTTPS) 다이렉트 호출
        try:
            kospi_data = yf.download('^KS11', start=start_str, end=end_str, progress=False)
            
            # yfinance 최신 다중인덱스 규격 대응 단일 인덱스 변환
            if isinstance(kospi_data.columns, pd.MultiIndex):
                kospi = pd.DataFrame(kospi_data['Close']['^KS11'])
            else:
                kospi = kospi_data[['Close']]
            kospi.columns = ['KOSPI']
        except Exception as e:
            st.error(f"지수 수집 실패 (네트워크 연결 혹은 날짜 오류): {e}")
            st.stop()
            
        # 한국거래소 공식 정보망 연동 상장 목록 확보
        try:
            kospi_list = fdr.StockListing('KOSPI').head(100) # 시가총액 상위 대형주 풀
        except:
            st.error("거래소 종목 정보를 읽어오지 못했습니다.")
            st.stop()
            
        master_df = kospi.copy()
        stock_names = {}
        
        # [표준화 변경 2] 의도적 트래픽 변장용 지연 딜레이(time.sleep) 완전 제거하여 고속 수집
        progress_bar = st.progress(0)
        for idx, row in kospi_list.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                stock_data = yf.download(f"{code}.KS", start=start_str, end=end_str, progress=False)
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
            
        # 데이터프레임 결측치 보정 및 수익률 변환
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
            
            # 마켓 국면별 복리 다운사이드 캡처 지표 연산
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
            
            # 2. 결과 출력 레이아웃 구성
            st.success(f"분석 완료! 해당 기간 코스피 수익률은 **{round(bench_cum*100, 1)}%** 입니다.")
            
            st.subheader(f"🏆 초과 수익률 상위 {top_n} 주도주 리스트 ({start_date} ~ {end_date})")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            # 다운로드 인터페이스 생성
            csv = df_res.to_csv(index=False).encode('euc-kr')
            st.download_button(label="📥 분석 결과 엑셀(CSV) 다운로드", data=csv, file_name="주도주_스크리닝_결과.csv", mime="text/csv")
        else:
            st.warning("설정하신 기간 동안 지수 성과를 상회한 주도주가 존재하지 않습니다.")
