#!/usr/bin/env python3
import math
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped

def yaw_to_quat(yaw: float):
    # z-only rotation
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))

if __name__ == "__main__":
    rospy.init_node("publish_initialpose", anonymous=True)

    x = rospy.get_param("~x", 0.0)
    y = rospy.get_param("~y", 0.0)
    yaw = rospy.get_param("~yaw", 0.0)
    frame_id = rospy.get_param("~frame_id", "map")
    delay = rospy.get_param("~delay", 1.0)

    pub = rospy.Publisher("/initialpose", PoseWithCovarianceStamped, queue_size=1)

    rospy.sleep(delay)

    msg = PoseWithCovarianceStamped()
    msg.header.stamp = rospy.Time.now()
    msg.header.frame_id = frame_id

    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose.position.z = 0.0

    qx, qy, qz, qw = yaw_to_quat(yaw)
    msg.pose.pose.orientation.x = qx
    msg.pose.pose.orientation.y = qy
    msg.pose.pose.orientation.z = qz
    msg.pose.pose.orientation.w = qw

    pub.publish(msg)
    rospy.loginfo("Published /initialpose: x=%.3f y=%.3f yaw=%.3f (frame=%s)", x, y, yaw, frame_id)
