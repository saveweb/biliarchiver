import click
from biliarchiver.cli_tools.up_command import up
from biliarchiver.cli_tools.down_command import down
from biliarchiver.cli_tools.get_command import get


@click.group()
def biliarchiver():
    pass


@biliarchiver.command(help=click.style("初始化所需目录", fg="cyan"))
def init():
    import pathlib

    biliarchiver_home = pathlib.Path.cwd() / "biliarchiver.home"
    bilibili_archive_dir = pathlib.Path.cwd() / "bilibili_archive_dir"
    biliarchiver_home.mkdir(exist_ok=True)
    bilibili_archive_dir.mkdir(exist_ok=True)


biliarchiver.add_command(up)
biliarchiver.add_command(down)
biliarchiver.add_command(get)


if __name__ == "__main__":
    biliarchiver()
