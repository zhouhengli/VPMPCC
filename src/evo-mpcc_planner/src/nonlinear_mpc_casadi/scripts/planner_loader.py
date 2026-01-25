#!/usr/bin/env python

import ctypes
import os
import rospy

lib_path = os.path.join(os.path.dirname(__file__))
import Nonlinear_MPC_node  

if __name__ == "__main__":
    Nonlinear_MPC_node.MPCKinematicNode()
    rospy.spin()