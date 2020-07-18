import os 
import glob

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

capture_dirname = 'capt'
capture_dirpath = os.path.join(__location__, capture_dirname)
num_capture_subdir_padding = 3      # e.g. capt/004
capture_filename_gphoto2 = '%07n.jpg'       # e.g. capt/004/0000001.jpg
capture_filename_ffmpeg = '%07d.jpg'
video_filename = 'video.mp4'


'''
file structure:
    capt/
    capt/000/
    capt/000/0000001.jpg
    capt/000/0000002.jpg
    capt/000/video.mp4
    capt/001/
    capt/001/0000001.jpg
    capt/001/0000002.jpg
    ...
'''

def index_exists(index = 0):
    """Determines if the index exists. At least you need on jpg file in the directory for this to be determined.
    """ 
    subdir = get_subdir(index)
    if (os.path.isdir(capture_dirpath)
            and os.path.isdir(subdir)):
        jpgs = glob.glob(os.path.join(subdir, "*.jpg"))
        if len(jpgs) > 0:
            return True

    return False


def get_subdir(index = 0):
    """
    Return (str):
        capt/000
    """ 
    assert index >= 0
    
    return os.path.join(capture_dirpath, str(index).zfill(num_capture_subdir_padding))


def get_video_path(index = 0):
    '''
    Return (str):
        capt/000/video.mp4
    '''
    assert index >= 0

    return os.path.join(get_subdir(index), video_filename)


def list_subdirs():
    if os.path.isdir(capture_dirpath):
        file_and_dir = os.listdir(capture_dirpath)
        return sorted([dirname for dirname in file_and_dir if os.path.isdir(os.path.join(capture_dirpath, dirname))])
    
    else:
        return []


def list_jpgs(index = 0):
    return sorted(glob.glob(os.path.join(get_subdir(index) , "*.jpg")))


def get_last_index():
    dirs = list_subdirs()

    if len(dirs) > 0:
        last_index = int(dirs[-1])
    else:
        last_index = -1

    return last_index


def get_last_downloaded_filename(index = -1):
    if index < 0:
        # return the last time lapse
        index = get_last_index()


    filelist = list_jpgs(index)

    if len(filelist) > 0:
        last_filename = filelist[-1]
        return last_filename
    else:
        return None


def get_last_downloaded_num(index = -1):
    last_filename = get_last_downloaded_filename(index)
    return int(os.path.basename(last_filename)[:-4]) if last_filename is not None else None
