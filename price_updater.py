"""추천 종목 주가 자동 수집 (네이버 금융 크롤링)"""
import os
import json
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from database import get_recommendations, save_price_tracking, update_recommendation_status
from config import TRACKING_DAYS, BASE_DIR

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
STOCK_LIST_PATH = os.path.join(BASE_DIR, "data", "stock_list.json")


# ============================================================
# 종목 리스트 관리 (네이버 금융에서 전 종목 수집 → 로컬 캐시)
# ============================================================

def _fetch_market_stocks(market_code):
    """네이버 금융 시가총액 페이지에서 종목 리스트 수집 (0=코스피, 1=코스닥)"""
    stocks = []
    page = 1
    while True:
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={market_code}&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("table.type_2 tbody tr")
        found = 0
        for row in rows:
            a = row.select_one("a.tltle")
            if not a:
                continue
            name = a.text.strip()
            match = re.search(r"code=(\d+)", a["href"])
            if match:
                stocks.append({"code": match.group(1), "name": name})
                found += 1

        if found == 0:
            break

        # 마지막 페이지 확인
        pgrr = soup.select_one("td.pgRR a")
        if pgrr:
            last_match = re.search(r"page=(\d+)", pgrr["href"])
            last_page = int(last_match.group(1)) if last_match else page
        else:
            last_page = page

        if page >= last_page:
            break
        page += 1
        time.sleep(0.3)

    return stocks


def refresh_stock_list():
    """코스피 + 코스닥 전 종목 리스트를 네이버에서 수집하여 로컬 저장"""
    os.makedirs(os.path.dirname(STOCK_LIST_PATH), exist_ok=True)
    all_stocks = []
    all_stocks.extend(_fetch_market_stocks(0))  # 코스피
    all_stocks.extend(_fetch_market_stocks(1))  # 코스닥

    data = {
        "updated_at": datetime.now().isoformat(),
        "count": len(all_stocks),
        "stocks": all_stocks
    }
    with open(STOCK_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return len(all_stocks)


def _load_stock_list():
    """로컬 종목 리스트 로드. 없거나 1일 이상 오래되면 새로 수집."""
    if os.path.exists(STOCK_LIST_PATH):
        with open(STOCK_LIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = datetime.fromisoformat(data["updated_at"])
        if (datetime.now() - updated).days < 1:
            return data["stocks"]

    # 캐시 없거나 오래됨 → 새로 수집
    refresh_stock_list()
    with open(STOCK_LIST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["stocks"]


# ============================================================
# 종목 검색 / 코드 조회
# ============================================================

def get_stock_code_by_name(stock_name):
    """종목명으로 종목코드 검색 (정확히 일치)"""
    stocks = _load_stock_list()
    for s in stocks:
        if s["name"] == stock_name:
            return s["code"]
    return None


def search_stock(keyword):
    """종목명 부분 검색"""
    stocks = _load_stock_list()
    results = [s for s in stocks if keyword in s["name"]]
    return results[:20]


# ============================================================
# 현재가 / 일별 시세 조회 (네이버 금융 크롤링)
# ============================================================

def get_current_price(stock_code):
    """네이버 금융에서 현재가(종가) 조회"""
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    price_tag = soup.select_one("p.no_today .blind")
    if price_tag:
        price_text = price_tag.text.strip().replace(",", "")
        return int(price_text)
    return None


def _get_daily_prices(stock_code, pages=3):
    """네이버 금융 일별 시세 페이지에서 과거 데이터 수집"""
    all_data = []
    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/item/sise_day.naver?code={stock_code}&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("table.type2 tr")
        for row in rows:
            cols = row.select("td span.tah")
            if len(cols) < 6:
                continue
            date_tag = row.select_one("td span.tah")
            if not date_tag:
                continue

            date_text = cols[0].text.strip()
            if not re.match(r"\d{4}\.\d{2}\.\d{2}", date_text):
                continue

            try:
                close = int(cols[1].text.strip().replace(",", ""))
                high = int(cols[3].text.strip().replace(",", ""))
                low = int(cols[4].text.strip().replace(",", ""))
                volume = int(cols[5].text.strip().replace(",", ""))
                trade_date = date_text.replace(".", "-")

                all_data.append({
                    "date": trade_date,
                    "close": close,
                    "high": high,
                    "low": low,
                    "volume": volume
                })
            except (ValueError, IndexError):
                continue

        time.sleep(0.3)

    # 날짜순 정렬 (오래된 순)
    all_data.sort(key=lambda x: x["date"])
    return all_data


# ============================================================
# 가격 업데이트
# ============================================================

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

            rec_date = rec["recommended_date"]  # "2026-04-29" 형식
            rec_price = rec["recommended_price"]

            # 네이버 일별 시세 (최근 약 60영업일)
            daily = _get_daily_prices(code, pages=5)

            if not daily:
                errors.append(f"{rec['stock_name']}: 주가 데이터 없음")
                continue

            # 추천일 이후 데이터만 필터
            daily_after = [d for d in daily if d["date"] >= rec_date]

            for i, day in enumerate(daily_after):
                change_pct = ((day["close"] - rec_price) / rec_price) * 100
                days_since = i + 1

                save_price_tracking(
                    recommendation_id=rec["id"],
                    tracking_date=day["date"],
                    close_price=day["close"],
                    change_pct=round(change_pct, 2),
                    high_price=day["high"],
                    low_price=day["low"],
                    volume=day["volume"],
                    days_since_rec=days_since
                )

                if days_since >= TRACKING_DAYS:
                    update_recommendation_status(rec["id"], "completed")

            updated += 1
            time.sleep(0.5)

        except Exception as e:
            errors.append(f"{rec['stock_name']}: {str(e)}")

    msg = f"{updated}개 종목 업데이트 완료"
    if errors:
        msg += f"\n오류 {len(errors)}건:\n" + "\n".join(errors)
    return updated, msg
