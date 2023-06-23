import os
import cv2
import time
from skimage.metrics import structural_similarity as ssim

VIDEO_DIR = '/home/wins/MServer.conf/Videos/'
VIDEO_NAME = 'enter-video-du8min'

BPS_400 = '_400_dashinit.mp4'
BPS_800 = '_800_dashinit.mp4'
BPS_1200 = '_1400_dashinit.mp4'
BPS_1600 = '_2000_dashinit.mp4'\

vidcap = cv2.VideoCapture()

def compareSSIM(image_original, image_compare):
	img1 = cv2.imread(image_original)
	img2 = cv2.imread(image_compare)
	
	(H, W, d) = img1.shape
	img2 = cv2.resize(img2, (W, H))

	img1_color = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
	img2_color = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

	score, diff = ssim(img1_color, img2_color, full=True)
	diff = (diff * 255).astype("uint8")

	return score, diff


def getFrame(vidcap, sec=0, count=0, name='video'):
#	vidcap.set(cv2.CAP_PROP_POS_MSEC, sec*1000)
	vidcap.set(cv2.CAP_PROP_POS_FRAMES, count)
	hasFrames, image = vidcap.read()
	if hasFrames:
		image_name = name + '_' + str(count) + '.png'
		cv2.imwrite("images/server_images/" + image_name, image)

	return hasFrames, image_name

def getClientSSIM(client_image_name, frame_number):
	vidCp_1600 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1600)
	succ1600, img1600 = getFrame(vidCp_1600, 0, frame_number, BPS_1600)
	score_v1600, diff_v1600 = compareSSIM('images/server_images/' + img1600,'images/' + client_image_name)

	return f'{score_v1600:.5f}'
	
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
		score_v1600, diff_v1600 = compareSSIM('images/server_images/' + img1600, 'images/server_images/' + img1600)
		score_v1200, diff_v1200 = compareSSIM('images/server_images/' + img1600, 'images/server_images/' + img1200)
		score_v800, diff_v800 = compareSSIM('images/server_images/' + img1600, 'images/server_images/' + img800)
		score_v400, diff_v400 = compareSSIM('images/server_images/' + img1600, 'images/server_images/' + img400)
		

		print(f'SSIM = {score_v1600:.5f}')
		print(f'SSIM = {score_v1200:.5f}')
		print(f'SSIM = {score_v800:.5f}')
		print(f'SSIM = {score_v400:.5f}')
		

		# f = open("enter-video-du8min_SSIM.txt", 'w')
		# f.write(f'original: 1600bps\n')
		# f.write(f'1600 vs 1600: {score_v1600:.5f}\n')
		# f.write(f'1600 vs 1200: {score_v1200:.5f}\n')
		# f.write(f'1600 vs 800: {score_v800:.5f}\n')
		# f.write(f'1600 vs 400: {score_v400:.5f}\n')
		
		# f.close()

	else:
		print('getFrame is failed')

	print("Elapsed time: ", time.time() - start)


