#!/usr/bin/env python

import roslib
import rospy
from geometry_msgs.msg import Twist
from kobuki_msgs.msg import Led
from kobuki_msgs.msg import ButtonEvent
from kobuki_msgs.msg import BumperEvent
from sensor_msgs.msg import Image
from struct import unpack
import cv2
import copy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from cmvision.msg import Blobs, Blob
import math
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

colorImage = Image()
isColorImageReady = False
blobsInfo = Blobs()
isBlobsInfoReady = False
pub = rospy.Publisher('kobuki_command', Twist, queue_size=10)
command = Twist()
bumper = True
pub1 = rospy.Publisher('/mobile_base/commands/led1', Led, queue_size=10)
pub2 = rospy.Publisher('/mobile_base/commands/led2', Led, queue_size=10)
led = Led()

depthData = Image()
isDepthReady = False
previousDistance = 0.0

def depthCallback(data):
	global depthData, isDepthReady
	depthData = data
	isDepthReady = True

def resetter():
        pub = rospy.Publisher('/mobile_base/commands/reset_odometry', Empty,
                queue_size=10)
        while pub.get_num_connections() == 0:
                pass
        pub.publish(Empty())


def bumperCallback(data):
    global pub, command, bumper, led
    if data.state == 1:
        command.linear.x = 0
        command.linear.y = 0
        command.linear.z = 0
        command.angular.z = 0
        command.angular.y = 0
	bumper = False
	led.value = 3
        pub.publish(command)
	pub1.publish(led)

def buttonCallback(data):
    global pub1, led, buttonGreen, command, bumper
    str = ""
    if data.state != 0:
        if data.button == 0:
                str = str + "Button 0 is "
                if bumper == True:
                        command.linear.x = 0
                        command.linear.y = 0
                        command.angular.z = 0
                        command.angular.y = 0
                        led.value = 3
                        bumper = False
                else:
                        led.value = 1
                        bumper = True
                pub1.publish(led)
        elif data.button == 1:
                str = str + "Button 1 is "
        else:
                str = str + "Button 2 is "

        if data.state == 0:
		str = str + "released."
        else:
                str = str + "pressed."
        rospy.loginfo(str)




def updateColorImage(data):
    global colorImage, isColorImageReady
    colorImage = data
    isColorImageReady = True

def updateBlobsInfo(data):
    global blobsInfo, isBlobsInfoReady
    blobsInfo = data
    isBlobsInfoReady = True

def main():
    global colorImage, led,  isColorImageReady, blobsInfo, isBlobsInfoReady, pub, bumper, command, pub1
    rospy.init_node('showBlobs', anonymous=True)
    rospy.Subscriber("/blobs", Blobs, updateBlobsInfo)
    rospy.Subscriber("/camera/depth/image", Image, depthCallback, queue_size=10)
    rospy.Subscriber('/mobile_base/events/bumper', BumperEvent, bumperCallback)
    rospy.Subscriber('/mobile_base/events/button', ButtonEvent, buttonCallback)
    bridge = CvBridge()
    cv2.namedWindow("Blob Location")

    while not rospy.is_shutdown() and (not isBlobsInfoReady or not isColorImageReady):
        print("we passed for some reason?")
	pass

    while not rospy.is_shutdown():
        try:
	   # command.angular.y = 0.5
 	   # command.angular.z = 10
	   # pub.publish(command)
            color_image = bridge.imgmsg_to_cv2(colorImage, "bgr8")
        except CvBridgeError, e:
            print e
            print "colorImage"

	if(bumper != False):
		print("samesamesame")
		led.value = 1
		pub1.publish(led)
        	blobsCopy = copy.deepcopy(blobsInfo)
		height = blobsCopy.image_height
		width = blobsCopy.image_width
		lowestMiddleVar = (width/2) - 50
		highestMiddleVar = (width/2) + 50
#		print(blobsCopy)
		largestBlob = None
		largestBlobSize = 0

		for b in blobsCopy.blobs:
			if b.name !=  "LightBlue":
				print("largestBlob is not bright green")
				continue
			cv2.rectangle(color_image, (b.left, b.top), (b.right, b.bottom), (0,255,0), 2)
			if(largestBlob == None):
				largestBlob = b
				largestBlobSize = b.right - b.left
			elif((b.right - b.left) > largestBlobSize):
				largestBlog = b
		
			
			#print(str(cv2.rectangle))
		if(largestBlob != None):
			print("we have a largestBlob")
			if(str(largestBlob.name) != "BrightGreen"):
				print("largestBlob is not bright green")
				#print("this is largets blob name:" + str(largestBlob.name))
				command.linear.x = 0.0
				command.linear.y = 0.0
				command.angular.z = 0.0
				command.angular.y = 0.0
				print "no more green"
			
			elif(largestBlob.x < lowestMiddleVar):
				print("largestblob is bright green")
				errorNumber = lowestMiddleVar - largestBlob.x
				outputNumber = .04 * errorNumber
				if(outputNumber > 1.0):
					outputNumber = 1.0
				command.linear.x = 0.2
				command.linear.y = 0.3
				command.angular.y = 0.2
				command.angular.z = outputNumber
				pub.publish(command)
			elif(largestBlob.x > highestMiddleVar):
			        errorNumber = largestBlob.x - highestMiddleVar
                                outputNumber = .04 * errorNumber
				outputNumber = outputNumber * -1.0
                                if(outputNumber < -1.0):
                                        outputNumber = -1.0
				command.linear.x = 0.2
				command.linear.y = 0.3
				command.angular.y = -0.2
				command.angular.z = outputNumber

				pub.publish(command)
			elif(largestBlob.x >= lowestMiddleVar and largestBlob.x <= highestMiddleVar):
				command.linear.x = 0.2
				command.linear.y = 0.3
				command.angular.y = 0.0
				command.angular.z = 0.0
				pub.publish(command)
			#print(largestBlob)
			#print bumper
		else:
			print("no large blob")
			bumper = False
			
			led.value = 1
			pub1.publish(led) 
			command.linear.x = 0.0
			command.linear.y = 0.0
			command.angular.y = 0.0
			command.angular.z = 0.0
        		pub.publish(command)
	else:
		command.linear.x = 0.0
		command.linear.y = 0.0
		command.angular.y = 0.0 
		command.angular.z = 0.0
		pub.publish(command)
	cv2.imshow("Color Image", color_image)
        cv2.waitKey(1)
#	print("bumper:" + str(bumper))

if __name__ == '__main__':
    main()
