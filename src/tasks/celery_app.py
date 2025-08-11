"""
Celery アプリケーション設定
"""

import os

from celery import Celery

# Redis URL取得
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celeryアプリケーション作成
app = Celery(
    "keiba_ai",
    broker=redis_url,
    backend=redis_url,
    include=["src.tasks.data_tasks", "src.tasks.ml_tasks"],
)

# 設定
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分
    task_soft_time_limit=25 * 60,  # 25分
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


# タスク例
@app.task
def test_task():
    """テストタスク"""
    return {"status": "success", "message": "Celery is working!"}
