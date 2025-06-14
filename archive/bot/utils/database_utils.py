"""
データベース操作のユーティリティモジュール
エラーハンドリング、トランザクション、パフォーマンス監視を提供
"""
import sqlite3
import logging
import time
import functools
from typing import Any, Dict, List, Optional, Callable, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """データベース操作の基本エラー"""
    pass


class RecordNotFoundError(DatabaseError):
    """レコードが見つからない場合のエラー"""
    pass


class DuplicateRecordError(DatabaseError):
    """重複レコードの場合のエラー"""
    pass


def handle_database_error(func: Callable) -> Callable:
    """データベースエラーを統一的に処理するデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateRecordError(f"重複レコードエラー: {e}")
            else:
                raise DatabaseError(f"整合性エラー: {e}")
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning("データベースがロックされています。リトライします...")
                time.sleep(0.1)
                return func(*args, **kwargs)
            else:
                raise DatabaseError(f"操作エラー: {e}")
        except sqlite3.Error as e:
            raise DatabaseError(f"データベースエラー: {e}")
        except Exception as e:
            logger.error(f"予期しないエラー: {e}", exc_info=True)
            raise DatabaseError(f"予期しないエラー: {e}")
    
    return wrapper


# Alias for backward compatibility  
handle_db_error = handle_database_error


def retry_on_lock(max_retries: int = 3, delay: float = 0.1) -> Callable:
    """データベースロック時のリトライデコレータ"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"データベースロック (試行 {attempt + 1}/{max_retries})")
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise DatabaseError(f"データベースロックエラー: {e}")
            return None
        return wrapper
    return decorator


@contextmanager
def transaction_context(connection: sqlite3.Connection):
    """トランザクション管理のコンテキストマネージャ"""
    try:
        connection.execute("BEGIN")
        cursor = connection.cursor()
        yield cursor
        connection.commit()
        logger.debug("トランザクションがコミットされました")
    except Exception as e:
        connection.rollback()
        logger.error(f"トランザクションがロールバックされました: {e}")
        raise


# Alias for backward compatibility
transaction = transaction_context


def safe_execute(cursor_or_connection, query: str, params: Tuple = ()) -> sqlite3.Cursor:
    """安全なSQL実行"""
    try:
        # cursorまたはconnectionどちらでも対応
        if hasattr(cursor_or_connection, 'execute'):
            result = cursor_or_connection.execute(query, params)
            logger.debug(f"クエリ実行: {query[:50]}...")
            return result
        else:
            raise TypeError("cursor または connection オブジェクトが必要です")
    except sqlite3.Error as e:
        logger.error(f"クエリ実行エラー: {query[:50]}... - {e}")
        raise DatabaseError(f"クエリ実行エラー: {e}")


def fetch_one_as_dict(cursor: sqlite3.Cursor) -> Optional[Dict[str, Any]]:
    """単一行を辞書として取得"""
    row = cursor.fetchone()
    if row is None:
        return None
    
    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def fetch_all_as_dict(cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
    """全行を辞書のリストとして取得"""
    rows = cursor.fetchall()
    if not rows:
        return []
    
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """必須フィールドの検証"""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        raise ValueError(f"必須フィールドが不足しています: {missing_fields}")
    return True


def sanitize_string(value: str, max_length: Optional[int] = None) -> Optional[str]:
    """文字列のサニタイズ"""
    if value is None:
        return None
    
    if not isinstance(value, str):
        value = str(value)
    
    # 基本的なサニタイズ
    value = value.strip()
    
    # 長さ制限
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


def build_update_query(table: str, data: Dict[str, Any], where_clause: str) -> Tuple[str, List]:
    """UPDATE クエリの構築"""
    if not data:
        raise ValueError("更新データが空です")
    
    # updated_atを自動追加
    data_with_timestamp = data.copy()
    data_with_timestamp['updated_at'] = 'CURRENT_TIMESTAMP'
    
    set_clauses = []
    params = []
    
    for key, value in data_with_timestamp.items():
        if key == 'updated_at' and value == 'CURRENT_TIMESTAMP':
            set_clauses.append(f"{key} = CURRENT_TIMESTAMP")
        else:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    
    set_clause = ", ".join(set_clauses)
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    
    return query, params


def log_query_performance(func: Callable) -> Callable:
    """クエリのパフォーマンスをログに記録するデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # 1秒以上の場合は警告
                logger.warning(f"遅いクエリ検出: {func.__name__} - {execution_time:.2f}秒")
            else:
                logger.debug(f"クエリ実行時間: {func.__name__} - {execution_time:.3f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"クエリエラー: {func.__name__} - {execution_time:.3f}秒 - {e}")
            raise
    
    return wrapper