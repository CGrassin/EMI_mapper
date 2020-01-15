import imutils #pip3 install imutils
import time
import cv2 #sudo apt install opencv-data opencv-doc python-opencv && pip3 install opencv-contrib-python
from rtlsdr import RtlSdr # pip3 install pyrtlsdr
import scipy.signal
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter
import argparse

def gaussian_with_nan(U, sigma=7):
	"""Computes the gaussian blur of a numpy array with NaNs.
	"""
	np.seterr(divide='ignore', invalid='ignore')
	V=U.copy()
	V[np.isnan(U)]=0
	VV=gaussian_filter(V,sigma=sigma)

	W=0*U.copy()+1
	W[np.isnan(U)]=0
	WW=gaussian_filter(W,sigma=sigma)
	
	return VV/WW

def print_sdr_config(sdr):
	"""Prints the RTL-SDR configuration in the console.
	"""
	print("RTL-SDR config:")
	print("    * Using device",sdr.get_device_serial_addresses())
	print("    * Device opened:", sdr.device_opened)
	print("    * Center frequency:",sdr.get_center_freq(),"Hz")
	print("    * Sample frequency:",sdr.get_sample_rate(),"Hz")
	print("    * Gain:",sdr.get_gain(),"dB")
	print("    * Available gains:",sdr.get_gains())
	
def get_RMS_power(sdr):
	"""Measures the RMS power with a RTL-SDR.
	"""
	samples = sdr.read_samples(1024*4)
	freq,psd = scipy.signal.welch(samples,sdr.sample_rate/1e6,nperseg=512,return_onesided=0)
	return 10*np.log10(np.sqrt(np.mean(psd**2)))

# Thanks to https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
# for the tracking tutorial.
def main():
    print("Usage:")
    print("    * Press s to select the probe.")
    print("    * Press r to reset.")
    print("    * Press q to display the EMI map and exit.")
    print("Call with -h for help on the args.")
    		
    # parse args
    parser = argparse.ArgumentParser(description='EMI mapping with camera and RTL-SDR.')
    parser.add_argument('-c', '--camera', type=int, help='camera id (default=0)',default=0)
    parser.add_argument('-f', '--frequency', type=float, help='sets the center frequency on the SDR, in MHz (default: 300).',default=300)
    parser.add_argument('-g', '--gain', type=int, help='sets the SDR gain (default: 496).',default=496)
    args = parser.parse_args()
    
    # configure SDR device
    sdr = RtlSdr()
    sdr.sample_rate = 2.4e6
    sdr.center_freq = args.frequency * 1e6
    sdr.gain = args.gain
    sdr.set_agc_mode(0)
    #print_sdr_config(sdr)
    
    # read from specified webcam
    cap = cv2.VideoCapture(args.camera)
    if cap is None or not cap.isOpened():
    	   print('Error: unable to open video source: ', args.camera)
    else:
    	# wait some time for the camera to be ready
    	time.sleep(2.0)
    
    # initialize variables
    powermap = None
    firstFrame = None
    firstFrameMask = None
    
    # Init OpenCV object tracker objects
    tracker = cv2.TrackerCSRT_create()
    init_tracking_BB = None
    
    # loop while exit button wasn't pressed
    while True:
    	# grab the current frame
    	ret, frame = cap.read()
    
    	# if the frame could not be grabbed, then we have reached the end
    	# of the video
    	if ret == False or frame is None:
    		break
    
    	# resize the frame, convert it to grayscale, and blur it
    	frame = imutils.resize(frame, width=500)
    	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    	gray = cv2.GaussianBlur(gray, (11, 11), 0)
    
    	# if the first frame is None, initialize it
    	if firstFrame is None:
    		firstFrame = frame
    		firstFrameMask = gray
    		powermap = np.empty((len(frame),len(frame[0])))
    		powermap.fill(np.nan)
    		continue
    
    	# compute the absolute difference between the current frame and
    	# first frame
    	frameDelta = cv2.absdiff(firstFrameMask, gray)
    	thresh = cv2.threshold(frameDelta, 15, 255, cv2.THRESH_BINARY)[1]
    
    	# dilate the thresholded image to fill in holes, then find contours
    	# on thresholded image
    	thresh = cv2.dilate(thresh, None, iterations=2)
    	
    	# tracking and reading SDR
    	if init_tracking_BB is not None:
    		# grab the new bounding box coordinates of the object
    		(success, box) = tracker.update(thresh)
    
    		# check to see if the tracking was a success
    		if success:
    			(x, y, w, h) = [int(v) for v in box]
    			# print bounding box
    			cv2.rectangle(frame, (x, y), (x + w, y + h),
    				(0, 255, 0), 2)
    			# fill map
    			power = get_RMS_power(sdr)
    			print("RMS power",power,"dBm at",x+w/2,";",y+h/2)
    			powermap[int(y+h/4):int(y+h/4*3),int(x+w/4):int(x+w/4*3)] = power
    			
    	# show the frame (adding scanned zone overlay)
    	frame[:,:,2] = np.where(np.isnan(powermap),frame[:,:,2],255/2)
    	cv2.imshow("Frame", frame)
    	# debug only
    	#cv2.imshow("Thresh", thresh)
    	#cv2.imshow("Frame Delta", frameDelta)
    	
    	# handle keypresses
    	key = cv2.waitKey(1) & 0xFF
    	if key == ord("s") and init_tracking_BB is None:
    		# select the bounding box
    		init_tracking_BB = cv2.selectROI("Frame", frame, fromCenter=False,
    			showCrosshair=True)
    
    		# start OpenCV object tracker
    		tracker.init(thresh, init_tracking_BB)
    	elif key == ord("q"):
    		break
    	elif key == ord("r"):
    		firstFrame = None
    
    # gracefully free the resources
    sdr.close()
    cap.release()
    cv2.destroyAllWindows()
    
    # generate picture
    if init_tracking_BB is not None and powermap is not None and firstFrame is not None:
    	blurred = gaussian_with_nan(powermap, sigma=7)
    	plt.imshow(cv2.cvtColor(firstFrame, cv2.COLOR_BGR2RGB))
    	plt.imshow(blurred, cmap='hot', interpolation='nearest',alpha=0.55)
    	plt.axis('off')
    	plt.title("EMI map (min. "+"%.2f" % np.nanmin(powermap)+" dBm, max. "+"%.2f" % np.nanmax(powermap)+" dBm)")
    	plt.show()
    	# TODO : add distribution plot
    else:
    	print("Warning: nothing captured, nothing to do")
        
if __name__== "__main__":
  main()