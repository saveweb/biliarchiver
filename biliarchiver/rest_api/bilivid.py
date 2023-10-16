from biliarchiver.cli_tools.bili_archive_bvids import _down
from biliarchiver._biliarchiver_upload_bvid import upload_bvid
from biliarchiver.config import config


class BiliVideo:
    def __init__(self, bvid) -> None:
        if not bvid.startswith("BV"):
            bvid = "BV" + bvid
        self.bvid = bvid

    def __str__(self) -> str:
        return self.bvid

    async def down(self):
        await _down(
            bvids=self.bvid,
            skip_ia_check=True,
            from_browser=None,
            min_free_space_gb=1,
            skip_to=0,
        )

    async def up(self):
        upload_bvid(
            self.bvid,
            update_existing=False,
            collection="default",
            delete_after_upload=False,
        )
