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
        return "Version outdated: %s" % self.version