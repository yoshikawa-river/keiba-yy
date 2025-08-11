"""
WebSocket接続管理
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from src.api.config import settings
from src.api.schemas.common import WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket接続マネージャー"""

    def __init__(self):
        # 接続中のWebSocketを管理
        self.active_connections: dict[str, WebSocket] = {}
        # ユーザーごとの接続を管理
        self.user_connections: dict[str, set[str]] = {}
        # チャンネル（トピック）ごとの購読者を管理
        self.channel_subscribers: dict[str, set[str]] = {}
        # 接続情報
        self.connection_info: dict[str, dict[str, Any]] = {}
        # ハートビートタスク
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}

    async def connect(
        self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None
    ) -> bool:
        """WebSocket接続を確立"""
        try:
            # 最大接続数チェック
            if len(self.active_connections) >= settings.websocket_max_connections:
                await websocket.close(code=1008, reason="Maximum connections reached")
                return False

            await websocket.accept()

            # 接続を登録
            self.active_connections[client_id] = websocket

            # ユーザー接続を記録
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(client_id)

            # 接続情報を保存
            self.connection_info[client_id] = {
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "subscribed_channels": set(),
            }

            # ハートビートタスクを開始
            self.heartbeat_tasks[client_id] = asyncio.create_task(
                self._heartbeat_loop(client_id)
            )

            # 接続成功メッセージを送信
            await self.send_personal_message(
                WebSocketMessage(
                    type="connection",
                    data={
                        "status": "connected",
                        "client_id": client_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
                client_id,
            )

            logger.info(
                f"WebSocket connected: client_id={client_id}, user_id={user_id}"
            )
            return True

        except Exception as e:
            logger.exception(f"Connection error: {e}")
            return False

    async def disconnect(self, client_id: str):
        """WebSocket接続を切断"""
        try:
            # ハートビートタスクをキャンセル
            if client_id in self.heartbeat_tasks:
                self.heartbeat_tasks[client_id].cancel()
                del self.heartbeat_tasks[client_id]

            # 接続情報を取得
            conn_info = self.connection_info.get(client_id)

            # チャンネル購読を解除
            for channel in list(conn_info.get("subscribed_channels", [])):
                await self.unsubscribe(client_id, channel)

            # ユーザー接続から削除
            if conn_info and conn_info.get("user_id"):
                user_id = conn_info["user_id"]
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(client_id)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]

            # 接続を削除
            if client_id in self.active_connections:
                del self.active_connections[client_id]

            if client_id in self.connection_info:
                del self.connection_info[client_id]

            logger.info(f"WebSocket disconnected: client_id={client_id}")

        except Exception as e:
            logger.exception(f"Disconnect error: {e}")

    async def send_personal_message(self, message: WebSocketMessage, client_id: str):
        """個別メッセージ送信"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message.dict())

                # 最終アクティビティを更新
                if client_id in self.connection_info:
                    self.connection_info[client_id]["last_activity"] = datetime.utcnow()

            except WebSocketDisconnect:
                await self.disconnect(client_id)
            except Exception as e:
                logger.exception(f"Send message error: {e}")
                await self.disconnect(client_id)

    async def broadcast(
        self, message: WebSocketMessage, exclude_client: Optional[str] = None
    ):
        """全クライアントにブロードキャスト"""
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            if client_id == exclude_client:
                continue

            try:
                await websocket.send_json(message.dict())
            except:
                disconnected_clients.append(client_id)

        # 切断されたクライアントを削除
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def send_to_user(self, message: WebSocketMessage, user_id: str):
        """特定ユーザーの全接続にメッセージ送信"""
        if user_id in self.user_connections:
            for client_id in self.user_connections[user_id]:
                await self.send_personal_message(message, client_id)

    async def subscribe(self, client_id: str, channel: str):
        """チャンネル購読"""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(client_id)

        if client_id in self.connection_info:
            self.connection_info[client_id]["subscribed_channels"].add(channel)

        # 購読確認メッセージ
        await self.send_personal_message(
            WebSocketMessage(
                type="subscription",
                data={
                    "action": "subscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
            client_id,
        )

        logger.info(f"Client {client_id} subscribed to channel: {channel}")

    async def unsubscribe(self, client_id: str, channel: str):
        """チャンネル購読解除"""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(client_id)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]

        if client_id in self.connection_info:
            self.connection_info[client_id]["subscribed_channels"].discard(channel)

        # 購読解除確認メッセージ
        await self.send_personal_message(
            WebSocketMessage(
                type="subscription",
                data={
                    "action": "unsubscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
            client_id,
        )

    async def publish_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        exclude_client: Optional[str] = None,
    ):
        """チャンネルにメッセージを配信"""
        if channel in self.channel_subscribers:
            disconnected_clients = []

            for client_id in self.channel_subscribers[channel]:
                if client_id == exclude_client:
                    continue

                if client_id in self.active_connections:
                    try:
                        await self.send_personal_message(message, client_id)
                    except:
                        disconnected_clients.append(client_id)

            # 切断されたクライアントを削除
            for client_id in disconnected_clients:
                await self.disconnect(client_id)

    async def _heartbeat_loop(self, client_id: str):
        """ハートビート送信ループ"""
        try:
            while client_id in self.active_connections:
                await asyncio.sleep(settings.websocket_heartbeat_interval)

                # Pingメッセージを送信
                await self.send_personal_message(
                    WebSocketMessage(
                        type="ping", data={"timestamp": datetime.utcnow().isoformat()}
                    ),
                    client_id,
                )

                # タイムアウトチェック
                if client_id in self.connection_info:
                    last_activity = self.connection_info[client_id]["last_activity"]
                    timeout = settings.websocket_heartbeat_interval * 3

                    if (datetime.utcnow() - last_activity).total_seconds() > timeout:
                        logger.warning(f"Client {client_id} timed out")
                        await self.disconnect(client_id)
                        break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Heartbeat error for {client_id}: {e}")

    async def handle_message(self, client_id: str, message: dict[str, Any]):
        """クライアントからのメッセージを処理"""
        try:
            msg_type = message.get("type")
            data = message.get("data", {})

            # 最終アクティビティを更新
            if client_id in self.connection_info:
                self.connection_info[client_id]["last_activity"] = datetime.utcnow()

            # メッセージタイプごとの処理
            if msg_type == "pong":
                # Pongレスポンス（ハートビート応答）
                pass

            elif msg_type == "subscribe":
                # チャンネル購読
                channel = data.get("channel")
                if channel:
                    await self.subscribe(client_id, channel)

            elif msg_type == "unsubscribe":
                # チャンネル購読解除
                channel = data.get("channel")
                if channel:
                    await self.unsubscribe(client_id, channel)

            elif msg_type == "message":
                # メッセージ配信
                channel = data.get("channel")
                content = data.get("content")

                if channel and content:
                    await self.publish_to_channel(
                        channel,
                        WebSocketMessage(
                            type="message",
                            data={
                                "channel": channel,
                                "content": content,
                                "from": client_id,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        ),
                        exclude_client=client_id,
                    )
            else:
                # 不明なメッセージタイプ
                await self.send_personal_message(
                    WebSocketMessage(
                        type="error",
                        data={
                            "message": f"Unknown message type: {msg_type}",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    ),
                    client_id,
                )

        except Exception as e:
            logger.exception(f"Message handling error: {e}")
            await self.send_personal_message(
                WebSocketMessage(
                    type="error",
                    data={
                        "message": "Message processing error",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
                client_id,
            )

    def get_stats(self) -> dict[str, Any]:
        """接続統計を取得"""
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "channels": list(self.channel_subscribers.keys()),
            "channel_stats": {
                channel: len(subscribers)
                for channel, subscribers in self.channel_subscribers.items()
            },
        }


# シングルトンインスタンス
manager = ConnectionManager()
