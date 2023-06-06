from biliarchiver._biliarchiver_upload_bvid import upload_bvid
from biliarchiver.config import config
import os

def main():
    for bvid_with_upper_part in os.listdir(config.storage_home_dir / 'videos'):
        bvid = bvid_with_upper_part
        if '-' in bvid_with_upper_part:
            bvid = bvid_with_upper_part.split('-')[0]

        upload_bvid(bvid)

if __name__ == '__main__':
    main()