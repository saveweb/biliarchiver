import asyncio
from asyncio import Queue
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from biliarchiver.rest_api.bilivid import BiliVideo
from datetime import datetime
from biliarchiver.version import BILI_ARCHIVER_VERSION

app = FastAPI()

queue = Queue()

from enum import Enum


class VideoStatus(str, Enum):
    pending = "pending"
    downloading = "downloaded"
    uploading = "uploaded"
    finished = "finished"
    failed = "failed"


class Video:
    def __init__(self, vid, status=VideoStatus.pending):
        self.vid = vid
        self.status = status

    def __str__(self):
        return f"{self.vid} {self.status}"


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


# @app.delete("/archive/{vid}")
# async def delete(vid: str):
#     # TODO
#     return {"success": True, "vid": vid}


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
    # bg_task = BackgroundTasks()
    # bg_task.add_task(scheduler)
    asyncio.create_task(scheduler())
    load_queue()


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")
    save_queue()
    exit()


def save_queue():
    with open("queue.txt", "w") as f:
        while not queue.empty():
            video = queue.get_nowait()
            f.write(str(video) + "\n")


def load_queue():
    try:
        with open("queue.txt", "r") as f:
            for line in f:
                queue.put_nowait(Video(*line.strip().split(" ")))
    except FileNotFoundError:
        pass
