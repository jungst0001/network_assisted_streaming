import cv2
import numpy as np
import time
from scipy import signal
from skimage.measure import compare_ssim
import os

# image opencv2 compression: jpeg-based 80 ([0, 100])
# image capture compression ratio: javascript canvas-based 0.8 ([0, 1])
# higher value, higher quality

vidcap = cv2.VideoCapture()

def calculateSSIM(image_original, image_compare):
    img1 = cv2.imread(image_original)
    img2 = cv2.imread(image_compare)
    
    (H, W, d) = img1.shape
    img2 = cv2.resize(img2, (W, H))

    img1_color = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2_color = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    score, diff = compare_ssim(img1_color, img2_color, full=True)
    diff = (diff * 255).astype("uint8")

    return score

def getOriAndCompImage(client_image_name, server_image_name):
    client_img = cv2.imread(client_image_name, cv2.IMREAD_COLOR)
    server_img = cv2.imread(server_image_name, cv2.IMREAD_COLOR)

    return client_img, server_img

def calculateGMSD(image_original, image_compare):
    ori_img = cv2.imread(image_original, cv2.IMREAD_COLOR)
    dist_img = cv2.imread(image_compare, cv2.IMREAD_COLOR)
    # ori_img = image_original
    # dist_img = image_compare

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

def getImageName():
    cnameList = os.listdir('.')
    snameList = os.listdir('./server_images')

    imageName_peer = []

    for fname in cnameList:
        extention = fname.split('.')[-1]
        if extention != 'jpeg':
            continue

        name = fname.split('-')

        ip = name[0]
        bitrate = int(name[1])
        if bitrate == 1401:
            bitrate = 1400

        frame_number = name[2]
        frame_number = frame_number[:-5]

        sname = f'_{bitrate}_dashinit.mp4_{frame_number}.jpeg'
        if sname in snameList:
            peer = (fname, 'server_images/' + sname)
            imageName_peer.append(peer)
        else:
            print(f'no server image name: {sname}')

    return imageName_peer

def testPerceptualQuality():
    # start = time.time()

    imageName_peer = getImageName()

    metrics = {}
    frameList = {}

    for cname, sname in imageName_peer:
        bitrate = cname.split('-')[1]
        frame_number = cname.split('-')[2]
        frame_number = frame_number[:-5]

        # client_img, server_img = getOriAndCompImage(cname, sname)
        gmsd = calculateGMSD(cname, sname)
        ssim = calculateSSIM(cname, sname)
        metric = [gmsd, ssim]

        try:
            metrics[bitrate].append(metric)
            frameList[bitrate].append(frame_number)
        except KeyError:
            metrics[bitrate] = []
            frameList[bitrate] = []
            metrics[bitrate].append(metric)
            frameList[bitrate].append(frame_number)

    # f = open('summary.csv', 'w')

    for bitrate in metrics.keys():
        metrics[bitrate] = np.array(metrics[bitrate])

        print(f'{bitrate} video capture')
        # print(metrics[bitrate])
        for i in range(len(metrics[bitrate])):
            print(f'{metrics[bitrate][i]} | {frameList[bitrate][i]}')
        print(f'\tGSMD | SSIM')
        print(f'mean: {np.mean(metrics[bitrate], axis=0)}')
        print(f'max: {np.max(metrics[bitrate], axis=0)}')
        print(f'min: {np.min(metrics[bitrate], axis=0)}')
        print(f'std: {np.std(metrics[bitrate], axis=0)}\n')

        # f.write()

    # f.close()

if __name__ == "__main__":  
    # testPerceptualQuality()

    compare_name = ['_2000_dashinit.mp4_620.jpeg',
        '_1400_dashinit.mp4_620.jpeg',
        '_800_dashinit.mp4_620.jpeg',
        '_400_dashinit.mp4_620.jpeg']

    source_name = '_2000_dashinit.mp4_620.jpeg'

    gmsd0 = calculateGMSD(source_name, compare_name[0])
    ssim0 = calculateSSIM(source_name, compare_name[0])

    gmsd1 = calculateGMSD(source_name, compare_name[1])
    ssim1 = calculateSSIM(source_name, compare_name[1])

    gmsd2 = calculateGMSD(source_name, compare_name[2])
    ssim2 = calculateSSIM(source_name, compare_name[2])

    gmsd3 = calculateGMSD(source_name, compare_name[3])
    ssim3 = calculateSSIM(source_name, compare_name[3])


    print(gmsd0, ssim0)
    print(gmsd1, ssim1)
    print(gmsd2, ssim2)
    print(gmsd3, ssim3)

