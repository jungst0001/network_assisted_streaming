import cv2
import numpy as np
import time
import os
import cserverConfig
from threading import Lock 
from scipy import signal
 
VIDEO_DIR = cserverConfig.VIDEO_DIR
VIDEO_NAME = cserverConfig.VIDEO_NAME

BPS_400 = cserverConfig.BPS_400
BPS_800 = cserverConfig.BPS_800
BPS_1200 = cserverConfig.BPS_1200
BPS_1600 = cserverConfig.BPS_1600

# vidcap = cv2.VideoCapture()
cvLocks = {}
_lockforLock = Lock()
_LOG = '[calculateGMSD]'

def _getLock(chunkMP4):
    global cvLocks
    for key in cvLocks.keys():
        if key == chunkMP4:
            return cvLocks[key]

    return None

def _getServerImageName(name, frame_number):
    return f'{cserverConfig.LOCAL_DIR}images/server_images/{name}_{frame_number}.jpeg'

def getFrame(vidcap, frame_number, count=0, name='video'):
#   vidcap.set(cv2.CAP_PROP_POS_MSEC, sec*1000)
    vidcap.set(cv2.CAP_PROP_POS_FRAMES, count)
    hasFrames, image = vidcap.read()
    # image_name = name + '_' + str(count) + '.jpeg' # .png to .jpeg
    # image_name = f'{name}_{frame_number}.jpeg' # .png to .jpeg
    image_name = _getServerImageName(name, frame_number)

    if hasFrames:
        # print(f'[calculateGMSD] vidcap has frame')
        # [cv2.IMWRITE_JPEG_QUALITY, 95] (default is 95, high quality:100)
        cv2.imwrite(image_name, image, [cv2.IMWRITE_JPEG_QUALITY, 50])

    return hasFrames, image_name

def _recal_frame_number(frame_number, frame_rate, chunk_unit=2):
    remain = frame_number % (frame_rate * chunk_unit)

    if remain == 0:
        remain = frame_rate * chunk_unit

    return remain

def _getClientGMSD(server_image_name, client_image_name):
    ori_img = cv2.imread(server_image_name, cv2.IMREAD_COLOR)
    dist_img = cv2.imread(f'{cserverConfig.LOCAL_DIR}images/{client_image_name}', cv2.IMREAD_COLOR)
    gmsd_score = calculateGMSD(ori_img, dist_img)

    return f'{gmsd_score:.5f}'

def getClientGMSD(client_image_name, frame_number, frame_rate, chunkMP4, currentQuality):
    server_image_name = _getServerImageName(currentQuality, frame_number)
    isServerImage = os.path.isfile(server_image_name)

    global _lockforLock
    global cvLocks

    _lockforLock.acquire()
    lock = _getLock(chunkMP4)
    if lock is None:
        lock = Lock()
        cvLocks[chunkMP4] = lock
    _lockforLock.release()

    if not isServerImage:
        while lock.locked():
            time.sleep(0.2)
            if os.path.isfile(server_image_name):
                lock.acquire()
                gmsd = _getClientGMSD(server_image_name, client_image_name)
                lock.release()
                return gmsd

        lock.acquire()
        chunkVidCp = cv2.VideoCapture(chunkMP4)

        recal_frame_number = _recal_frame_number(frame_number, frame_rate)
        hasFrames, server_image_name = getFrame(chunkVidCp, frame_number, recal_frame_number, currentQuality)
        i = 0
        while not hasFrames:
            time.sleep(0.2)
            hasFrames, server_image_name = getFrame(chunkVidCp, frame_number, recal_frame_number, currentQuality)

            if not chunkVidCp.isOpened():
                chunkVidCp = cv2.VideoCapture(chunkMP4)
            i += 1

            if i > 5:
                # print(f'{_LOG} | frame number: {frame_number}')
                # print(f'{_LOG} | frame number: {frame_rate}')
                # print(f'{_LOG} | recal_frame_number: {recal_frame_number}')
                # print(f'{_LOG} | chunkMP4: {chunkMP4}')
                # print(f'{_LOG} | currentQuality: {currentQuality}')
                if chunkVidCp.isOpened():
                    chunkVidCp.release()
                lock.release()

                raise Exception
        if chunkVidCp.isOpened():
            chunkVidCp.release()
        lock.release()

    lock.acquire()
    gmsd = _getClientGMSD(server_image_name, client_image_name)
    lock.release()

    return gmsd

def calculateGMSD(image_original, image_compare):
    # ori_img = cv2.imread(image_original, cv2.IMREAD_COLOR)
    # dist_img = cv2.imread(image_compare, cv2.IMREAD_COLOR)
    ori_img = image_original
    dist_img = image_compare

    # (H, W, d) = ori_img.shape
    # dist_img = cv2.resize(dist_img, (W, H))

    (H, W, d) = dist_img.shape
    ori_img = cv2.resize(ori_img, (W, H))
     
    ori_img = cv2.cvtColor(ori_img, cv2.COLOR_BGR2GRAY)
    dist_img = cv2.cvtColor(dist_img, cv2.COLOR_BGR2GRAY)
     
    ori_img = np.float64(ori_img)
    dist_img = np.float64(dist_img)
     
    ave_kernal = np.array([[0.25, 0.25],
                           [0.25, 0.25]])
     
    ave_ori = signal.convolve2d(ori_img, ave_kernal, boundary='fill', mode='full')
    (M, N) = ave_ori.shape
    ave_ori = ave_ori[1:M, 1:N]
     
    ave_dist = signal.convolve2d(dist_img, ave_kernal, boundary='fill', mode='full')
    (M, N) = ave_dist.shape
    ave_dist = ave_dist[1:M, 1:N]
     
    ori_img = ave_ori[::2, ::2]
    dist_img = ave_dist[::2, ::2] 
     
    Prewitt_x = np.array([[1, 0, -1],
                          [1, 0, -1],
                          [1, 0, -1]])/3
    Prewitt_x = np.float64(Prewitt_x)
    Prewitt_y = np.transpose(Prewitt_x)
     
    ori_GM_x = signal.convolve2d(ori_img, Prewitt_x, boundary='fill', mode='full')
    (M, N) = ori_GM_x.shape
    ori_GM_x = ori_GM_x[1:M-1, 1:N-1]
     
    ori_GM_y = signal.convolve2d(ori_img, Prewitt_y, boundary='fill', mode='full')
    (M, N) = ori_GM_y.shape
    ori_GM_y = ori_GM_y[1:M-1, 1:N-1]
     
    ori_GM = np.sqrt(np.square(ori_GM_x) + np.square(ori_GM_y))
     
    dist_GM_x = signal.convolve2d(dist_img, Prewitt_x, boundary='fill', mode='full')
    (M, N) = dist_GM_x.shape
    dist_GM_x = dist_GM_x[1:M-1, 1:N-1]
     
    dist_GM_y = signal.convolve2d(dist_img, Prewitt_y, boundary='fill', mode='full')
    (M, N) = dist_GM_y.shape
    dist_GM_y = dist_GM_y[1:M-1, 1:N-1]
     
    dist_GM = np.sqrt(np.square(dist_GM_x) + np.square(dist_GM_y))
     
    T = 170
    quality_map = (2*ori_GM*dist_GM + 170)/(np.square(ori_GM) + np.square(dist_GM) + T)
     
    score = 1 - np.std(quality_map)
    
    return score

if __name__ == "__main__":  
    server_image_name = _getServerImageName(2, 97)
    client_image_name = f'10.0.0.1-595-97.jpeg'
    print(os.path.isfile(client_image_name))
    print(_getClientGMSD(server_image_name, client_image_name))