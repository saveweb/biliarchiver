from enum import Enum
import time
from typing import Optional

from biliarchiver.cli_tools.bili_archive_bvids import _down
from biliarchiver.cli_tools.up_command import DEFAULT_COLLECTION


class VideoStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    uploading = "uploaded"
    finished = "finished"
    failed = "failed"


class BiliVideo:
    def __init__(self, bvid: str, status: VideoStatus):
        if not bvid.startswith("BV"):
            bvid = "BV" + bvid
        self.added_time = int(time.time())
        self.bvid = bvid
        self.status = status


    def __str__(self) -> str:
        return "\t".join([self.bvid, self.status])

    async def down(self):
        await _down(
            bvids=self.bvid,
            skip_ia_check=True,
            from_browser=None,
            min_free_space_gb=1,
            skip_to=0,
            disable_version_check=True,
        )

    async def up(self) -> int:
        import subprocess as sp
        from asyncio import subprocess
        from shlex import quote

        cmd = ["biliarchiver", "up" ,"-i", quote(self.bvid), "-d"]

        process: Optional[subprocess.Process] = None
        try:
            process = await subprocess.create_subprocess_exec(*cmd)
            retcode = await process.wait()
        except (KeyboardInterrupt, SystemExit, Exception):
            if process:
                process.terminate()
                await process.wait()
                print("upload terminated")
            return -1
        else:
            return retcode
