"""주가 자동 업데이트 스케줄러 (1시간 간격, 장 시간에만 동작)"""
import threading
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from price_updater import update_prices
from database import get_recommendations

logger = logging.getLogger(__name__)

_scheduler = None
_last_result = {"time": None, "message": "", "updated": 0}


def _job_update_prices():
    """스케줄러가 실행하는 주가 업데이트 작업"""
    now = datetime.now()

    # 주말 제외 (토=5, 일=6)
    if now.weekday() >= 5:
        _last_result["time"] = now
        _last_result["message"] = "주말 - 업데이트 건너뜀"
        _last_result["updated"] = 0
        return

    # 장 시간 외 제외 (09:00 ~ 18:00만 실행)
    if now.hour < 9 or now.hour >= 18:
        _last_result["time"] = now
        _last_result["message"] = "장외 시간 - 업데이트 건너뜀"
        _last_result["updated"] = 0
        return

    active = get_recommendations(status="active")
    if not active:
        _last_result["time"] = now
        _last_result["message"] = "추적중인 종목 없음"
        _last_result["updated"] = 0
        return

    try:
        updated, msg = update_prices()
        _last_result["time"] = now
        _last_result["message"] = msg
        _last_result["updated"] = updated
        logger.info(f"[스케줄러] {msg}")
    except Exception as e:
        _last_result["time"] = now
        _last_result["message"] = f"오류: {str(e)}"
        _last_result["updated"] = 0
        logger.error(f"[스케줄러] 오류: {e}")


def start_scheduler():
    """스케줄러 시작 (1시간 간격)"""
    global _scheduler
    if _scheduler and _scheduler.running:
        return  # 이미 실행 중

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _job_update_prices,
        trigger="interval",
        hours=1,
        id="price_update",
        next_run_time=None  # 즉시 실행하지 않음 (첫 실행은 1시간 후)
    )
    _scheduler.start()
    logger.info("[스케줄러] 시작됨 (1시간 간격)")


def stop_scheduler():
    """스케줄러 중지"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def is_running():
    """스케줄러 실행 상태"""
    return _scheduler is not None and _scheduler.running


def get_last_result():
    """마지막 업데이트 결과"""
    return _last_result.copy()


def get_next_run():
    """다음 실행 예정 시간"""
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("price_update")
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    return None
