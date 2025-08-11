"""
WebSocketエンドポイント
"""

import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.api.auth.jwt_handler import jwt_handler
from src.api.schemas.common import WebSocketMessage
from src.api.websocket.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="認証トークン"),
    client_id: Optional[str] = Query(None, description="クライアントID"),
):
    """
    WebSocketエンドポイント

    接続例:
    - 認証あり: ws://localhost:8000/ws?token=YOUR_JWT_TOKEN
    - 認証なし: ws://localhost:8000/ws?client_id=YOUR_CLIENT_ID

    メッセージ形式:
    ```json
    {
        "type": "subscribe",
        "data": {
            "channel": "predictions"
        }
    }
    ```

    利用可能なメッセージタイプ:
    - subscribe: チャンネル購読
    - unsubscribe: 購読解除
    - message: メッセージ送信
    - pong: ハートビート応答
    """

    # クライアントIDの生成または検証
    if not client_id:
        client_id = f"ws_{uuid.uuid4().hex[:8]}"

    # ユーザー認証（オプション）
    user_id = None
    if token:
        token_data = jwt_handler.decode_token(token)
        if token_data:
            user_id = str(token_data.user_id)

    # 接続を確立
    connected = await manager.connect(websocket, client_id, user_id)

    if not connected:
        return

    try:
        # メッセージ受信ループ
        while True:
            # テキストメッセージを待機
            data = await websocket.receive_text()

            try:
                # JSONパース
                message = json.loads(data)

                # メッセージ処理
                await manager.handle_message(client_id, message)

            except json.JSONDecodeError:
                # JSON解析エラー
                await manager.send_personal_message(
                    WebSocketMessage(
                        type="error",
                        data={
                            "message": "Invalid JSON format",
                            "received": data[:100],  # 最初の100文字のみ
                        },
                    ),
                    client_id,
                )
            except Exception as e:
                logger.exception(f"Message processing error: {e}")
                await manager.send_personal_message(
                    WebSocketMessage(
                        type="error", data={"message": "Internal server error"}
                    ),
                    client_id,
                )

    except WebSocketDisconnect:
        # クライアントが切断
        await manager.disconnect(client_id)
        logger.info(f"WebSocket disconnected: {client_id}")

    except Exception as e:
        # その他のエラー
        logger.exception(f"WebSocket error: {e}")
        await manager.disconnect(client_id)


@router.websocket("/ws/predictions/{race_id}")
async def prediction_updates(
    websocket: WebSocket, race_id: str, token: Optional[str] = Query(None)
):
    """
    レース予測更新用WebSocket

    特定のレースの予測更新をリアルタイムで配信します。
    """
    client_id = f"pred_{race_id}_{uuid.uuid4().hex[:8]}"

    # ユーザー認証
    user_id = None
    if token:
        token_data = jwt_handler.decode_token(token)
        if token_data:
            user_id = str(token_data.user_id)

    # 接続確立
    connected = await manager.connect(websocket, client_id, user_id)

    if not connected:
        return

    # 予測チャンネルに自動購読
    channel = f"predictions_{race_id}"
    await manager.subscribe(client_id, channel)

    try:
        # 初期データ送信（モック）
        await manager.send_personal_message(
            WebSocketMessage(
                type="prediction_status",
                data={
                    "race_id": race_id,
                    "status": "waiting",
                    "message": f"レース {race_id} の予測更新を待機中",
                },
            ),
            client_id,
        )

        # メッセージ受信ループ
        while True:
            data = await websocket.receive_text()

            # Pong以外のメッセージは無視（このエンドポイントは受信専用）
            message = json.loads(data)
            if message.get("type") == "pong":
                await manager.handle_message(client_id, message)

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.exception(f"Prediction WebSocket error: {e}")
        await manager.disconnect(client_id)
