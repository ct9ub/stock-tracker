"""추천 종목 주가 자동 수집 (PyKRX 이용)"""
from datetime import datetime, timedelta
from pykrx import stock as pykrx_stock
import time

from database import get_recommendations, save_price_tracking, update_recommendation_status
from config import TRACKING_DAYS


def get_stock_code_by_name(stock_name):
    """종목명으로 종목코드 검색"""
    today = datetime.now().strftime("%Y%m%d")
    tickers = pykrx_stock.get_market_ticker_list(today, market="ALL")
    for ticker in tickers:
        name = pykrx_stock.get_market_ticker_name(ticker)
        if name == stock_name:
            return ticker
    return None


def update_prices():
    """활성 추천 종목의 주가를 업데이트"""
    recs = get_recommendations(status="active")
    if not recs:
        return 0, "업데이트할 활성 추천 종목이 없습니다"

    updated = 0
    errors = []

    for rec in recs:
        try:
            code = rec["stock_code"]
            if not code:
                code = get_stock_code_by_name(rec["stock_name"])
                if not code:
                    errors.append(f"{rec['stock_name']}: 종목코드를 찾을 수 없습니다")
                    continue

            rec_date = rec["recommended_date"].replace("-", "")
            today = datetime.now().strftime("%Y%m%d")

            # 추천일부터 오늘까지의 주가 조회
            df = pykrx_stock.get_market_ohlcv(rec_date, today, code)

            if df.empty:
                errors.append(f"{rec['stock_name']}: 주가 데이터 없음")
                continue

            rec_price = rec["recommended_price"]

            for idx, row in df.iterrows():
                tracking_date = idx.strftime("%Y-%m-%d")
                close_price = float(row["종가"])
                high_price = float(row["고가"])
                low_price = float(row["저가"])
                volume = int(row["거래량"])
                change_pct = ((close_price - rec_price) / rec_price) * 100

                # 추천일로부터 경과 영업일 계산
                days_since = len(df.loc[:idx])

                save_price_tracking(
                    recommendation_id=rec["id"],
                    tracking_date=tracking_date,
                    close_price=close_price,
                    change_pct=round(change_pct, 2),
                    high_price=high_price,
                    low_price=low_price,
                    volume=volume,
                    days_since_rec=days_since
                )

                # 모니터링 기간 초과 시 자동 종료
                if days_since >= TRACKING_DAYS:
                    update_recommendation_status(rec["id"], "completed")

            updated += 1
            time.sleep(1)  # API 부하 방지

        except Exception as e:
            errors.append(f"{rec['stock_name']}: {str(e)}")

    msg = f"{updated}개 종목 업데이트 완료"
    if errors:
        msg += f"\n오류 {len(errors)}건:\n" + "\n".join(errors)
    return updated, msg


def search_stock(keyword):
    """종목명 검색 (자동완성용)"""
    today = datetime.now().strftime("%Y%m%d")
    results = []
    tickers = pykrx_stock.get_market_ticker_list(today, market="ALL")
    for ticker in tickers:
        name = pykrx_stock.get_market_ticker_name(ticker)
        if keyword in name:
            results.append({"code": ticker, "name": name})
        if len(results) >= 20:
            break
    return results


def get_current_price(stock_code):
    """종목의 현재(최근) 종가 조회"""
    today = datetime.now().strftime("%Y%m%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    df = pykrx_stock.get_market_ohlcv(week_ago, today, stock_code)
    if df.empty:
        return None
    return float(df.iloc[-1]["종가"])
