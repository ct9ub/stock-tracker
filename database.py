"""SQLite 데이터베이스 관리"""
import sqlite3
import os
from datetime import datetime, date
from config import DB_PATH


def get_connection():
    """DB 연결 반환"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """테이블 생성"""
    conn = get_connection()
    cursor = conn.cursor()

    # 인플루언서 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS influencers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            platform TEXT DEFAULT 'youtube',
            channel_url TEXT,
            memo TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 추천 종목 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            influencer_id INTEGER NOT NULL,
            stock_name TEXT NOT NULL,
            stock_code TEXT,
            recommended_date TEXT NOT NULL,
            recommended_price REAL NOT NULL,
            target_price REAL,
            stop_loss_price REAL,
            memo TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (influencer_id) REFERENCES influencers(id)
        )
    """)

    # 일별 가격 추적 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER NOT NULL,
            tracking_date TEXT NOT NULL,
            close_price REAL NOT NULL,
            change_pct REAL,
            high_price REAL,
            low_price REAL,
            volume INTEGER,
            days_since_rec INTEGER,
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
            UNIQUE(recommendation_id, tracking_date)
        )
    """)

    # 매매 일지 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            stock_code TEXT,
            action TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL,
            fee REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            reason TEXT,
            result_pct REAL,
            memo TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()


# === 인플루언서 CRUD ===

def add_influencer(name, platform="youtube", channel_url="", memo=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO influencers (name, platform, channel_url, memo) VALUES (?, ?, ?, ?)",
            (name, platform, channel_url, memo)
        )
        conn.commit()
        return True, "등록 완료"
    except sqlite3.IntegrityError:
        return False, "이미 등록된 인플루언서입니다"
    finally:
        conn.close()


def get_influencers():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM influencers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_influencer(influencer_id):
    conn = get_connection()
    conn.execute("DELETE FROM price_tracking WHERE recommendation_id IN (SELECT id FROM recommendations WHERE influencer_id = ?)", (influencer_id,))
    conn.execute("DELETE FROM recommendations WHERE influencer_id = ?", (influencer_id,))
    conn.execute("DELETE FROM influencers WHERE id = ?", (influencer_id,))
    conn.commit()
    conn.close()


# === 추천 종목 CRUD ===

def add_recommendation(influencer_id, stock_name, stock_code, recommended_date,
                       recommended_price, target_price=None, stop_loss_price=None, memo=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO recommendations
           (influencer_id, stock_name, stock_code, recommended_date,
            recommended_price, target_price, stop_loss_price, memo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (influencer_id, stock_name, stock_code, recommended_date,
         recommended_price, target_price, stop_loss_price, memo)
    )
    conn.commit()
    conn.close()


def get_recommendations(influencer_id=None, status=None):
    conn = get_connection()
    query = """
        SELECT r.*, i.name as influencer_name
        FROM recommendations r
        JOIN influencers i ON r.influencer_id = i.id
        WHERE 1=1
    """
    params = []
    if influencer_id:
        query += " AND r.influencer_id = ?"
        params.append(influencer_id)
    if status:
        query += " AND r.status = ?"
        params.append(status)
    query += " ORDER BY r.recommended_date DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_recommendation_status(rec_id, status):
    conn = get_connection()
    conn.execute("UPDATE recommendations SET status = ? WHERE id = ?", (status, rec_id))
    conn.commit()
    conn.close()


# === 가격 추적 ===

def save_price_tracking(recommendation_id, tracking_date, close_price,
                        change_pct, high_price, low_price, volume, days_since_rec):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO price_tracking
           (recommendation_id, tracking_date, close_price, change_pct,
            high_price, low_price, volume, days_since_rec)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (recommendation_id, tracking_date, close_price, change_pct,
         high_price, low_price, volume, days_since_rec)
    )
    conn.commit()
    conn.close()


def get_price_tracking(recommendation_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM price_tracking WHERE recommendation_id = ? ORDER BY tracking_date",
        (recommendation_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# === 매매 일지 ===

def add_trade(trade_date, stock_name, stock_code, action, price, quantity,
              reason="", memo=""):
    total_amount = price * quantity
    tax = total_amount * 0.002 if action == "매도" else 0  # 거래세 0.2%
    conn = get_connection()
    conn.execute(
        """INSERT INTO trade_journal
           (trade_date, stock_name, stock_code, action, price, quantity,
            total_amount, fee, tax, reason, memo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (trade_date, stock_name, stock_code, action, price, quantity,
         total_amount, 0, tax, reason, memo)
    )
    conn.commit()
    conn.close()


def get_trades(start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT * FROM trade_journal WHERE 1=1"
    params = []
    if start_date:
        query += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND trade_date <= ?"
        params.append(end_date)
    query += " ORDER BY trade_date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# === 인플루언서 성과 계산 ===

def get_influencer_stats():
    """인플루언서별 성과 통계 계산"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            i.id,
            i.name,
            i.platform,
            COUNT(r.id) as total_recs,
            SUM(CASE WHEN pt.latest_change_pct > 0 THEN 1 ELSE 0 END) as hit_count,
            AVG(pt.latest_change_pct) as avg_return,
            MAX(pt.latest_change_pct) as max_return,
            MIN(pt.latest_change_pct) as min_return
        FROM influencers i
        LEFT JOIN recommendations r ON i.id = r.influencer_id
        LEFT JOIN (
            SELECT recommendation_id, change_pct as latest_change_pct
            FROM price_tracking
            WHERE (recommendation_id, tracking_date) IN (
                SELECT recommendation_id, MAX(tracking_date)
                FROM price_tracking
                GROUP BY recommendation_id
            )
        ) pt ON r.id = pt.recommendation_id
        GROUP BY i.id
        ORDER BY AVG(pt.latest_change_pct) DESC NULLS LAST
    """).fetchall()
    conn.close()

    stats = []
    for r in rows:
        d = dict(r)
        total = d["total_recs"] or 0
        hits = d["hit_count"] or 0
        d["hit_rate"] = (hits / total * 100) if total > 0 else 0
        d["avg_return"] = d["avg_return"] or 0
        d["max_return"] = d["max_return"] or 0
        d["min_return"] = d["min_return"] or 0
        stats.append(d)
    return stats


# 앱 시작 시 DB 초기화
init_db()
