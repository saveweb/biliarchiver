class VideosBasePathNotFoundError(FileNotFoundError):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return f"Videos base path {self.path} not found"