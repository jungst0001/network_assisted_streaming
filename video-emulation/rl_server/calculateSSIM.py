import os
import cv2
from datetime import datetime
from skimage.metrics import structural_similarity as ssim

VIDEO_DIR = '/home/wins/jin/VideoDQN/Videos/'
VIDEO_NAME = 'enter-video-du8min'
BPS_200 = '_200_dashinit.mp4'
BPS_400 = '_400_dashinit.mp4'
BPS_800 = '_800_dashinit.mp4'
BPS_1500 = '_1500_dashinit.mp4'


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
	# print(f'hasFrames: {hasFrames}')
	if hasFrames:
		image_name = name + '_' + str(count) + '.png'
		cv2.imwrite("images/server_images/" + image_name, image)

	return hasFrames, image_name


def getClientSSIM(client_image_name, frame_number):
	vidCp_1500 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1500)
	succ1500, img1500 = getFrame(vidCp_1500, 0, frame_number, BPS_1500)
	score_v1500, diff_v1500 = compareSSIM('images/server_images/' + img1500,'images/' + client_image_name)

	return f'{score_v1500:.5f}'
	

if __name__ == "__main__":
	# vidCp_200 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_200)
	# vidCp_400 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_400)
	# vidCp_800 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_800)
	a = datetime.now()
	# vidCp_1500 = cv2.VideoCapture(VIDEO_DIR + VIDEO_NAME + BPS_1500)
	# # print(vidCp_1500)
	# # frame_size = (int(vidCp_1500.get(cv2.CAP_PROP_FRAME_WIDTH)),
	# # 	int(vidCp_1500.get(cv2.CAP_PROP_FRAME_HEIGHT)))
	# # print(frame_size)

	# succ1500, img1500 = getFrame(vidCp_1500, 0, 0, BPS_1500)
	# # succ800, img800 = getFrame(vidCp_800, 0, 0, BPS_800)
	# # succ400, img400 = getFrame(vidCp_400, 0, 0, BPS_400)
	# # succ200, img200 = getFrame(vidCp_200, 0, 0, BPS_200)
	# score_v1500, diff_v1500 = compareSSIM(img1500, img1500)
	# print(f'SSIM = {score_v1500:.5f}')
	getClientSSIM("192.168.0.15-474.png", 474)
	b = datetime.now()
	print(f'{(b-a).total_seconds()}')
	# if (succ1500 is True) and (succ800 is True) and (succ400 is True) and (succ200 is True):
	# 	score_v1500, diff_v1500 = compareSSIM(img1500, img1500)
	# 	score_v800, diff_v800 = compareSSIM(img1500, img800)
	# 	score_v400, diff_v400 = compareSSIM(img1500, img400)
	# 	score_v200, diff_v200 = compareSSIM(img1500, img200)

	# 	print(f'SSIM = {score_v1500:.5f}')
	# 	print(f'SSIM = {score_v800:.5f}')
	# 	print(f'SSIM = {score_v400:.5f}')
	# 	print(f'SSIM = {score_v200:.5f}')

	# 	f = open("enter-video-du8min_SSIM.txt", 'w')
	# 	f.write(f'original: 1500bps\n')
	# 	f.write(f'1500 vs 1500: {score_v1500:.5f}\n')
	# 	f.write(f'1500 vs 800: {score_v800:.5f}\n')
	# 	f.write(f'1500 vs 400: {score_v400:.5f}\n')
	# 	f.write(f'1500 vs 200: {score_v200:.5f}\n')
	# 	f.close()

	# else:
	# 	print('getFrame is failed')




