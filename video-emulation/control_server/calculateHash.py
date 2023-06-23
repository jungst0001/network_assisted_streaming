import cv2
import numpy as np
import time
from scipy import signal
from PIL import Image
import imagehash
 
VIDEO_DIR = '/home/wins/MServer.conf/Videos/'
VIDEO_NAME = 'enter-video-du8min'

BPS_400 = '_400_dashinit.mp4'
BPS_800 = '_800_dashinit.mp4'
BPS_1200 = '_1400_dashinit.mp4'
BPS_1600 = '_2000_dashinit.mp4'

vidcap = cv2.VideoCapture()

def getFrame(vidcap, sec=0, count=0, name='video'):
#   vidcap.set(cv2.CAP_PROP_POS_MSEC, sec*1000)
    vidcap.set(cv2.CAP_PROP_POS_FRAMES, count)
    hasFrames, image = vidcap.read()
    if hasFrames:
        image_name = name + '_' + str(count) + '.png'
        cv2.imwrite("images/server_images/" + image_name, image)

    return hasFrames, image_name

def getClientHammingDistanceOfImageHash(client_image_name, frame_number):
    vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)
    succ1600, img1600 = getFrame(vidCp_1600, 0, frame_number, BPS_1600)
    score_v1600 = calculateHammingDistanceOfImageHash('images/server_images/' + img1600,'images/' + client_image_name)

    return f'{score_v1600}'

def calculateHammingDistanceOfImageHash(image_original, image_compare):
	h_original = imagehash.average_hash(Image.open(image_original))
	h_compare = imagehash.average_hash(Image.open(image_compare))
	
	hd = h_original - h_compare
    
	return hd

if __name__ == "__main__":  
    start = time.time()

    vidCp_400 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_400)
    vidCp_800 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_800)
    vidCp_1200 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1200)
    vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)


    succ1600, img1600 = getFrame(vidCp_1600, 0, 0, BPS_1600)
    succ1200, img1200 = getFrame(vidCp_1200, 0, 0, BPS_1200)
    succ800, img800 = getFrame(vidCp_800, 0, 0, BPS_800)
    succ400, img400 = getFrame(vidCp_400, 0, 0, BPS_400)
    

    if (succ1600 is True) and (succ800 is True) and (succ400 is True) and (succ1200 is True):
        score_v1600 = calculateHammingDistanceOfImageHash('images/server_images/' + img1600, 'images/server_images/' + img1600)
        score_v1200 = calculateHammingDistanceOfImageHash('images/server_images/' + img1600, 'images/server_images/' + img1200)
        score_v800 = calculateHammingDistanceOfImageHash('images/server_images/' + img1600, 'images/server_images/' + img800)
        score_v400 = calculateHammingDistanceOfImageHash('images/server_images/' + img1600, 'images/server_images/' + img400)
        

        print(f'hd = {score_v1600}')
        print(f'hd = {score_v1200}')
        print(f'hd = {score_v800}')
        print(f'hd = {score_v400}')
        

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
