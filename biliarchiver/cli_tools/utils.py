from pathlib import Path
from biliarchiver.utils.identifier import is_bvid
from biliarchiver.i18n import _


def read_bvids(bvids: str) -> list[str]:
    bvids_list = None

    file = Path(bvids)
    if file.exists() and file.is_file():
        with open(file, "r", encoding="utf-8") as f:
            bvids_list = f.read().split()
    else:
        bvids_list = bvids.split()

    del bvids

    for bvid in bvids_list:
        assert is_bvid(bvid), _("bvid {} 不合法").format(bvid)

    assert bvids_list is not None and len(bvids_list) > 0, _("bvids 为空")

    return bvids_list
