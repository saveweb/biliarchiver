from biliarchiver.i18n import _


class VideosBasePathNotFoundError(FileNotFoundError):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Videos base path {self.path} not found"


class VideosNotFinishedDownloadError(FileNotFoundError):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Videos not finished download: {self.path}"


class VersionOutdatedError(Exception):
    def __init__(self, version):
        self.version = version

    def __str__(self):
        return _("请更新 biliarchiver。当前版本已过期：") + str(self.version)


class DirNotInitializedError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return _("先在当前工作目录运行 `biliarchiver init` 以初始化配置")
