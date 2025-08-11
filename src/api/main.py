"""
FastAPI メインアプリケーション
"""

import time
import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.exceptions.custom_exceptions import KeibaAPIException
from src.api.middleware.error_handler import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.api.middleware.logging_middleware import LoggingMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routers import auth, prediction, websocket
from src.api.websocket.connection_manager import manager

# 起動時間記録
start_time = time.time()

# アプリケーション作成
app = FastAPI(
    title="競馬予想AIシステム",
    description="JRA-VAN DataLabのデータを活用した競馬予測システム",
    version="0.1.0",
)

# ミドルウェア設定
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# エラーハンドラー
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(KeibaAPIException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境では全て許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(prediction.router, prefix="/api/v1", tags=["prediction"])
app.include_router(websocket.router, tags=["websocket"])


@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    """リクエストIDをヘッダーに追加"""
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "競馬予想AIシステム API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    uptime = int(time.time() - start_time)
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": uptime,
        "services": {
            "api": True,
        },
    }


@app.get("/metrics")
async def metrics():
    """メトリクスエンドポイント"""
    uptime = int(time.time() - start_time)
    websocket_stats = manager.get_stats()
    return {
        "uptime_seconds": uptime,
        "websocket_connections": websocket_stats["total_connections"],
        "api_version": "0.1.0",
    }


# デバッグエンドポイント（常に有効）
@app.get("/debug/routes")
async def debug_routes():
    """ルート一覧取得（デバッグ用）"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append(
                {
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": getattr(route, "name", ""),
                }
            )
    return {"routes": routes}


@app.get("/debug/websocket-stats")
async def debug_websocket_stats():
    """WebSocket統計（デバッグ用）"""
    return manager.get_stats()
