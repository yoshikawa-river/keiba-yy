"""
データベース接続管理

SQLAlchemyを使用したデータベース接続の管理と
セッション管理を提供する
"""
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from src.core.config import settings


class DatabaseManager:
    """データベース接続マネージャー"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        pool_pre_ping: Optional[bool] = None,
        echo: Optional[bool] = None,
    ):
        """
        データベース接続マネージャーの初期化

        Args:
            database_url: データベース接続URL
            pool_size: コネクションプールサイズ
            max_overflow: 最大オーバーフロー数
            pool_pre_ping: 接続前のping確認
            echo: SQLログ出力
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.pool_size = pool_size or settings.DATABASE_POOL_SIZE
        self.max_overflow = max_overflow or settings.DATABASE_MAX_OVERFLOW
        self.pool_pre_ping = pool_pre_ping or settings.DATABASE_POOL_PRE_PING
        self.echo = echo if echo is not None else settings.DEBUG

        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """SQLAlchemyエンジンを取得"""
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=self.pool_pre_ping,
                echo=self.echo,
                # MySQL固有の設定
                connect_args={
                    "charset": "utf8mb4",
                },
            )
            # イベントリスナーの設定
            self._setup_event_listeners()

        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """セッションファクトリーを取得"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def get_session(self) -> Session:
        """新しいセッションを取得"""
        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        セッションのコンテキストマネージャー

        使用例:
            with db.session_scope() as session:
                user = session.query(User).first()

        Yields:
            Session: データベースセッション
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """エンジンとコネクションプールを閉じる"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def _setup_event_listeners(self) -> None:
        """イベントリスナーの設定"""
        # コネクションプールのイベント
        @event.listens_for(Pool, "connect")
        def set_mysql_charset(dbapi_conn, connection_record):
            """MySQL接続時の文字コード設定"""
            cursor = dbapi_conn.cursor()
            cursor.execute("SET NAMES utf8mb4")
            cursor.close()

        # エンジンのイベント
        @event.listens_for(self.engine, "before_execute")
        def receive_before_execute(conn, clauseelement, multiparams, params):
            """SQL実行前のログ（開発環境のみ）"""
            if settings.is_development and settings.LOG_LEVEL == "DEBUG":
                print(f"[SQL] {clauseelement}")

    def create_tables(self) -> None:
        """
        全テーブルを作成

        注意: 本番環境ではAlembicを使用すること
        """
        from src.data.models import Base

        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """
        全テーブルを削除

        警告: このメソッドは全データを削除します
        """
        from src.data.models import Base

        Base.metadata.drop_all(bind=self.engine)

    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.close()


# グローバルデータベースマネージャーインスタンス
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI依存性注入用のデータベースセッション取得関数

    使用例:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Session: データベースセッション
    """
    with db_manager.session_scope() as session:
        yield session


# セッションのショートカット
Session = db_manager.session_factory
session_scope = db_manager.session_scope