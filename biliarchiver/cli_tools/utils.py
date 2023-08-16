from pathlib import Path
from biliarchiver.utils.identifier import is_bvid


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
        assert is_bvid(bvid), f"bvid {bvid} 不合法"

    assert bvids_list is not None and len(bvids_list) > 0, "bvids 为空"

    return bvids_list
