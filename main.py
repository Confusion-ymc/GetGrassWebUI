import asyncio
import uuid

import uvicorn
from typing import Dict, Optional

from fastapi import FastAPI, APIRouter, UploadFile, BackgroundTasks
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from utils import parse_line
from core import AsyncGrassWs

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

client_router = APIRouter(prefix='/client')

all_client: Dict[str, AsyncGrassWs] = {}
all_client_ids = []

CLIENT_INDEX = 0

# 或者，如果有多个 task
background_tasks = set()


def run_client(client_id):
    task = asyncio.create_task(all_client[client_id].run())

    # 将 task 添加到集合中，以保持强引用：
    background_tasks.add(task)

    # 为了防止 task 被永远保持强引用，而无法被垃圾回收
    # 让每个 task 在结束后将自己从集合中移除：
    task.add_done_callback(background_tasks.discard)
    return client_id


def add_client(grass_client: AsyncGrassWs):
    client_id = uuid.uuid4().__str__()
    all_client[client_id] = grass_client
    all_client_ids.append(client_id)
    return client_id


async def delete_client(client_id):
    logger.info(f'[退出] {all_client[client_id].user_id}')
    await all_client[client_id].stop()
    del all_client[client_id]
    all_client_ids.remove(client_id)


def load_file_clients(data):
    new_clients = []
    index = 0
    for line in data.split('\n'):
        user_id, proxy_url = parse_line(line)
        if not user_id:
            continue
        index += 1
        client = AsyncGrassWs(user_id=user_id, proxy_url=proxy_url)
        new_clients.append(add_client(client))
    return new_clients


async def threading_run_clients(clients):
    for client_id in clients:
        run_client(client_id)


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@client_router.get("/{client_id}")
def find_one(client_id: str):
    client = all_client.get(client_id)
    data = {
        'data': {
            'status': None,
            "proxy_url": None,
            "logs": []
        },
        'message': "failed"
    }
    if client is not None:
        data = {
            'data': {
                'status': client.status,
                "proxy_url": client.proxy_url,
                "logs": list(reversed(client.logs[-50:]))
            },
            'message': "success"
        }
    return data


@client_router.get("/")
def find_all():
    data = []
    for client_id in all_client_ids:
        try:
            data.append({
                'id': client_id,
                'user_id': all_client[client_id].user_id,
                'status': all_client[client_id].status,
                "proxy_url": all_client[client_id].proxy_url
            })
        except:
            continue
    return {
        'data': data,
        'message': "success"
    }


@client_router.post("/")
async def add(user_id: str, proxy_url: Optional[str] = None):
    client = AsyncGrassWs(user_id=user_id, proxy_url=proxy_url or None)
    client_id = add_client(client)
    run_client(client_id)
    return {'data': client_id, 'message': 'create success'}


@client_router.delete("/{user_id}")
async def delete_one(user_id: str):
    await delete_client(user_id)
    return {'data': user_id, 'message': 'success'}


@client_router.delete("/")
async def delete_all():
    all_client_ids_copy = all_client_ids[::]
    for client_id in all_client_ids_copy:
        await delete_client(client_id)
    return {'data': [], 'message': 'success'}


@app.post("/upload/")
async def run_by_file(file: UploadFile, background_task: BackgroundTasks):
    data = (await file.read()).decode()
    new_clients = load_file_clients(data)
    background_task.add_task(threading_run_clients, new_clients)
    return {"data": None, 'message': 'success'}


app.include_router(client_router)

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0')
