#!/usr/bin/env python

import roslib
import rospy
from geometry_msgs.msg import Twist
from kobuki_msgs.msg import Led
from kobuki_msgs.msg import ButtonEvent
from kobuki_msgs.msg import BumperEvent
import cv2
import copy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from cmvision.msg import Blobs, Blob
import math
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion
from std_msgs.msg import Empty


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
x = 0.0
y = 0.0
degree = 0.0
firstRedBall = 0.0
firstSame = 0.0

#step number = which step we are trying to solve / angles we need to get.
stepNumber = 0

def resetter():
        pub = rospy.Publisher('/mobile_base/commands/reset_odometry', Empty,
                queue_size=10)
        while pub.get_num_connections() == 0:
                pass
        pub.publish(Empty())

def odomCallback(data):
        global command, bumper, pub, x , y, degree
           # Convert quaternion to degree
        q = [data.pose.pose.orientation.x,
                data.pose.pose.orientation.y,
                data.pose.pose.orientation.z,
                data.pose.pose.orientation.w]
        roll, pitch, yaw = euler_from_quaternion(q)
        # roll, pitch, and yaw are in radian
        degree = yaw * 180 / math.pi
        x = data.pose.pose.position.x
        y = data.pose.pose.position.y
	
	# First step, trying to get the angle from the start position before we move 1.5 meters
	if(stepNumber == 0):
		same = 5
	msg = "(%.6f,%.6f) at %.6f degree." % (x, y, degree)
        rospy.loginfo(msg)

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
    global colorImage, led,  isColorImageReady, blobsInfo, isBlobsInfoReady, pub, bumper, command, pub1, x, y, degree, stepNumber, firstRedBall, firstSame
    rospy.init_node('showBlobs', anonymous=True)
    rospy.Subscriber("/blobs", Blobs, updateBlobsInfo)
    rospy.Subscriber("/v4l/camera/image_raw", Image, updateColorImage)
    rospy.Subscriber('/mobile_base/events/bumper', BumperEvent, bumperCallback)
    rospy.Subscriber('/mobile_base/events/button', ButtonEvent, buttonCallback)
    bridge = CvBridge()
    cv2.namedWindow("Blob Location")
    rospy.Subscriber('/odom', Odometry, odomCallback)

    resetter()
    while not rospy.is_shutdown() and (not isBlobsInfoReady or not isColorImageReady):
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
	secondRotate = 0.0
#	resetter()
	if(bumper != False):
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
			cv2.rectangle(color_image, (b.left, b.top), (b.right, b.bottom), (0,255,0), 2)
			if(largestBlob == None):
				largestBlob = b
				largestBlobSize = b.right - b.left
			elif((b.right - b.left) > largestBlobSize):
				largestBlog = b
		
			
			#print(str(cv2.rectangle))
		if(firstRedBall == 0.0):
			if(largestBlob != None):	
				if(largestBlob.x < lowestMiddleVar):
					errorNumber = lowestMiddleVar - largestBlob.x
					outputNumber = .04 * errorNumber
					if(outputNumber > 1.0):
						outputNumber = 1.0
					command.linear.x = 0.0
					command.linear.y = 0.0
					command.angular.y = 0.2
					command.angular.z = outputNumber
					pub.publish(command)
				elif(largestBlob.x > highestMiddleVar):
			        	errorNumber = largestBlob.x - highestMiddleVar
                                	outputNumber = .04 * errorNumber
					outputNumber = outputNumber * -1.0
                                	if(outputNumber < -1.0):
                                        	outputNumber = -1.0
					command.linear.x = 0.0
					command.linear.y = 0.0
					command.angular.y = -0.2
					command.angular.z = outputNumber
					pub.publish(command)
				elif(largestBlob.x >= lowestMiddleVar and largestBlob.x <= highestMiddleVar):
					command.linear.x = 0.0
					command.linear.y = 0.0
					command.angular.y = 0.0
					command.angular.z = 0.0
					pub.publish(command)
					firstRedBall = degree
					resetter()
					print(str(largestBlob.x))
					print(str(degree))
				#print(largestBlob)
				#print bumper
			else:
				print("no large blob")
				#bumper = False
				led.value = 1
				pub1.publish(led) 
				command.linear.x = 0.0
				command.linear.y = 0.0
				command.angular.y = 0.0
				command.angular.z = 0.0
        			pub.publish(command)
		else:
			#if the red ball has already been collected, (first time)
			if(firstSame == 0.0 and secondRotate == 0.0):
				rotateAmount = firstRedBall + 90.0
			 	if(rotateAmount > 180.0):
					rotateAmount - 180.0
				elif(rotateAmount < 180.0):
					rotateAmount + 180.0
				if(degree < rotateAmount):
					command.angular.y = -20
					command.angular.z = -0.7 
					pub.publish(command)
					#firstSame = 1.0
					#rospy.sleep(2.0)
					print("currentdegree: " + str(degree) + " firstRedBall + 90.0 " + str(firstRedBall + 90.0)) 
				else:
					command.angular.y = 0.0
					command.angular.z = 0.0
					pub.publish(command)
					secondRotate = 1.0
					firstSame = 1.0
					
			#bumper = False
			#rospy.sleep(1.0)
			#bumper = False
	else:
		command.linear.x = 0.0
		command.linear.y = 0.0
		command.angular.y = 0.0 
		command.angular.z = 0.0
		pub.publish(command)
	cv2.imshow("Color Image", color_image)
        cv2.waitKey(1)
#	print("bumper:" + str(bumper))
def findX(N, alpha, theta, phi):
	b = N * math.tan(theta)
	a = N * math.tan(theta + phi) - N * math.tan(theta)
	x = (a+b) / (tan(90-alpha))


if __name__ == '__main__':
    main()