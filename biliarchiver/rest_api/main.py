import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import os
from pathlib import Path
from typing import List

from biliarchiver.cli_tools.utils import read_bvids_from_txt

try:
    from fastapi import FastAPI, HTTPException
except ImportError:
    print("Please install fastapi")
    print("`pip install fastapi`")
    raise


from biliarchiver.cli_tools.get_command import by_favlist, by_series, by_up_videos, by_season
from biliarchiver.rest_api.bilivid import BiliVideo, VideoStatus
from biliarchiver.version import BILI_ARCHIVER_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pending_queue, other_queue
    pending_queue = BiliVideoQueue()
    other_queue = BiliVideoQueue(maxsize=250)
    print("Loading queue...")
    load_queue()
    print("Queue loaded")
    _video_scheduler = asyncio.create_task(video_scheduler())
    yield
    print("Shutting down...")
    save_queue()
    print("Queue saved")


class BiliVideoQueue(asyncio.Queue):
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

pending_queue: BiliVideoQueue = None # type: ignore
other_queue: BiliVideoQueue = None # type: ignore

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

async def source_action(fun, source_id: str, TRUNCATE=20):
    try:
        txt_path = await fun(source_id, truncate=TRUNCATE)
    except Exception as e:
        print(f"Failed to call {fun}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to call {fun}: {e}")
    if not isinstance(txt_path, Path):
        raise HTTPException(status_code=500, detail="Failed to get path")

    bvids = read_bvids_from_txt(txt_path)
    txt_path.unlink(missing_ok=True)

    return {"success": True, "bvids": bvids}

@app.get("/get_bvids_by/{source_type}/{source_id}")
@app.post("/get_bvids_by/{source_type}/{source_id}")
async def perform_source_action_from_req(source_type: str, source_id: str):
    # make sure source_id is valid integer
    if not source_id.isdecimal():
        raise HTTPException(status_code=400, detail="Invalid source_id")

    source_id = str(int(source_id))

    fun_mapping = {
        "up_videos": by_up_videos,
        "favlist": by_favlist,
        "series": by_series,
        "season": by_season,
    }

    if source_type not in fun_mapping:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    fun = fun_mapping[source_type]

    assert callable(fun)

    return await source_action(fun, source_id, TRUNCATE=300)

async def video_scheduler():
    while True:
        print("Getting a video URL... If no video URL is printed, the queue is empty.")
        video = await pending_queue.get()
        print(f"Start downloading {video}")

        video.status = VideoStatus.downloading
        await other_queue.put(video)
        downloaded = False
        for _ in range(2):
            try:
                if retcode := await video.down():
                    raise Exception(f"Download failed with retcode {retcode}")
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
