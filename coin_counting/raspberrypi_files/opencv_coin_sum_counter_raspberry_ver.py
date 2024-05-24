import cv2
import cvzone
import numpy as np
import pyttsx3
import RPi.GPIO as GPIO
from cvzone.ColorModule import ColorFinder
from picamera2 import Picamera2

# Prepare the setup of the buttons
# There are two buttons that will be used for speaking the amount and total coins
# We will be using BCM since we will follow the RPi.GPIO guide for pins
# BCM = GPIO2... etc / BOARD = PIN3... etc
buttonSpeakTotalCoins = 2
buttonSpeakTotalMoney = 3
GPIO.setmode(GPIO.BCM)
GPIO.setup(buttonSpeakTotalCoins, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buttonSpeakTotalMoney, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Since we are using Raspberry Pi Camera Module 2, we will be using PiCamera2 function
# We will be setting the resolution to 640x480 since it gives the system 90+ FPS
# We will be also set the color mode RGB888 for the camera to detect true colors
piCam = Picamera2()
piCam.preview_configuration.main.size=(640,480)
piCam.preview_configuration.main.format="RGB888"
piCam.preview_configuration.align()
piCam.configure("preview")
piCam.start()

# Initializes the PYTTSX library for speaking the amount of coins and total count
textSpeech = pyttsx3.init()

# Sets the custom colors for the coins
# In this case, it sets the color for orange
myColorFinder = ColorFinder(False)
hsvVals = {'hmin': 0, 'smin': 0, 'vmin': 145, 'hmax': 63, 'smax': 91, 'vmax': 255}

# Setting the global variables for the total sum of the coins and total count of each coins
totalMoney = 0
totalOnePeso = 0
totalFivePeso = 0
totalTenPeso = 0
totalTwentyPeso = 0

# Makes a pass statement disguised as a function
def empty(a):
    pass

# A user-defined function that speaks the total amount of coins being seen by the system
def speakAmount():
    global totalMoney
    if totalMoney == 0:
        textSpeech.say("No coins detected, please place some coins first.")
    else:
        textSpeech.say(f"{totalMoney} pesos")
    textSpeech.runAndWait()

# A user-defined function that speaks the total count of coins detected by the system
def speakTotalCoins():
    global totalOnePeso
    global totalFivePeso
    global totalTenPeso
    global totalTenPeso
    textSpeech.say(f"You have a total of {totalOnePeso} 1 peso coins, "
                   f"{totalFivePeso} 5 peso coins, "
                   f"{totalTenPeso} 10 peso coins, and "
                   f"{totalTwentyPeso} 20 peso coins.")
    textSpeech.runAndWait()

# A user-defined function that calls the function speakAmount in order to be operated by the first button
def buttonSpeakAmount(channel):
    speakAmount()

# A user-defined function that calls the function speakTotalCoins in order to be operated by the second button
def buttonSpeakCoinsTotal(channel):
    speakTotalCoins()

# Detects if the button was pressed, the functions under those callbacks will be operated by the system
GPIO.add_event_detect(buttonSpeakTotalMoney, GPIO.RISING, callback=buttonSpeakAmount, bouncetime=300)
GPIO.add_event_detect(buttonSpeakTotalCoins, GPIO.RISING, callback=buttonSpeakCoinsTotal, bouncetime=300)

# Setup the Threshold and Brightness Settings
# It has a default value of 15 and 235, respectively.
cv2.namedWindow("Settings")
cv2.resizeWindow("Settings", 640, 240)
cv2.createTrackbar("Threshold1", "Settings", 15, 255, empty)
cv2.createTrackbar("Threshold2", "Settings", 230, 255, empty)

# A user-defined function that pre-processed the image being streamed by the RPi Camera
def preProcessing(img):
    imgPre = cv2.GaussianBlur(img, (5, 5), 3)
    thresh1 = cv2.getTrackbarPos("Threshold1", "Settings")
    thresh2 = cv2.getTrackbarPos("Threshold2", "Settings")
    imgPre = cv2.Canny(imgPre, thresh1, thresh2)
    kernel = np.ones((3, 3), np.uint8)
    imgPre = cv2.dilate(imgPre, kernel, iterations=1)
    imgPre = cv2.morphologyEx(imgPre, cv2.MORPH_CLOSE, kernel)

    return imgPre

# Main loop for the camera stream and image recognition processes
try:
    while True:
        # Setup the camera and contours for getting the edges of the coins
        img = piCam.capture_array()
        imgPre = preProcessing(img)
        imgContours, conFound = cvzone.findContours(img, imgPre, minArea=20)

        # Initializes the global variables for counting and amount of the coins
        totalMoney = 0
        totalOnePeso = 0
        totalFivePeso = 0
        totalTenPeso = 0
        totalTwentyPeso = 0

        # Initializes the image stream for the system
        imgCount = np.zeros((480, 640, 3), np.uint8)

        # conFound = if there is contour found in the camera stream
        if conFound:
            for count, contour in enumerate(conFound):
                peri = cv2.arcLength(contour['cnt'], True)
                approx = cv2.approxPolyDP(contour['cnt'], 0.02 * peri, True)

                if len(approx) > 5:
                    area = contour['area']
                    x, y, w, h = contour['bbox']
                    imgCrop = img[y:y + h, x:x + w]
                    # cv2.imshow(str(count),imgCrop)
                    imgColor, mask = myColorFinder.update(imgCrop, hsvVals)
                    whitePixelCount = cv2.countNonZero(mask)
                    # print(whitePixelCount)
                    # print(area)

                    # Counting the sum of the coins
                    # Counting also the count of each coins
                    if area < 10200:
                        totalMoney += 1
                        totalOnePeso += 1
                    elif 10500 < area < 12300:
                        totalMoney += 5
                        totalFivePeso += 1
                    elif 12700 < area < 12900:
                        totalMoney += 10
                        totalTenPeso += 1

        cvzone.putTextRect(imgCount, f'P {totalMoney}', (100, 200), scale=10, offset=30, thickness=7)

        imgStacked = cvzone.stackImages([img, imgPre, imgContours, imgCount], 2, 1)
        cvzone.putTextRect(imgStacked, f'P {totalMoney}', (50, 50))

        cv2.imshow("Coin Counter", imgStacked)
        # cv2.imshow("imgColor", imgColor)
        cv2.waitKey(1)
finally:
    GPIO.cleanup()