"""
FastAPI メインアプリケーション
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# アプリケーション作成
app = FastAPI(
    title="競馬予想AIシステム",
    description="JRA-VAN DataLabのデータを活用した競馬予測システム",
    version="0.1.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境では全て許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "競馬予想AIシステム API"}


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}