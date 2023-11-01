import asyncio
import os
from pathlib import Path
from typing import List, Optional, Union

from bilix.sites.bilibili.downloader import DownloaderBilibili
from httpx import AsyncClient, Client, TransportError
from rich.traceback import install

from biliarchiver.archive_bvid import archive_bvid
from biliarchiver.config import config
from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX
from biliarchiver.utils.http_patch import HttpOnlyCookie_Handler
from biliarchiver.utils.version_check import check_outdated_version
from biliarchiver.utils.storage import get_free_space
from biliarchiver.utils.identifier import human_readable_upper_part_map
from biliarchiver.utils.ffmpeg import check_ffmpeg
from biliarchiver.version import BILI_ARCHIVER_VERSION
from biliarchiver.cli_tools.utils import read_bvids
from biliarchiver.i18n import _

install()


def check_ia_item_exist(client: Client, identifier: str) -> bool:
    cache_dir = config.storage_home_dir / "ia_item_exist_cache"
    # check_ia_item_exist_from_cache_file:
    if (cache_dir / f"{identifier}.mark").exists():
        # print('from cached .mark')
        return True

    def create_item_exist_cache_file(identifier: str) -> Path:
        with open(cache_dir / f"{identifier}.mark", "w", encoding="utf-8") as f:
            f.write("")
        return cache_dir / f"{identifier}.mark"

    params = {
        "identifier": identifier,
        "output": "json",
    }
    # check_identifier.php API 响应快
    r = None
    for _ in range(3):
        try:
            r = client.get(
                "https://archive.org/services/check_identifier.php", params=params
            )
            break
        except TransportError as e:
            print(e, "retrying...")
    assert r is not None
    r.raise_for_status()
    r_json = r.json()
    assert r_json["type"] == "success"
    if r_json["code"] == "available":
        return False
    elif r_json["code"] == "not_available":  # exists
        cache_dir.mkdir(parents=True, exist_ok=True)
        create_item_exist_cache_file(identifier)
        return True
    else:
        raise ValueError(f'Unexpected code: {r_json["code"]}')


async def _down(
    bvids: str,
    skip_ia_check: bool,
    from_browser: Optional[str],
    min_free_space_gb: int,
    skip_to: int,
    disable_version_check: bool,
):
    assert check_ffmpeg() is True, _("ffmpeg 未安装")

    bvids_list = read_bvids(bvids)

    check_outdated_version(
        pypi_project="biliarchiver", self_version=BILI_ARCHIVER_VERSION
    ) if disable_version_check is False else print(
        _("pypi version check disabled")
    )

    d = DownloaderBilibili(
        hierarchy=True,
        sess_data=None,  # sess_data 将在后面装载 cookies 时装载 # type: ignore
        video_concurrency=config.video_concurrency,
        part_concurrency=config.part_concurrency,
        stream_retry=config.stream_retry,
    )

    # load cookies
    if from_browser is not None:
        update_cookies_from_browser(d.client, from_browser)
    else:
        update_cookies_from_file(d.client, config.cookies_file)
    client = Client(cookies=d.client.cookies, headers=d.client.headers)
    logined = is_login(client)
    if not logined:
        return

    def check_free_space():
        if min_free_space_gb != 0:
            if (
                get_free_space(path=config.storage_home_dir) // 1024 // 1024 // 1024
                <= min_free_space_gb
            ):
                return False  # not pass
        return True  # pass

    d.progress.start()
    sem = asyncio.Semaphore(config.video_concurrency)
    tasks: List[asyncio.Task] = []

    def tasks_check():
        for task in tasks:
            if task.done():
                _task_exception = task.exception()
                if isinstance(_task_exception, BaseException):
                    import traceback
                    traceback.print_exc()
                    print(f"任务 {task} 出错，即将异常退出...")
                    for task in tasks:
                        task.cancel()
                    raise _task_exception
                # print(f'任务 {task} 已完成')
                tasks.remove(task)
        if not check_free_space():
            s = _("剩余空间不足 {} GiB").format(min_free_space_gb)
            print(s)
            for task in tasks:
                task.cancel()
            raise RuntimeError(s)

    for index, bvid in enumerate(bvids_list):
        if index < skip_to:
            print(f"跳过 {bvid} ({index+1}/{len(bvids_list)})", end="\r")
            continue
        tasks_check()
        if not skip_ia_check:
            upper_part = human_readable_upper_part_map(string=bvid, backward=True)
            remote_identifier = f"{BILIBILI_IDENTIFIER_PERFIX}-{bvid}_p1-{upper_part}"
            if check_ia_item_exist(client, remote_identifier):
                print(_("IA 上已存在 {}，跳过").format(remote_identifier))
                continue

        upper_part = human_readable_upper_part_map(string=bvid, backward=True)
        videos_basepath: Path = (
            config.storage_home_dir / "videos" / f"{bvid}-{upper_part}"
        )
        if os.path.exists(videos_basepath / "_all_downloaded.mark"):
            print(_("{} 的所有分p都已下载过了").format(bvid))
            continue

        if len(tasks) >= config.video_concurrency:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            tasks_check()

        print(f"=== {bvid} ({index+1}/{len(bvids_list)}) ===")

        task = asyncio.create_task(
            archive_bvid(d, bvid, logined=logined, semaphore=sem),
            name=f"archive_bvid({bvid})",
        )
        tasks.append(task)

    while len(tasks) > 0:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        tasks_check()

    print("DONE")


def update_cookies_from_browser(client: AsyncClient, browser: str):
    try:
        import browser_cookie3

        f = getattr(browser_cookie3, browser.lower())
        cookies_to_update = f(domain_name="bilibili.com")
        client.cookies.update(cookies_to_update)
        print(_("从 {} 品尝了 {} 块 cookies").format(browser, len(cookies_to_update)))
    except AttributeError:
        raise AttributeError(f"Invalid Browser {browser}")


def update_cookies_from_file(client: AsyncClient, cookies_path: Union[str, Path]):
    if isinstance(cookies_path, Path):
        cookies_path = cookies_path.expanduser()
    elif isinstance(cookies_path, str):
        cookies_path = Path(cookies_path).expanduser()
    else:
        raise TypeError(f"cookies_path: {type(cookies_path)}")

    assert os.path.exists(cookies_path), _("cookies 文件不存在: {}").format(cookies_path)

    from http.cookiejar import MozillaCookieJar

    cj = MozillaCookieJar()

    with HttpOnlyCookie_Handler(cookies_path):
        cj.load(f"{cookies_path}", ignore_discard=True, ignore_expires=True)
        loadded_cookies = 0
        loadded_keys = []
        for cookie in cj:
            # only load bilibili cookies
            if "bilibili.com" not in cookie.domain:
                continue
            if cookie.name in loadded_keys:
                print(_("跳过重复的 cookies"), end="")
                print(f": {cookie.name}")
                # httpx 不能处理不同域名的同名 cookies，只好硬去重了
                continue
            assert cookie.value is not None
            client.cookies.set(
                cookie.name, cookie.value, domain=cookie.domain, path=cookie.path
            )
            loadded_keys.append(cookie.name)
            loadded_cookies += 1
        print(_("从 {} 品尝了 {} 块 cookies").format(cookies_path, loadded_cookies))
        if loadded_cookies > 100:
            print(_("吃了过多的 cookies，可能导致 httpx.Client 怠工，响应非常缓慢"))

        assert client.cookies.get("SESSDATA") is not None, "SESSDATA 不存在"
        # print(f'SESS_DATA: {client.cookies.get("SESSDATA")}')


def is_login(cilent: Client) -> bool:
    r = cilent.get("https://api.bilibili.com/x/member/web/account")
    r.raise_for_status()
    nav_json = r.json()
    if nav_json["code"] == 0:
        print(_("BiliBili 登录成功，饼干真香。"))
        print(_("NOTICE: 存档过程中请不要在 cookies 的源浏览器访问 B 站，避免 B 站刷新"), end=" ")
        print(_("cookies 导致我们半路下到的视频全是 480P 的优酷土豆级醇享画质。"))
        return True
    print(_("未登录/SESSDATA无效/过期，你这饼干它保真吗？"))
    return False


if __name__ == "__main__":
    raise DeprecationWarning(_("已废弃直接运行此命令，请改用 biliarchiver 命令"))
