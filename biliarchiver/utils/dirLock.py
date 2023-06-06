import os
import sys
import importlib.util

class AlreadyRunningError(Exception):
    def __init__(self, message: str=""):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message


LOCK_FILENAME = '_uploading.lock'

class UploadLock_Basic:
    def __init__(self, lock_dir):
        self.lock_file = os.path.join(lock_dir, LOCK_FILENAME)

    def __enter__(self):
        if os.path.exists(self.lock_file):
            with open(self.lock_file, 'r', encoding='utf-8') as f:
                print(f.read())
            print("Another instance is already running.")
            raise AlreadyRunningError('Another instance is already running.')
        else:
            with open(self.lock_file, 'w', encoding='utf-8') as f:
                f.write(f'PID: {os.getpid()}: Running')
            # print("Acquired lock, continuing.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.lock_file)
        # print("Released lock.")

    # decorator
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


class UploadLock_Fcntl():
    fcntl = None
    try:
        import fcntl
    except ModuleNotFoundError:
        pass

    def __init__(self, lock_dir):
        if self.fcntl is None:
            raise(ModuleNotFoundError("No module named 'fcntl'", name='fcntl'))
        
        self.lock_file = os.path.join(lock_dir, LOCK_FILENAME)
        self.lock_file_fd = None

    def __enter__(self):
        assert self.fcntl is not None
        self.lock_file_fd = open(self.lock_file, 'w')
        try:
            self.fcntl.lockf(self.lock_file_fd, self.fcntl.LOCK_EX | self.fcntl.LOCK_NB)
            # print("Acquired lock, continuing.")
        except IOError:
            raise AlreadyRunningError("Another instance is already running.")
            

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.fcntl is not None
        if self.lock_file_fd is None:
            raise IOError("Lock file not opened.")
        self.fcntl.lockf(self.lock_file_fd, self.fcntl.LOCK_UN)
        self.lock_file_fd.close()
        os.remove(self.lock_file)
        # print("Released lock.")

    # decorator
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

class UploadLock():
    def __new__(cls, lock_dir):
        fcntl_avaivable = importlib.util.find_spec('fcntl')
        if fcntl_avaivable is not None:
            return UploadLock_Fcntl(lock_dir)
        else:
            return UploadLock_Basic(lock_dir)