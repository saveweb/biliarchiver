from _biliarchiver_upload_bvid import upload_bvid
import os

def main():
    for bvid in os.listdir('biliarchiver/videos'):
        upload_bvid(bvid)

if __name__ == '__main__':
    main()