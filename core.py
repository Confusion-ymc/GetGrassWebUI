import asyncio
import json
import ssl
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

import socks
import websockets
from faker import Faker
from loguru import logger
from websockets import WebSocketCommonProtocol

from utils import parse_proxy_url, Status

logger.remove()  # 移除默认的控制台输出处理器

logger.add(sys.stdout, level="INFO")  # 添加新的控制台输出处理器

INFO = 'INFO'
DEBUG = 'DEBUG'


class AsyncGrassWs:
    def __init__(self, user_id, proxy_url=None):
        self.user_id = user_id
        self.user_agent = Faker().chrome()
        self.device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url or ""))
        self.proxy_url = proxy_url
        self.ws: Optional[WebSocketCommonProtocol] = None
        self.status: Status = Status.disconnect
        self._stop = False
        self._stopped = False
        self._ping_stopped = False
        self.server_url = "wss://proxy.wynd.network:4650/"
        self.server_hostname = "proxy.wynd.network"
        self.logs = []

    def log(self, level, message):
        logger.log(logger.level(level).name, message)
        self.logs.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message))
        if len(self.logs) >= 100:
            self.logs = self.logs[-100:]

    async def send_ping(self):
        await asyncio.sleep(5)
        while not self._stop:
            try:
                send_message = json.dumps(
                    {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                if self.ws:
                    self.log(DEBUG, f'[发送消息] [{self.user_id}] [{self.proxy_url}] [{send_message}]')
                    await self.ws.send(send_message)
            except Exception as e:
                self.log(DEBUG, f'[PING Error] {e}')
            for i in range(20):
                if self._stop:
                    break
                await asyncio.sleep(1)
        self._ping_stopped = True

    def auth_response(self, message):
        return {
            "id": message["id"],
            "origin_action": "AUTH",
            "result": {
                "browser_id": self.device_id,
                "user_id": self.user_id,
                "user_agent": self.user_agent,
                "timestamp": int(time.time()),
                "device_type": "extension",
                "version": "3.3.2"
            }
        }

    async def run(self):
        self.log(INFO, f'[启动] [{self.user_id}] [{self.proxy_url}]')
        asyncio.create_task(self.send_ping())
        loop = asyncio.get_event_loop()
        while True:
            ws_proxy = None
            try:
                self.status = Status.connecting
                if self.proxy_url:
                    proxy_type, http_proxy_host, http_proxy_port, http_proxy_auth = parse_proxy_url(self.proxy_url)
                    if http_proxy_auth:
                        username, password = http_proxy_auth[0], http_proxy_auth[1]
                    else:
                        username = password = None
                    # Initialize the connection to the server through the proxy
                    self.log(DEBUG, f'[连接代理] [{self.user_id}] [{self.proxy_url}]')
                    ws_proxy = socks.socksocket()
                    ws_proxy.set_proxy(socks.PROXY_TYPES[proxy_type.upper()], http_proxy_host, http_proxy_port,
                                       username=username, password=password)
                    await loop.run_in_executor(None, ws_proxy.connect, ("proxy.wynd.network", 4650))  # 执行阻塞函数
                    self.log(DEBUG, f'[连接代理成功] [{self.user_id}] [{self.proxy_url}]')
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                custom_headers = {
                    "User-Agent": self.user_agent
                }
                self.log(DEBUG, f'[连接服务器] [{self.user_id}] [{self.proxy_url}]')
                self.ws = await websockets.connect(
                    self.server_url,
                    ssl=ssl_context,
                    sock=ws_proxy,
                    extra_headers=custom_headers,
                    server_hostname=self.server_hostname,
                    open_timeout=60
                )

                self.log(DEBUG, f'[连接服务器成功] [{self.user_id}] [{self.proxy_url}]')
                while True:
                    response = await self.ws.recv()
                    message = json.loads(response)
                    self.log(DEBUG, f'[收到消息] [{self.user_id}] [{self.proxy_url}] [{message}]')
                    if message.get("action") == "AUTH":
                        auth_response = self.auth_response(message)
                        self.log(DEBUG, f'[发送消息] [{self.user_id}] [{self.proxy_url}] [{auth_response}]')
                        await self.ws.send(json.dumps(auth_response))
                        self.status = Status.connected
                        self.log(INFO, f'[在线] [{self.user_id}] [{self.proxy_url}]')
                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        self.log(DEBUG, f'[发送消息] [{self.user_id}] [{self.proxy_url}] [{pong_response}]')
                        await self.ws.send(json.dumps(pong_response))
            except Exception as e:
                self.log(INFO, f'[连接断开] [{self.user_id}] [{self.proxy_url}] {e}')
            self.status = Status.disconnect
            if not self._stop:
                self.log(DEBUG, f'[重新连接] [{self.user_id}] [{self.proxy_url}]')
                try:
                    ws_proxy.close()
                except:
                    pass
            else:
                while not self._ping_stopped:
                    await asyncio.sleep(1)
                self.log(INFO, f'手动退出 [{self.user_id}] [{self.proxy_url}]')
                self._stopped = True
                break
            await asyncio.sleep(5)

    async def stop(self):
        self._stop = True
        if self.ws:
            await self.ws.close()
