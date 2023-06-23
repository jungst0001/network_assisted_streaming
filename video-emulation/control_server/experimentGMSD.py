import os
import cv2
import time
import traceback
from calculateGMSD import calculateGMSD, getOriAndCompImage
from threading import Thread
from multiprocessing import Process, Queue

vidcap = cv2.VideoCapture()

VIDEO_DIR = '/home/wins/jin/video_emulation/Videos/Videos/'
VIDEO_NAME = 'enter-video-du8min'

BPS_400 = '_400_dashinit.mp4'
BPS_800 = '_800_dashinit.mp4'
BPS_1400 = '_1400_dashinit.mp4'
BPS_2000 = '_2000_dashinit.mp4'

DIR_NAME = '/GMSD_Result/'
IMAGE_DIR_NAME = '/GMSD_Image/'

BPS = [400, 800, 1400, 2000]

# LOGGING
LOG=False

# Experimentation parameter
TOTAL_FRAMES = 300

DEFAULT_METHOD = {
    'SMALL_REGION' : True,
    'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
    'CHECK_REGION' : False,
    'CHECK_REGION_SIZE' : '2x2', # check region size ex) 2x2, 4x4 (row by column)
    'FLAT_REGION' : False,
    'FLAT_DIRECTION' : 'VERTICLE', # VERTICLE (full height size) or HORIZONTAL (full width size)
    'FLAT_REGION_SIZE' : '1/2' # flat region size ex) 1/2, 1/4 (num by dom)
}

###############################

def saveFrameImage(vidcap, image_DIR, sec=0, count=0, name='video'):
#   vidcap.set(cv2.CAP_PROP_POS_MSEC, sec*1000)
    vidcap.set(cv2.CAP_PROP_POS_FRAMES, count)
    hasFrames, image = vidcap.read()
    if hasFrames:
        image_name = name + '_' + str(count) + '.png'
        cv2.imwrite(image_DIR + image_name, image)

    return hasFrames, image_name

def getFrameImage(bps, frame_number, image_DIR):
    image_name = bps + '_' + str(frame_number) + '.png'
    image = cv2.imread(image_DIR + image_name, cv2.IMREAD_COLOR)

    return image

def getVideoCap():
    vidCps = []

    vidCp_400 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_400)
    vidCp_800 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_800)
    vidCp_1400 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1400)
    vidCp_2000 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_2000)

    vidCps.append(vidCp_400)
    vidCps.append(vidCp_800)
    vidCps.append(vidCp_1400)
    vidCps.append(vidCp_2000)

    return vidCps

def divideByCheck(image, method):
    row = int(method['CHECK_REGION_SIZE'].split('x')[0])
    column = int(method['CHECK_REGION_SIZE'].split('x')[1])

    if row != column:
        print(f'Only number of row is applyed.\n')
        print(f'row: {row}\n')

    if LOG:
        print(f'divideByCheck() | row: {row}, column: {column}')

    (height, width, _) = image.shape

    images = []
    for i in range(row):
        h_start = int(height/row * i)
        h_end = int(height/row * (i+1))
        w_start = int(width/row * i)
        w_end = int(width/row * (i+1))
        cutted_image = image[h_start:h_end, w_start:w_end].copy()

        images.append(cutted_image)

    return images

# The main cutting point is center
def cutFlatRegion(image, method):
    numerator = int(method['FLAT_REGION_SIZE'].split('/')[0])
    denominator = int(method['FLAT_REGION_SIZE'].split('/')[1])
    fraction = numerator / denominator

    if denominator == 0:
        print(f'cutFlatRegion() | denominator is 0\n')
        exit()

    (height, width, _) = image.shape

    middle_height = height/2
    middle_width = width/2

    if method['FLAT_DIRECTION'] == 'VERTICLE':
        mh_start = 0
        mh_end = height
        mw_start = int(middle_width - middle_width*fraction)
        mw_end = int(middle_width + middle_width*fraction)
    else: # FLAT_DIRECTION is HORIZONTAL
        mh_start = int(middle_height - middle_height*fraction)
        mh_end = int(middle_height + middle_height*fraction)
        mw_start = 0
        mw_end = width

    if LOG:
        print(f'method: FLAT_REGION ({method["FLAT_REGION_SIZE"]}, {method["FLAT_DIRECTION"]})')
        print(f'mh_start: {mh_start}')
        print(f'mh_end: {mh_end}')
        print(f'mw_start: {mw_start}')
        print(f'mw_end: {mw_end}')

    changed_image = image[mh_start:mh_end, mw_start:mw_end].copy()

    images = [changed_image]

    return images

# The main cutting point is center
def cutSmallRegion(image, method):
    numerator = int(method['SMALL_REGION_SIZE'].split('/')[0])
    dorminator = int(method['SMALL_REGION_SIZE'].split('/')[1])
    fraction = numerator / dorminator

    if dorminator == 0:
        print(f'cutSmallRegion() | dorminator is 0\n')
        exit()

    (height, width, _) = image.shape
    # print(f'ori_image shape: {image.shape}')
    # print(f'ori_image\n{image}')

    middle_height = height/2
    middle_width = width/2

    mh_start = int(middle_height - middle_height*fraction)
    mh_end = int(middle_height + middle_height*fraction)
    mw_start = int(middle_width - middle_width*fraction)
    mw_end = int(middle_width + middle_width*fraction)

    if LOG:
        print(f'method: SMALL_REGION ({method["SMALL_REGION_SIZE"]})')
        print(f'mh_start: {mh_start}')
        print(f'mh_end: {mh_end}')
        print(f'mw_start: {mw_start}')
        print(f'mw_end: {mw_end}')

    changed_image = image[mh_start:mh_end, mw_start:mw_end].copy()
    # print(f'ch_image shape: {changed_image.shape}')
    # print(f'ch_image\n{changed_image}')
    # print(f'END function()\n')
    images = [changed_image]

    return images

def divdeImageRegion(image, method=None):
    images = None

    if method is None:
        method = DEFAULT_METHOD

    if method['SMALL_REGION'] == True:
        images = cutSmallRegion(image, method)
    elif method['FLAT_REGION']  == True:
        images = cutFlatRegion(image, method)
    else:
        images = divideByCheck(image, method)

    return images

def saveImagesForExperiment(image_DIR):
    vidCps = getVideoCap()

    # save images for experiment
    for vid in range(len(vidCps)):
        for frame_number in range(TOTAL_FRAMES):
            succ_image, image = saveFrameImage(vidCps[vid], image_DIR, 0, frame_number, str(BPS[vid]))

def getGMSDofFrame(prep_ori_images, prep_comp_images, frame_number, metrics):
    start_time = time.time()

    GMSD = []
    for i in range(len(prep_ori_images)):
        # print(prep_ori_images[i].shape)
        GMSD.append(calculateGMSD(prep_ori_images[i], prep_comp_images[i]))

    avg_GMSD = sum(GMSD) / len(GMSD)

    elapsed_time = time.time() - start_time

    metric = {}

    metric["frame_number"] = frame_number
    metric["avg_GMSD"] = avg_GMSD
    metric["elapsed_time"] = elapsed_time

    metrics.append(metric)
    # metrics.put(metric)

def getResultOfGMSD(bps, image_DIR, method=None):
    metrics = []
    # metrics = Queue()
    threads = []
    isthread = False

    stime = time.time()

    for frame_number in range(TOTAL_FRAMES):
        ori_image = getFrameImage(str(BPS[-1]), frame_number, image_DIR)
        comp_image = getFrameImage(str(bps), frame_number, image_DIR)

        prep_ori_images = divdeImageRegion(ori_image, method)
        prep_comp_images = divdeImageRegion(comp_image, method)

        if (prep_ori_images is None) or (prep_comp_images is None):
            print(f'divideImageRegion() has a problem\n')
            print(f'images are None type')
            exit()

        if isthread == False:
            start_time = time.time()

            GMSD = []
            for i in range(len(prep_ori_images)):
                # print(prep_ori_images[i].shape)
                GMSD.append(calculateGMSD(prep_ori_images[i], prep_comp_images[i]))

            avg_GMSD = sum(GMSD) / len(GMSD)

            elapsed_time = time.time() - start_time

            metric = {}

            metric["frame_number"] = frame_number
            metric["avg_GMSD"] = avg_GMSD
            metric["elapsed_time"] = elapsed_time

            metrics.append(metric)
        else:
            t = Thread(target=getGMSDofFrame, args=(prep_ori_images, prep_comp_images, frame_number, metrics,))
            t.start()
            threads.append(t)

    if isthread:
        for t in threads:
            t.join()

        # mm = []

        # while True:
        #     m = metrics.get()
        #     mm.append(m)
        #     if metrics.empty():
        #         break

        # metrics = mm

    etime = time.time() - stime

    print(f'isThread: {isthread}')
    print(f'bps: {bps}')
    print(f'total frames: {TOTAL_FRAMES}')
    print(f'elapsed time: {etime}\n')

    return metrics

def createDir(requestedDIR):
    try:
        if not os.path.exists(requestedDIR):
            os.makedirs(requestedDIR)
    except OSError:
        print(f'Error: Creating directory. - {requestedDIR}')
        print(f'Exit program')
        exit()

def writeResultOfGMSD(data, f):
    try:
        f.write(f'frame_number,')
        for i in range(len(data)-1):
            f.write(f'{data[i]["frame_number"]},')
        f.write(f'{data[-1]["frame_number"]}\n')

        f.write(f'avg_GMSD,')
        gmsd = []
        for i in range(len(data)-1):
            gmsd.append(data[i]["avg_GMSD"])
            f.write(f'{data[i]["avg_GMSD"]},')
        f.write(f'{data[-1]["avg_GMSD"]}\n')
        gmsd.append(data[-1]["avg_GMSD"])

        etime = []
        f.write(f'elapsed_time,')
        for i in range(len(data)-1):
            etime.append(data[i]["elapsed_time"])
            f.write(f'{data[i]["elapsed_time"]},')
        f.write(f'{data[-1]["elapsed_time"]}\n')
        etime.append(data[-1]["elapsed_time"])

    except Exception as err:
        print(f'file write function err: \n{traceback.format_exc()}')

    f.write(f'\n')

    print(f'avg_GMSD: {sum(gmsd) / len(gmsd)}')
    print(f'elapsed_time: {sum(etime) / len(etime)}')

def saveResultOfGMSD(data, file_name, default_DIR=None):
    # PART: search default directory
    if default_DIR is None:
        default_DIR = os.getcwd()
        default_DIR = default_DIR + DIR_NAME
    createDir(default_DIR)

    # PART: file write function 
    f = open(default_DIR + file_name, 'w')
    writeResultOfGMSD(data, f)
    f.close()

    print(f'The file is saved as {file_name}\n')

def makeFileName(bps, method=None):
    if method is None:
        method = DEFAULT_METHOD

    if method['SMALL_REGION'] == True:
        numerator = method['SMALL_REGION_SIZE'].split('/')[0]
        dorminator = method['SMALL_REGION_SIZE'].split('/')[1]
        return bps + 'st' + numerator + '_' + dorminator + '.csv'
    elif method['FLAT_REGION'] == True:
        numerator = method['FLAT_REGION_SIZE'].split('/')[0]
        dorminator = method['FLAT_REGION_SIZE'].split('/')[1]
        if method['FLAT_DIRECTION'] == 'VERTICLE':
            abb = 'v'
        else:
            abb = 'h'
        return bps + 'ft' + numerator + '_' + dorminator + '_' + abb + '.csv'
    else:
        return bps + 'ct' + method['CHECK_REGION_SIZE'] + '.csv'

if __name__ == "__main__":
    # PART: create Image Directory
    current_DIR = os.getcwd()
    image_DIR = current_DIR + IMAGE_DIR_NAME
    createDir(image_DIR)

    # PART: save experimental images with varios bitrates
    #       if the images are aleady created, comment this code
    # saveImagesForExperiment(image_DIR)

    # PART: save result of GMSD with bps
    for i in range(len(BPS)):
        bps = BPS[i] # This is a video with 800Kbps 

        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/1', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '1x1', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'VERTICLE', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/16' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # # ############################################################

        # # # PART: save result of GMSD with bps
        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/2', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '2x2', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'VERTICLE', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/32' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # # #############################################################

        # # # PART: save result of GMSD with bps
        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/4', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '4x4', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'VERTICLE', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/64' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # # #############################################################

        # # # PART: save result of GMSD with bps
        # # method = {
        # #     'SMALL_REGION' : False,
        # #     'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
        # #     'CHECK_REGION' : False,
        # #     'CHECK_REGION_SIZE' : '8x8', # check region size ex) 2x2, 4x4 (row by column)
        # #     'FLAT_REGION' : True,
        # #     'FLAT_DIRECTION' : 'VERTICLE', # VERTICLE (full height size) or HORIZONTAL (full width size)
        # #     'FLAT_REGION_SIZE' : '1/8' # flat region size ex) 1/2, 1/4 (num by dom)
        # # }

        # # metrics = getResultOfGMSD(bps, image_DIR, method)

        # # file_name = makeFileName(str(bps), method)
        # # saveResultOfGMSD(metrics, file_name)
        # # #############################################################

        # # # PART: save result of GMSD with bps
        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '16x16', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'HORIZONTAL', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/16' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # # #############################################################

        # # PART: save result of GMSD with bps
        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '32x32', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'HORIZONTAL', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/32' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # #############################################################

        # # PART: save result of GMSD with bps
        # method = {
        #     'SMALL_REGION' : False,
        #     'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
        #     'CHECK_REGION' : False,
        #     'CHECK_REGION_SIZE' : '64x64', # check region size ex) 2x2, 4x4 (row by column)
        #     'FLAT_REGION' : True,
        #     'FLAT_DIRECTION' : 'HORIZONTAL', # VERTICLE (full height size) or HORIZONTAL (full width size)
        #     'FLAT_REGION_SIZE' : '1/64' # flat region size ex) 1/2, 1/4 (num by dom)
        # }

        # metrics = getResultOfGMSD(bps, image_DIR, method)

        # file_name = makeFileName(str(bps), method)
        # saveResultOfGMSD(metrics, file_name)
        # #############################################################

        # PART: save result of GMSD with bps
        method = {
            'SMALL_REGION' : False,
            'SMALL_REGION_SIZE' : '1/8', # small region size ex) 1/2, 1/4 (num by dom)
            'CHECK_REGION' : True,
            'CHECK_REGION_SIZE' : '4x4', # check region size ex) 2x2, 4x4 (row by column)
            'FLAT_REGION' : False,
            'FLAT_DIRECTION' : 'HORIZONTAL', # VERTICLE (full height size) or HORIZONTAL (full width size)
            'FLAT_REGION_SIZE' : '1/8' # flat region size ex) 1/2, 1/4 (num by dom)
        }

        metrics = getResultOfGMSD(bps, image_DIR, method)

        file_name = makeFileName(str(bps), method)
        saveResultOfGMSD(metrics, file_name)
        #############################################################
