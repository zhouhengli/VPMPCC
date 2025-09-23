#!/usr/bin/env python3
import matplotlib.pyplot as plt
import csv
import os
import time
import numpy as np
import math
import rospy

from casadi import *
from scipy.interpolate import splprep, splev
from geometry_msgs.msg import Pose, PoseStamped, Quaternion, Vector3, Point, PointStamped
from ackermann_msgs.msg import AckermannDriveStamped
from nav_msgs.msg import Path, Odometry
from std_msgs.msg import Duration, Header, ColorRGBA
from tf.transformations import quaternion_from_euler, euler_from_quaternion
from visualization_msgs.msg import Marker, MarkerArray
from Nonlinear_MPC import MPC
from osuf1_common.msg import MPC_metadata, MPC_trajectory, MPC_prediction

# user defined
from std_msgs.msg import Float32,Int32
import pickle
import datetime
from geometry_msgs.msg import PoseWithCovarianceStamped
import signal
import sensor_msgs.msg
from mpl_toolkits.mplot3d import Axes3D
from std_msgs.msg import Float32, String
from std_msgs.msg import Time, Empty
import json
from f110_msgs.msg import LapData, WpntArray, ObstacleArray, Obstacle
from sensor_msgs.msg import Imu
import random

class MPCKinematicNode:
    def __init__(self):
        rospy.init_node('mpc_node')
        self.tools_path = rospy.get_param('home_dir', None)
        self.mpc_coe_dir = "f1tenth_ws/params/mpc/"
        self.INF_NUM = 1e10
        self.params_file = rospy.get_param('params_file', "BO_params")

        self.system_model = rospy.get_param('system_model', None)
        self.cost_type = rospy.get_param('cost_type', None)
        self.other_planner = None
        self.issave_pretraj = False
        self.is_jit = rospy.get_param('is_jit', None)

        mpc_coe_name = os.path.join(self.tools_path, self.mpc_coe_dir, self.params_file + ".json")
        with open(mpc_coe_name, 'r') as file:
            self.parameters_algo = json.load(file)
        rospy.loginfo("%s", self.parameters_algo)

        self.param = self.getPreDefinedParas()
        self.is_sim = rospy.get_param('/converter/is_sim', False)
        self.is_data_record = rospy.get_param('is_data_record', False)
        self.is_BO_trainning = False
        self.is_state_machine = False

        ################## load tire model params ##################
        self.vheid = {
            'C_Pf': rospy.get_param('/model_params/C_Pf', None),
            'C_Pr': rospy.get_param('/model_params/C_Pr', None),
            'I_z': rospy.get_param('/model_params/I_z', None),
            'a_max': rospy.get_param('/model_params/a_max', None),
            'a_min': rospy.get_param('/model_params/a_min', None),
            'h_cg': rospy.get_param('/model_params/h_cg', None),
            'l_f': rospy.get_param('/model_params/l_f', None),
            'l_r': rospy.get_param('/model_params/l_r', None),
            'l_wb': rospy.get_param('/model_params/l_wb', None),
            'm': rospy.get_param('/model_params/m', None),
            'mu': rospy.get_param('/model_params/mu', None),
            'tire_model': rospy.get_param('/tire_model', None),
            }
        ################## load tire model params ##################

        ####################### user defined params #######################
        self.reset_list = [0, 1, 5] # 0:A 1:B 5:LB
        self.reset_list_check = [0, 0, 0]
        self.center_path_length = 0.
        
        self.parasReInit()
        ####################### user defined params #######################
        if not self.is_sim: # real car 
            rospy.Subscriber('/vesc/joy', sensor_msgs.msg.Joy, self.joy_callback)
            rospy.loginfo("use /vesc/odom")
            self.vx_odom = 0
            self.vy_odom = 0
            # self.pf_correct_pub = rospy.Publisher('/initialpose', PoseWithCovarianceStamped, queue_size=10)

        ####################### original settings #######################
        # Topic name related parameters
        pose_topic = rospy.get_param('localized_pose_topic_name', '/pf/viz/inferred_pose')
        cmd_vel_topic = rospy.get_param('cmd_vel_topic_name', '/vesc/high_level/ackermann_cmd_mux/input/nav_0')
        goal_topic = rospy.get_param('goal_topic_name', '/move_base_simple/goal')
        prediction_pub_topic = rospy.get_param('mpc_prediction_topic', 'mpc_prediction')
        odom_topic = rospy.get_param('odom_topic_name', '/vesc/odom')

        # user add and replace
        self.INFLATION_FACTOR = self.parameters_algo['alpha']
        self.LAG_TIME = rospy.get_param('lag_time', 0.05)
        self.DELAY_MODE = False
        self.CONTROLLER_FREQ = rospy.get_param('CONTROLLER_FREQ', 40)

        self.car_frame = rospy.get_param('car_frame', 'base_link')
        # Minimum distance search related variables
        self.ARC_LENGTH_MIN_DIST_TOL = rospy.get_param('arc_length_min_dist_tol', 0.05) # minimum distance between current pose and point on path to calculate arc length travelled without projection

        self.GOAL_THRESHOLD = rospy.get_param('goal_threshold', 0.75)
        self.DEBUG_MODE = rospy.get_param('debug_mode', False)
        self.THROTTLE_MODE = rospy.get_param('throttle_mode', False)

        # Publishers
        self.ackermann_pub = rospy.Publisher(cmd_vel_topic, AckermannDriveStamped, queue_size=10)
        self.mpc_trajectory_pub = rospy.Publisher('/mpc_trajectory', Path, queue_size=10)
        self.mpc_trajectory_center_pub = rospy.Publisher('/mpc_center_trajectory', Path, queue_size=10)
        self.center_path_pub = rospy.Publisher('/center_path', Path, queue_size=10)
        self.right_path_pub = rospy.Publisher('/right_path', Path, queue_size=10)
        self.left_path_pub = rospy.Publisher('/left_path', Path, queue_size=10)
        self.center_tangent_pub = rospy.Publisher('/center_tangent', PoseStamped, queue_size=10)
        self.path_boundary_pub = rospy.Publisher('/boundary_marker', MarkerArray, queue_size=10)
        self.prediction_pub = rospy.Publisher(prediction_pub_topic, MPC_trajectory, queue_size=1)

        # Path related variables
        self.path_points = None
        self.center_lane = None
        self.center_point_angles = None
        self.center_lut_x, self.center_lut_y = None, None
        self.center_lut_dx, self.center_lut_dy = None, None
        self.right_lut_x, self.right_lut_y = None, None
        self.left_lut_x, self.left_lut_y = None, None
        self.element_arc_lengths = None
        self.element_arc_lengths_orig = None
        ####################### original settings #######################
    

        ####################### load different racetrack files #######################
        self.track_name = rospy.get_param('/converter/trackname', 'map421V5')
        self.map_name = rospy.get_param('/converter/mapname', 'map421V5')
        self.track_dir = "f1tenth_ws/toolkit/tracks/"
        path_folder_name = '/track'

        # rospy.loginfo("%s", self.tools_path)
        self.CENTER_TRACK_FILENAME = os.path.join(self.tools_path, self.track_dir, "track" + self.track_name + path_folder_name + self.track_name +  '_centerline_waypoints.csv')
        # rospy.loginfo("%s", self.CENTER_TRACK_FILENAME)
        self.CENTER_DERIVATIVE_FILENAME = os.path.join(self.tools_path, self.track_dir, "track" + self.track_name + path_folder_name + self.track_name +  '_center_derivates.csv')
        self.RIGHT_TRACK_FILENAME = os.path.join(self.tools_path, self.track_dir, "track" + self.track_name + path_folder_name + self.track_name + '_right_waypoints.csv')
        self.LEFT_TRACK_FILENAME = os.path.join(self.tools_path, self.track_dir, "track" + self.track_name + path_folder_name + self.track_name + '_left_waypoints.csv')
        ####################### load different racetrack files #######################
    
        ####################### Topic user defined topics #######################
        self.pf_pose_trans_pub = rospy.Publisher('/pf_pose_trans', PoseStamped, queue_size=10)
        ####################### Topic user defined topics #######################
            
        ####################### MPC related initializations #######################
        # MPC related initializations
        self.mpc = MPC("VPMPCC", "cimpcc_model")
        self.mpc.boundary_pub = self.path_boundary_pub
        self.initialize_MPC()
        self.current_pos_x, self.current_pos_y, self.current_yaw, self.current_s = 0.0, 0.0, 0.0, 0.0
        self.current_pose = None
        self.current_vel_odom = 0.0
        self.projected_vel = 0.0
        self.steering_angle = 0.0
        rospy.loginfo("element_arc_lengths_orig: %s", self.element_arc_lengths_orig[-1])
        self.d = 0.301 # laser dist to wheelbase
        ####################### MPC related initializations #######################

        ########################## Original Subscribers ##########################
        rospy.Subscriber(pose_topic, PoseStamped, self.pose_callback, queue_size=1)
        rospy.Subscriber(goal_topic, PoseStamped, self.goalCB, queue_size=1)
        rospy.Subscriber(odom_topic, Odometry, self.odomCB, queue_size=1)
        ########################## Original Subscribers ##########################

        # Timer callback function for the control loop
        rospy.Timer(rospy.Duration(1.0 / self.CONTROLLER_FREQ), self.controlLoopCB)
        ########################## paras need to be reinit when car doesn't run #################################################
            
    def parasReInit(self):
        # Plot related variables
        self.current_time = 0

        # Goal status related variables
        self.goal_pos = None
        self.goal_reached = False
        self.goal_received = False
        

    def joy_callback(self, data):
        origin_ctl_but = np.argwhere(data.buttons).flatten()
        origin_ctl_but = origin_ctl_but.tolist()

        if self.reset_list[2] not in origin_ctl_but:
            self.reset_list_check[2] = self.reset_list_check[2] + 1
            if self.reset_list_check[2] > 5:
                self.reset_list_check[2] = 0
                self.goal_received = False
                self.parasReInit()

        if self.reset_list[2] in origin_ctl_but:
            self.goal_received = True

    def initialize_MPC(self):
        self.preprocess_track_data()
        self.param['s_max'] = self.element_arc_lengths[-1]
        self.mpc.set_initial_params(self.param, self.vheid)
        self.mpc.set_track_data(self.center_lut_x, self.center_lut_y, self.center_lut_dx, self.center_lut_dy,
                        self.right_lut_x, self.right_lut_y, self.left_lut_x, self.left_lut_y,
                        self.element_arc_lengths, self.element_arc_lengths_orig[-1], self.lut_ref_v)
        
        self.mpc.setup_MPC()

    def create_header(self, frame_id):
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = frame_id
        return header

    def find_nearest_index(self, car_pos):
        distances_array = np.linalg.norm(self.center_lane - car_pos, axis=1)
        min_dist_idx = np.argmin(distances_array)
        
        return min_dist_idx, distances_array[min_dist_idx]

    def heading(self, yaw):
        q = quaternion_from_euler(0, 0, yaw)
        return Quaternion(*q)

    def quaternion_to_euler_yaw(self, orientation):
        _, _, yaw = euler_from_quaternion((orientation.x, orientation.y, orientation.z, orientation.w))
        return yaw

    def read_waypoints_array_from_csv(self, filename, type="path"):
        '''read waypoints from given csv file and return the data in the form of numpy array'''
        if filename == '':
            raise ValueError('No any file path for waypoints file')
        with open(filename) as f:
            path_points = [tuple(line) for line in csv.reader(f, delimiter=',')]

        if type == "traj":
            center_points = np.array([[float(point[0]), float(point[1])] for point in path_points])
            v_points = np.array([float(point[2]) for point in path_points])
            return center_points, v_points
        else:
            path_points = np.array([[float(point[0]), float(point[1])] for point in path_points])
            return path_points


    def pose_callback(self, msg):
        '''acquire estimated pose of car from particle filter'''
    
        self.current_yaw = self.quaternion_to_euler_yaw(msg.pose.orientation)
        if not self.is_sim:
            self.current_pos_x = msg.pose.position.x + self.d * np.cos(self.current_yaw + np.pi)
            self.current_pos_y = msg.pose.position.y + self.d * np.sin(self.current_yaw + np.pi)
            # Bz = Az
        else:
            self.current_pos_x = msg.pose.position.x
            self.current_pos_y = msg.pose.position.y

        self.current_pose = [self.current_pos_x, self.current_pos_y, self.current_yaw]
        

    def odomCB(self, msg):
        '''Get odometry data especially velocity from the car'''
        # in sim, current_vel_odom is sqrt(vx^2 + xy^2). But in real car, current_vel_odom = vx
        self.current_vel_odom = msg.twist.twist.linear.x
        self.omega_odom = msg.twist.twist.angular.z
        self.vx_odom = msg.twist.twist.linear.x
        self.vy_odom = msg.twist.twist.linear.y
        
    def goalCB(self, msg):
        '''Get goal pose from the user'''
        self.goal_pos = msg.pose.position
        self.goal_received = True
        self.goal_reached = False
        if self.DEBUG_MODE:
            print("Goal pos=", self.goal_pos)
        current_time_ros = rospy.get_rostime()

    def controlLoopCB(self, event):
        '''Control loop for car MPC'''

        pf_pose_trans_pose = PoseStamped()
        pf_pose_trans_pose.header = self.create_header('map')
        pf_pose_trans_pose.pose.position.x = self.current_pos_x
        pf_pose_trans_pose.pose.position.y = self.current_pos_y
        pf_pose_trans_pose.pose.orientation = self.heading(self.current_yaw)
        self.pf_pose_trans_pub.publish(pf_pose_trans_pose)      
    
       

        if self.goal_received == True and self.is_BO_trainning == False:
            
            px = self.current_pos_x
            py = self.current_pos_y
            car_pos = np.array([self.current_pos_x, self.current_pos_y])
            psi = self.current_yaw

            v = self.current_vel_odom
            steering = self.steering_angle  # radian
            L = self.mpc.L

            current_s, near_idx = self.find_current_arc_length(car_pos)
                     
            if self.other_planner == "pp":
                speed = self.pp_speed
                steering = self.pp_steering_angle
                mpc_compute_time = 0.
                opti_value = 0.
                # pretraj = []
            else:
                ####################### MPC related process #######################
                current_state = np.array([px, py, psi, current_s])
               
                centerPose = PoseStamped()
                centerPose.header = self.create_header('map')
                centerPose.pose.position.x = float(self.center_lane[near_idx, 0])
                centerPose.pose.position.y = float(self.center_lane[near_idx, 1])
                centerPose.pose.orientation = self.heading(self.center_point_angles[near_idx])
                self.center_tangent_pub.publish(centerPose)

                # Solve MPC Problem
                mpc_time = time.time()
                ##################################### main planner #####################################
                first_control, trajectory, control_inputs, opti_value = self.mpc.solve(current_state)
                ##################################### main planner #####################################
                mpc_compute_time = time.time() - mpc_time

                # MPC result (all described in car frame)
                speed = float(first_control[0])     # speed
                steering = float(first_control[1])  # radian
                
                self.projected_vel = speed

                if not self.mpc.WARM_START:
                    speed, steering, throttle = 0, 0, 0
                    self.mpc.WARM_START = True
                
                # Display the MPC predicted trajectory
                mpc_traj = Path()
                mpc_traj.header = self.create_header('map')
                mpc_traj.poses = []
                for i in range(trajectory.shape[0]):
                    tempPose = PoseStamped()
                    tempPose.header = mpc_traj.header
                    tempPose.pose.position.x = trajectory[i, 0]
                    tempPose.pose.position.y = trajectory[i, 1]
                    tempPose.pose.orientation = self.heading(trajectory[i, 2])
                    mpc_traj.poses.append(tempPose)
                self.mpc_trajectory_pub.publish(mpc_traj)

                # publish mpc prediction results message
                meta = MPC_metadata()
                meta.header = self.create_header('map')
                mpc_prediction_results = []
                for i in range(control_inputs.shape[0]):
                    mpc_prediction_states = [trajectory[i, 0], trajectory[i, 1], trajectory[i, 2], 0.1]
                    mpc_prediction_inputs = [control_inputs[i, 0], control_inputs[i, 1]]
                    mpc_prediction_results.append((mpc_prediction_states, mpc_prediction_inputs))

                trajectory = MPC_trajectory()
                trajectory.header = meta.header
                trajectory.trajectory = [MPC_prediction(pred[0], pred[1]) for pred in mpc_prediction_results]
                self.prediction_pub.publish(trajectory)
                
                self.current_time += 1.0 / self.CONTROLLER_FREQ
                ####################### MPC related process #######################

        else:
            steering = 0.0
            speed = 0.0
            throttle = 0.0

        ackermann_cmd = AckermannDriveStamped()
        ackermann_cmd.header = self.create_header(self.car_frame)
        ackermann_cmd.drive.steering_angle = steering
        self.steering_angle = steering
        ackermann_cmd.drive.speed = speed

        if self.THROTTLE_MODE:
            ackermann_cmd.drive.acceleration = throttle
        self.ackermann_pub.publish(ackermann_cmd)

    def publish_path(self, waypoints, publisher):
        # Visualize path derived from the given waypoints in the path
        path = Path()
        path.header = self.create_header('map')
        path.poses = []
        for point in waypoints:
            tempPose = PoseStamped()
            tempPose.header = path.header
            tempPose.pose.position.x = point[0]
            tempPose.pose.position.y = point[1]
            tempPose.pose.orientation.w = 1.0
            path.poses.append(tempPose)
        publisher.publish(path)
    
    def get_interpolated_path_casadi(self, label_x, label_y, pts, arc_lengths_arr):
        u = arc_lengths_arr
        V_X = pts[:, 0]
        # print(V_X)
        V_Y = pts[:, 1]
        lut_x = interpolant(label_x, 'bspline', [u], V_X)
        lut_y = interpolant(label_y, 'bspline', [u], V_Y)
        return lut_x, lut_y
    
    def get_interpolated_vref_casadi(self, label_v, pts, arc_lengths_arr):
        u = arc_lengths_arr
        V_ref = pts[:, 0]
        lut_ref_v = interpolant(label_v, 'bspline', [u], V_ref)
        return lut_ref_v

    def get_arc_lengths(self, waypoints):
        d = np.diff(waypoints, axis=0)
        consecutive_diff = np.sqrt(np.sum(np.power(d, 2), axis=1))
        dists_cum = np.cumsum(consecutive_diff)
        dists_cum = np.insert(dists_cum, 0, 0.0)
        return dists_cum


    def inflate_track_boundaries(self, center_lane, side_lane, car_width=0.325, inflation_factor=1.2):
        for idx in range(len(center_lane)):
            lane_vector = side_lane[idx, :] - center_lane[idx, :]
            side_track_width = np.linalg.norm(lane_vector)
            side_unit_vector = lane_vector / side_track_width
            side_lane[idx, :] = side_lane[idx, :] - side_unit_vector * inflation_factor * 0.8 # 0.8 is the offset scale
        return side_lane

    def preprocess_track_data(self):
        center_lane, ref_v = self.read_waypoints_array_from_csv(self.CENTER_TRACK_FILENAME, "traj")
        center_derivative_data = self.read_waypoints_array_from_csv(self.CENTER_DERIVATIVE_FILENAME)
        right_lane = self.read_waypoints_array_from_csv(self.RIGHT_TRACK_FILENAME)
        left_lane = self.read_waypoints_array_from_csv(self.LEFT_TRACK_FILENAME)
    
        for i in range(5):
            self.publish_path(center_lane, self.center_path_pub)
            self.publish_path(right_lane, self.right_path_pub)
            self.publish_path(left_lane, self.left_path_pub)
            rospy.sleep(0.2)

        right_lane = self.inflate_track_boundaries(center_lane, right_lane, None, self.INFLATION_FACTOR)
        left_lane = self.inflate_track_boundaries(center_lane, left_lane, None, self.INFLATION_FACTOR)
        
        extend_part = 2
        self.center_lane = np.row_stack((center_lane, center_lane[1:int(center_lane.shape[0] / extend_part), :]))
        right_lane = np.row_stack((right_lane, right_lane[1:int(center_lane.shape[0] / extend_part), :]))
        left_lane = np.row_stack((left_lane, left_lane[1:int(center_lane.shape[0] / extend_part), :]))
        center_derivative_data = np.row_stack(
            (center_derivative_data, center_derivative_data[1:int(center_lane.shape[0] / extend_part), :]))
                
        end_index = int(ref_v.shape[0] / extend_part)
        ref_v_2d = ref_v[:, np.newaxis]
        sub_array_2d = ref_v[1:end_index][:, np.newaxis]
        ref_v_stack = np.row_stack((ref_v_2d, sub_array_2d))

        # Interpolate center line upto desired resolution
        self.element_arc_lengths_orig = self.get_arc_lengths(center_lane)

        self.element_arc_lengths = self.get_arc_lengths(self.center_lane)
        self.center_path_length = self.element_arc_lengths_orig[-1]
        self.center_lut_x, self.center_lut_y = self.get_interpolated_path_casadi('lut_center_x', 'lut_center_y',
                                                                                 self.center_lane,
                                                                                 self.element_arc_lengths)
        self.center_lut_dx, self.center_lut_dy = self.get_interpolated_path_casadi('lut_center_dx', 'lut_center_dy',
                                                                                   center_derivative_data,
                                                                                   self.element_arc_lengths)
        self.center_point_angles = np.arctan2(center_derivative_data[:, 1], center_derivative_data[:, 0])

        # Interpolate right and left wall line
        self.right_lut_x, self.right_lut_y = self.get_interpolated_path_casadi('lut_right_x', 'lut_right_y', right_lane,
                                                                               self.element_arc_lengths)
        self.left_lut_x, self.left_lut_y = self.get_interpolated_path_casadi('lut_left_x', 'lut_left_y', left_lane,
                                                                             self.element_arc_lengths)
        
        self.lut_ref_v = self.get_interpolated_vref_casadi('lut_ref_v', ref_v_stack, self.element_arc_lengths)

    def find_current_arc_length(self, car_pos):
        nearest_index, minimum_dist = self.find_nearest_index(car_pos)
        # print(minimum_dist)
        if minimum_dist > self.ARC_LENGTH_MIN_DIST_TOL:
            if nearest_index == 0:
                next_idx = 1
                prev_idx = self.center_lane.shape[0] - 1
            elif nearest_index == (self.center_lane.shape[0] - 1):
                next_idx = 0
                prev_idx = self.center_lane.shape[0] - 2
            else:
                next_idx = nearest_index + 1
                prev_idx = nearest_index - 1
            dot_product_value = np.dot(car_pos - self.center_lane[nearest_index, :],
                                       self.center_lane[prev_idx, :] - self.center_lane[nearest_index, :])
            if dot_product_value > 0:
                nearest_index_actual = prev_idx
            else:
                nearest_index_actual = nearest_index
                nearest_index = next_idx
            new_dot_value = np.dot(car_pos - self.center_lane[nearest_index_actual, :],
                                   self.center_lane[nearest_index, :] - self.center_lane[nearest_index_actual, :])
            projection = new_dot_value / np.linalg.norm(
                self.center_lane[nearest_index, :] - self.center_lane[nearest_index_actual, :])
            current_s = self.element_arc_lengths[nearest_index_actual] + projection
        else:
            current_s = self.element_arc_lengths[nearest_index]

        if nearest_index == 0:
            current_s = 0.0

        return current_s, nearest_index

    def getPreDefinedParas(self):
        try:
            mpc_v_track = self.parameters_algo['q_v']
        except KeyError:
            mpc_v_track = 0
        param = {             
                'is_jit': self.is_jit,
                'mpc_v_track': mpc_v_track,
                'mpc_w_cte': self.parameters_algo['q_cte'],
                'mpc_w_lag': self.parameters_algo['q_lag'],
                'mpc_w_accel': self.parameters_algo['q_dv'],
                'mpc_w_delta_d': self.parameters_algo['q_d_delta'],
                'mpc_w_delta_vp': self.parameters_algo['q_dvp'],
                'mpc_vp_project': self.parameters_algo['gamma'],
                'N': self.parameters_algo['N_p'],

                'dT': rospy.get_param('dT', 0.1),
                'mpc_avoiding_obs': rospy.get_param('mpc_avoiding_obs', None),
                'theta_max': rospy.get_param('mpc_max_steering', 0.4),
                'v_max': rospy.get_param('max_speed', 15),
                'p_max': rospy.get_param('mpc_max_p', 15),
                'CEbetamax': rospy.get_param('CEbetamax', 1),
                'INTEGRATION_MODE': rospy.get_param('integration_mode', "Euler"),
                'L': rospy.get_param('vehicle_L', 0.319),
                'p_min': rospy.get_param('p_min', 0),
                'x_min': rospy.get_param('x_min', -200),
                'x_max': rospy.get_param('x_max', 200),
                'y_min': rospy.get_param('y_min', -200),
                'y_max': rospy.get_param('y_max', 200),
                'psi_min': rospy.get_param('psi_min', -1000),
                'psi_max': rospy.get_param('psi_max', 1000),
                's_min': rospy.get_param('s_min', 0),
                's_max': rospy.get_param('s_max', 200),
                'Vbias_max': rospy.get_param('Vbias_max', 10),
                'mpc_w_s': rospy.get_param('mpc_w_s', 0),
                'spline_poly_order': rospy.get_param('spline_poly_order', 3),
                'ipopt_verbose': rospy.get_param('ipopt_verbose', False)
                }
        return param

if __name__ == '__main__':
    mpc_node = MPCKinematicNode()
    rospy.spin()

