import asyncio
from asyncio import Queue
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from biliarchiver.rest_api.bilivid import BiliVideo
from datetime import datetime
from biliarchiver.version import BILI_ARCHIVER_VERSION

app = FastAPI()

queue = Queue()


class Video:
    def __init__(self, vid):
        self.vid = vid


@app.get("/")
async def root():
    return {
        "status": "ok",
        "biliarchiver": {"version": BILI_ARCHIVER_VERSION},
        "api": {"version": 1},
        "timestamp": int(datetime.now().timestamp()),
    }


@app.put("/archive/{vid}")
@app.post("/archive/{vid}")
async def add(vid: str):
    video = BiliVideo(vid)
    await queue.put(video)
    return {"success": True, "vid": vid}


@app.get("/archive")
async def get():
    return {"success": True, "queue": map(str, queue)}


@app.get("/archive/{vid}")
async def get(vid: str):
    if vid in queue:
        return {"success": True, "vid": vid}
    return {"success": False, "vid": vid}


@app.delete("/archive/{vid}")
async def delete(vid: str):
    return {"success": True, "vid": vid}


async def scheduler():
    while True:
        print("Getting a video URL... If no video URL is printed, the queue is empty.")
        video = await queue.get()
        print(f"Start donwloading {video}")
        await video.down()
        print(f"Start uploading {video}")
        await video.up()


@app.on_event("startup")
async def startup_event():
    bg_task = BackgroundTasks()
    bg_task.add_task(scheduler)
    asyncio.create_task(scheduler())
