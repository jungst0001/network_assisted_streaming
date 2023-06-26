import cv2
import numpy as np
import time
import cserverConfig
from scipy import signal
 
VIDEO_DIR = cserverConfig.VIDEO_DIR
VIDEO_NAME = cserverConfig.VIDEO_NAME

BPS_400 = cserverConfig.BPS_400
BPS_800 = cserverConfig.BPS_800
BPS_1200 = cserverConfig.BPS_1200
BPS_1600 = cserverConfig.BPS_1600

vidcap = cv2.VideoCapture()

def getFrame(vidcap, sec=0, count=0, name='video'):
#   vidcap.set(cv2.CAP_PROP_POS_MSEC, sec*1000)
    vidcap.set(cv2.CAP_PROP_POS_FRAMES, count)
    hasFrames, image = vidcap.read()
    if hasFrames:
        image_name = name + '_' + str(count) + '.jpeg' # .png to .jpeg
        # [cv2.IMWRITE_JPEG_QUALITY, 95] (default is 95, high quality:100)
        cv2.imwrite("images/server_images/" + image_name, image, [cv2.IMWRITE_JPEG_QUALITY, 50])

    return hasFrames, image_name

# Old_Version
# def getClientGMSD(client_image_name, frame_number):
#     vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)
#     succ1600, img1600 = getFrame(vidCp_1600, 0, frame_number, BPS_1600)
#     score_v1600 = calculateGMSD('images/server_images/' + img1600,'images/' + client_image_name)

#     return f'{score_v1600:.5f}'

def getOriAndCompImage(client_image_name, frame_number):
    vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)
    succ1600, img1600 = getFrame(vidCp_1600, 0, frame_number, BPS_1600)

    ori_img = cv2.imread('images/server_images/' + img1600, cv2.IMREAD_COLOR)
    dist_img = cv2.imread('images/' + client_image_name, cv2.IMREAD_COLOR)

    return ori_img, dist_img

def getClientGMSD(client_image_name, frame_number, chunkMP4, currentQuality):
    chunkVidCp = cv2.VideoCapture(chunkMP4)
    _, server_image_name = getFrame(chunkVidCp, 0, frame_number, currentQuality)

    ori_img = cv2.imread('images/server_images/' + server_image_name, cv2.IMREAD_COLOR)
    dist_img = cv2.imread('images/' + client_image_name, cv2.IMREAD_COLOR)
    gmsd_score = calculateGMSD(ori_img, dist_img)

    return f'{gmsd_score:.5f}'

def calculateGMSD(image_original, image_compare):
    # ori_img = cv2.imread(image_original, cv2.IMREAD_COLOR)
    # dist_img = cv2.imread(image_compare, cv2.IMREAD_COLOR)
    ori_img = image_original
    dist_img = image_compare

    (H, W, d) = ori_img.shape
    dist_img = cv2.resize(dist_img, (W, H))
     
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
    start = time.time()

    vidCp_400 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_400)
    vidCp_800 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_800)
    vidCp_1200 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1200)
    vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)


    succ1600, img1600 = getFrame(vidCp_1600, 0, 620, BPS_1600)
    succ1200, img1200 = getFrame(vidCp_1200, 0, 620, BPS_1200)
    succ800, img800 = getFrame(vidCp_800, 0, 620, BPS_800)
    succ400, img400 = getFrame(vidCp_400, 0, 620, BPS_400)
    

    if (succ1600 is True) and (succ800 is True) and (succ400 is True) and (succ1200 is True):
        score_v1600 = calculateGMSD('images/server_images/' + img1600, 'images/server_images/' + img1600)
        score_v1200 = calculateGMSD('images/server_images/' + img1600, 'images/server_images/' + img1200)
        score_v800 = calculateGMSD('images/server_images/' + img1600, 'images/server_images/' + img800)
        score_v400 = calculateGMSD('images/server_images/' + img1600, 'images/server_images/' + img400)
        

        print(f'GMSD = {score_v1600}')
        print(f'GMSD = {score_v1200}')
        print(f'GMSD = {score_v800}')
        print(f'GMSD = {score_v400}')
        

        # f = open("enter-video-du8min_GMSD.txt", 'w')
        # f.write(f'original: 2000bps\n')
        # f.write(f'2000 vs 2000: {score_v1600}\n')
        # f.write(f'2000 vs 1400: {score_v1200}\n')
        # f.write(f'2000 vs 800: {score_v800}\n')
        # f.write(f'2000 vs 400: {score_v400}\n')
        
        # f.close()

    else:
        print('getFrame is failed')

    print("Elapsed time: ", time.time() - start)