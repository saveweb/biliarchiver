import click
from rich.console import Console
from biliarchiver.i18n import _


@click.command(help=click.style(_("从哔哩哔哩下载"), fg="cyan"))
@click.option(
    "--bvids",
    "-i",
    type=click.STRING,
    required=True,
    help=_("空白字符分隔的 bvids 列表（记得加引号），或文件路径"),
)
@click.option(
    "--skip-ia-check",
    "-s",
    is_flag=True,
    default=False,
    show_default=True,
    help=_("不检查 IA 上是否已存在对应 BVID 的 item ，直接开始下载"),
)
@click.option(
    "--from-browser",
    "--fb",
    type=str,
    default=None,
    help=_("从指定浏览器导入 cookies (否则导入 config.json 中的 cookies_file)"),
)
@click.option(
    "--min-free-space-gb",
    type=int,
    default=10,
    help=_("最小剩余空间 (GB)，用超退出"),
    show_default=True,
)
@click.option(
    "--skip-to", type=int, default=0, show_default=True, help=_("跳过文件开头 bvid 的个数")
)
@click.option(
    "--disable-version-check",
    type=bool,
    is_flag=True,
    default=False,
    help=_("禁用 biliarchiver 的 pypi 版本检查")
)
def down(**kwargs):
    from biliarchiver.cli_tools.bili_archive_bvids import _down

    try:
        import asyncio

        asyncio.run(_down(**kwargs))
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        # 显示终端光标
        console = Console()
        console.show_cursor()
