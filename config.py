"""프로젝트 설정"""
import os

# 프로젝트 루트 디렉토리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DB 파일 경로
DB_PATH = os.path.join(BASE_DIR, "data", "stock_tracker.db")

# 추천 종목 모니터링 기간 (영업일 기준)
TRACKING_DAYS = 30

# 수익률 구간 (영업일 기준)
TRACKING_PERIODS = [1, 3, 5, 10, 20, 30]

# 인플루언서 최소 추천 수 (이 이상이어야 신뢰도 점수 의미 있음)
MIN_RECOMMENDATIONS = 5

# 수익 기준 (이 이상이면 "적중"으로 판단)
HIT_THRESHOLD_PCT = 0.0  # 0% 이상이면 적중
