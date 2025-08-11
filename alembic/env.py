"""
Alembic環境設定ファイル

データベースマイグレーションの環境設定
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(str(Path(__file__).parents[1]))

# モデルのインポート(全てのモデルをインポートすることで、Base.metadataに登録される)
from src.data.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """環境変数からデータベースURLを構築"""
    # DATABASE_URLが設定されている場合はそれを使用(CI環境など)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # 環境変数から接続情報を取得
    host = os.getenv("DATABASE_HOST", "mysql")
    port = os.getenv("DATABASE_PORT", "3306")
    user = os.getenv("DATABASE_USER", "keiba_user")
    password = os.getenv("DATABASE_PASSWORD", "keiba_password")
    database = os.getenv("DATABASE_NAME", "keiba_db")

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 設定を上書きしてデータベースURLを設定
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
