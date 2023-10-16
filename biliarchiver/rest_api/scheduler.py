import asyncio
from biliarchiver.rest_api.bilivid import BiliVideo


class ArchiveScheduler:
    def __init__(self) -> None:
        self.queue = []
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.main())
        self.should_stop = False

    async def main(self):
        while True:
            if self.should_stop:
                break
            if len(self.queue) > 0:
                vid = self.queue.pop(0)
                await vid.down()
                await vid.up()
            else:
                await asyncio.sleep(5)

    def add(self, vid: BiliVideo):
        self.queue.append(vid)

    def stop(self):
        self.should_stop = True
        self.loop.close()
