import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

try:
    from fastapi import FastAPI
except ImportError:
    print("Please install fastapi")
    print("`pip install fastapi`")
    raise


from biliarchiver.rest_api.bilivid import BiliVideo, VideoStatus
from biliarchiver.version import BILI_ARCHIVER_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(scheduler())
    print("Loading queue...")
    load_queue()
    yield
    print("Shutting down...")
    save_queue()


class BiliQueue(Queue):
    def get_all(self) -> List[BiliVideo]:
        return list(self._queue) # type: ignore
    async def get(self) -> BiliVideo:
        return await super().get()
    async def remove(self, video: BiliVideo):
        try:
            self._queue.remove(video) # type: ignore
            return True
        except ValueError:
            return False
    def get_nowait(self) -> BiliVideo:
        return super().get_nowait()
    async def change_status(self, ori_video: BiliVideo, status: VideoStatus):
        await self.remove(ori_video)
        ori_video.status = status
        await self.put(ori_video)

pending_queue = BiliQueue()
other_queue = BiliQueue(maxsize=250)

app = FastAPI(lifespan=lifespan)

def get_all_items() -> List[BiliVideo]:
    l = pending_queue.get_all() + other_queue.get_all()
    l.sort(key=lambda x: x.added_time)
    return l

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
    video = BiliVideo(vid, status=VideoStatus.pending)
    await pending_queue.put(video)
    return {"success": True, "vid": vid}


@app.get("/archive")
async def get_all():
    all_item = get_all_items()
    return {"success": True, "total_tasks_queued": pending_queue.qsize(), "items": all_item}


@app.get("/archive/{vid}")
async def get_one(vid: str):
    all_item = get_all_items()
    if vid in [v.bvid for v in all_item]:
        v: BiliVideo = [v for v in all_item if v.bvid == vid][0]
        return {"success": True, "vid": vid, "status": v.status, "queue_index": all_item.index(v)}
    return {"success": False, "vid": vid, "status": "not_found"} # TODO


@app.delete("/archive/{vid}")
async def delete(vid: str):
    queue_list = pending_queue.get_all()
    if vid in [v.bvid for v in queue_list]:
        v: BiliVideo = [v for v in queue_list if v.bvid == vid][0]
        if await pending_queue.remove(v):
            return {"success": True, "vid": vid, "result": "removed", "queue_index": queue_list.index(v)}

    return {"success": False, "vid": vid, "status": "not_found"}


async def scheduler():
    while True:
        print("Getting a video URL... If no video URL is printed, the queue is empty.")
        video = await pending_queue.get()
        print(f"Start donwloading {video}")

        video.status = VideoStatus.downloading
        await other_queue.put(video)
        downloaded = False
        for _ in range(2):
            try:
                await video.down()
                downloaded = True
                break
            except Exception as e:
                print(e)
                print(f"(down) Retrying {video}...")
                await asyncio.sleep(5)
        if not downloaded:
            await other_queue.change_status(video, VideoStatus.failed)
            print(f"Failed to download {video}")
            continue

        print(f"Start uploading {video}")
        await other_queue.change_status(video, VideoStatus.uploading)
        uploaded = False
        for _ in range(3):
            try:
                retcode = await video.up()
                uploaded = True
                if retcode != 0:
                    raise Exception(f"Upload failed with retcode {retcode}")
                break
            except Exception as e:
                print(e)
                print(f"(up) Retrying {video}...")
                await asyncio.sleep(10)
        if not uploaded:
            await other_queue.change_status(video, VideoStatus.failed)
            print(f"Failed to upload {video}")
            continue

        await other_queue.change_status(video, VideoStatus.finished)
        print(f"Finished {video}")

def save_queue():
    with open("queue.txt", "w") as f:
        while not pending_queue.empty():
            video = pending_queue.get_nowait()
            f.write(str(video) + "\n")


def load_queue():
    try:
        with open("queue.txt", "r") as f:
            while line := f.readline().strip():
                pending_queue.put_nowait(BiliVideo(*line.split("\t")))
    except FileNotFoundError:
        pass
