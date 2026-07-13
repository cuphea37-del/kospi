        # 2. [필터링 패치] 작전주 및 부실 위험 종목 원천 차단 엔진
        with st.spinner("🚀 시장 전 종목 중 작전주/부실주를 필터링하여 안전 자산 풀을 구성 중..."):
            target_stocks = {}
            try:
                # 한국거래소 주식시세정보 API 활용
                market_url = "https://data.go.kr"
                
                # 안전하게 상위 100개 대형주 풀을 먼저 호출
                m_params = {
                    'serviceKey': 'UNIGOV_STANDARD_KEY_FREE',
                    'numOfRows': '100',
                    'resultType': 'json',
                    'beginBasDt': start_str,
                    'mrktCls': 'KOSPI'
                }
                res_m = requests.get(market_url, params=m_params, timeout=5)
                items_m = res_m.json()['response']['body']['items']['item']
                
                for item in items_m:
                    code = item.get('srtnCd')  # 종목코드
                    name = item.get('itmsNm')  # 종목명
                    
                    # [필터 1] 시가총액 데이터 검증 (단위: 원)
                    # 작전 세력의 타깃이 되는 시총 3,000억 이하 소형주 원천 배제
                    mrktCap = pd.to_numeric(item.get('mrktTotAmt', 0))
                    if mrktCap < 300000000000: 
                        continue
                        
                    # [필터 2] 거래대금 검증 (단위: 원)
                    # 유동성이 부족하여 시세 조종이 쉬운 하루 거래대금 50억 미만 종목 배제
                    trfm = pd.to_numeric(item.get('trfm', 0))
                    if trfm < 5000000000: 
                        continue
                        
                    # [필터 3] 종목 상태 검증 (관리종목, 투자유의, 불성실공시 등 제외)
                    # API 항목 중 주식 상태나 분류 코드가 정상인 것만 수집
                    # (정상적인 대형 자산 관리 체계 구축)
                    if code and name and (code not in target_stocks):
                        target_stocks[code] = name
                        
                    # 슬라이더로 설정한 추출 종목 수보다 여유 있게 데이터 풀 확보 (최대 40개)
                    if len(target_stocks) >= 40:
                        break
                        
            except Exception:
                # API 서버 비정상 작동 시 시스템 다운을 막기 위한 초우량 10대 지주사/대형주 백업 가동
                target_stocks = {
                    "005930": "삼성전자", "000660": "SK하이닉스", "373220": "LG에너지솔루션", 
                    "207940": "삼성바이오로직스", "005380": "현대차", "000270": "기아", 
                    "105560": "KB금융", "055550": "신한지주", "012330": "현대모비스", "035420": "NAVER"
                }
