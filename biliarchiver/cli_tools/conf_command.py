import click
from dataclasses import dataclass
from biliarchiver.i18n import _

@click.command(help=click.style(_("将传入参数写入配置文件"), fg="cyan"))
@click.option("--video_concurrency", "-v", type=click.INT, default=None, help=_("视频下载并发数"))
@click.option("--part_concurrency", "-p", type=click.INT, default=None, help=_("分P下载并发数"))
@click.option("--stream_retry", "-r", type=click.INT, default=None, help=_("流下载重试次数"))
@click.option("--storage_home_dir", "-s", type=click.STRING, default=None, help=_("存储目录"))
@click.option("--ia_key_file", "-i", type=click.STRING, default=None, help=_("IA key文件"))
@click.option("--cookies_file", "-c", type=click.STRING, default=None, help=_("cookies文件"))

def config(**kwargs):
    from biliarchiver.config import _Config
    config = _Config()
    for k, v in kwargs.items():
        if v is not None:
            setattr(config, k, v)
    config.save()
    print(_("配置文件写入成功"))