#!/usr/bin/env python3
from casadi import *
import numpy as np

import rospy
from geometry_msgs.msg import Point, Quaternion, Vector3
from std_msgs.msg import ColorRGBA
from tf.transformations import quaternion_from_euler
from visualization_msgs.msg import Marker, MarkerArray

g_ = 9.81

class MPC:
    def __init__(self, cost_type, system_model):
        self.dT = None
        self.N = None
        self.L = None
        self.v_max = None
        self.v_min = None
        self.theta_max = None
        self.theta_min = None
        self.s_min, self.s_max = None, None
        self.p_min = None
        self.p_max = None
        self.x_min, self.x_max, self.y_min, self.y_max, self.psi_min, self.psi_max = None, None, None, None, None, None
        self.n_states, self.n_controls, self.T_V = None, None, None
        self.f = None
        self.U = None
        self.P = None
        self.X = None
        self.obj = 0
        self.X0 = None  # initial estimate for the states solution
        self.u0 = None  # initial estimate for the controls solution
        self.g = []
        self.Q = None
        self.R = None
        self.opts = {}
        self.param = {}
        self.lbg, self.ubg = None, None
        self.lbx, self.ubx = None, None
        self.nlp = None
        self.solver = None
        self.X_OBST = 3
        self.inf = 1e6
        self.SIDE_DECISION = 1
        self.is_ot = False

        self.center_lut_x, self.center_lut_y = None, None
        self.center_lut_dx, self.center_lut_dy = None, None
        self.right_lut_x, self.right_lut_y = None, None
        self.left_lut_x, self.left_lut_y = None, None
        self.element_arc_lengths = None
        self.arc_lengths_orig_l = None
        self.WARM_START = False
        self.INTEGRATION_MODE = "Euler"  # RK4 and RK3 method are the other two choices
        self.p_initial = 2.5  # projected centerline vel can set to desired value for initial estimation
        self.boundary_pub = None

    def setup_MPC(self):
        self.init_system_model()
        self.init_constraints()
        self.compute_optimization_cost()
        self.init_ipopt_solver()
        self.init_mpc_start_conditions()

    def init_system_model(self):
        # States
        x = MX.sym('x')
        y = MX.sym('y')
        psi = MX.sym('psi')
        s = MX.sym('s')

        # Controls
        v = MX.sym('v')
        theta = MX.sym('theta')
        p = MX.sym('p')

        states = vertcat(x, y, psi, s)
        controls = vertcat(v, theta, p)
        self.n_states = states.size1()
        self.n_controls = controls.size1()
        self.T_V = self.n_states + self.n_controls
        rhs = vertcat(v * cos(psi), v * sin(psi), (v / self.L) * tan(theta), p)  # dynamic equations of the states
        
        self.f = Function('f', [states, controls], [rhs])  # nonlinear mapping function f(x,u)
        self.U = MX.sym('U', self.n_controls, self.N)

        self.P = MX.sym('P', self.n_states + 2 * self.N + self.X_OBST + self.SIDE_DECISION)

        self.X = MX.sym('X', self.n_states, (self.N + 1))

        self.Q = MX.zeros(2, 2)
        self.Q[0, 0] = self.param['mpc_w_cte']  # cross track error
        self.Q[1, 1] = self.param['mpc_w_lag']  # lag error

        self.S = MX.zeros(3, 3)
        self.S[0, 0] = self.param['mpc_w_accel']  # change in velocity i.e, acceleration
        self.S[1, 1] = self.param['mpc_w_delta_d']  # change in steering angle. weighing matrices (change in controls)
        self.S[2, 2] = self.param['mpc_w_delta_vp'] # change in vp i.e, vp acceleration

        self.mpc_vp_project = self.param['mpc_vp_project']
        self.obj = 0  # Objective function
        self.g = []  # constraints vector

    def set_initial_params(self, param, vheid, is_ot):
        '''Set initial parameters related to MPC'''
        self.vheid = vheid
        self.param = param
        self.dT = param['dT']
        self.N = param['N']
        self.L = param['L']
        self.theta_max, self.v_max = param['theta_max'], param['v_max']
        self.p_initial = self.v_max
        self.theta_min = -self.theta_max
        self.v_min = -self.v_max
        self.x_min, self.x_max = param['x_min'], param['x_max']
        self.y_min, self.y_max = param['y_min'], param['y_max']
        self.psi_min, self.psi_max = param['psi_min'], param['psi_max']
        self.s_min, self.s_max = param['s_min'], param['s_max']
        self.p_min, self.p_max = param['p_min'], param['p_max']
        self.INTEGRATION_MODE = param['INTEGRATION_MODE']
        self.mpc_v_track = param['mpc_v_track']
        self.Vbias_max = param["Vbias_max"]
        self.is_ot = is_ot

    def set_track_data(self, c_x, c_y, c_dx, c_dy, r_x, r_y, l_x, l_y, element_arc_lengths, original_arc_length_total, ref_v):
        self.center_lut_x, self.center_lut_y = c_x, c_y
        self.center_lut_dx, self.center_lut_dy = c_dx, c_dy
        self.right_lut_x, self.right_lut_y = r_x, r_y
        self.left_lut_x, self.left_lut_y = l_x, l_y
        self.element_arc_lengths = element_arc_lengths
        self.arc_lengths_orig_l = original_arc_length_total
        self.ref_v = ref_v

    def compute_optimization_cost(self):
        st = self.X[:, 0]  # initial state
        self.g = vertcat(self.g, st - self.P[0:self.n_states])  # initial condition constraints

        for k in range(self.N):
            st = self.X[:, k]
            st_next = self.X[:, k + 1]
            con = self.U[:, k]
            ################## get ref msg ##################
            ref_v = self.ref_v(st_next[3])
            ################## get ref msg ##################

            dx, dy = self.center_lut_dx(st_next[3]), self.center_lut_dy(st_next[3])
            t_angle = atan2(dy, dx)
            ref_x, ref_y = self.center_lut_x(st_next[3]), self.center_lut_y(st_next[3])
            # Contouring error
            e_c = (sin(t_angle) * (st_next[0] - ref_x) - cos(t_angle) * (st_next[1] - ref_y)) / 0.5
            # Lag error
            e_l = (-cos(t_angle) * (st_next[0] - ref_x) - sin(t_angle) * (st_next[1] - ref_y)) / 0.5
            error = vertcat(e_c, e_l)

            self.obj = self.obj + mtimes(mtimes(error.T, self.Q), error)
            self.obj = self.obj - self.mpc_vp_project * (con[2]/self.p_max) * self.dT

            if not self.is_ot:
                ################## reference velocity tracking mpcc ##################
                self.obj = self.obj + (((con[0] - ref_v) / self.Vbias_max)** 2) * self.mpc_v_track
                ################## reference velocity tracking mpcc ##################
            else:
                ################## Terminal Velocity Cost MPCC ##################
                # === Retrieve obstacle position ===
                obs_x_idx = self.n_states + 2 * self.N + 1               # Start index for obstacle coordinates in parameter vector
                pos = st_next[0:2]                                       # Current vehicle position [x, y]
                obs = self.P[obs_x_idx : obs_x_idx + 2]                  # Obstacle position [obs_x, obs_y]

                # === Tuning parameters ===
                w_obs = 0.3 + ref_v * 0.01        # Weight of obstacle cost term, adaptive to terminal velocity

                # ===  Base obstacle cost ===
                diff_0 = pos - obs
                dist2_0 = mtimes(diff_0.T, diff_0)
                phi_0 = log(1 + 1.0 / (dist2_0 + 1e-3))

                # === Terminal Velocity Cost ===
                self.obj = self.obj + w_obs * phi_0 # penalizes proximity to the actual obstacle,
                
                if k == self.N - 1:
                    self.obj = self.obj + ((con[0] - ref_v))**2 * log(dist2_0 + 5) 
                ################## Terminal Velocity Cost MPCC ##################

            # delta u
            if k < self.N - 1:
                con_next = self.U[:, k + 1]
                self.obj += mtimes(mtimes(((con_next - con).T), self.S), ((con_next - con)))

            k1 = self.f(st, con)
            if self.INTEGRATION_MODE == "Euler":
                st_next_euler = st + (self.dT * k1)
            elif self.INTEGRATION_MODE == "RK3":
                k2 = self.f(st + self.dT / 2 * k1, con)
                k3 = self.f(st + self.dT * (2 * k2 - k1), con)
                st_next_euler = st + self.dT / 6 * (k1 + 4 * k2 + k3)
            elif self.INTEGRATION_MODE == "RK4":
                k2 = self.f(st + self.dT / 2 * k1, con)
                k3 = self.f(st + self.dT / 2 * k2, con)
                k4 = self.f(st + self.dT * k3, con)
                st_next_euler = st + self.dT / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

            self.g = vertcat(self.g, st_next - st_next_euler)  # compute constraints

            # path boundary constraints
            self.g = vertcat(self.g, self.P[self.n_states + 2 * k] * st_next[0] - self.P[self.n_states + 2 * k + 1] * st_next[1])  # LB<=ax-by<=UB  --represents half space planes

    def init_ipopt_solver(self):
        # Optimization variables(States+controls) across the prediction horizon
        OPT_variables = vertcat(reshape(self.X, self.n_states * (self.N + 1), 1),
                                reshape(self.U, self.n_controls * self.N, 1))
        self.opts["ipopt"] = {}
        self.opts["ipopt"]["max_iter"] = 500
        self.opts["ipopt"]["print_level"] = 0
        self.opts["verbose"] = self.param['ipopt_verbose']
        self.opts["jit"] = self.param['is_jit'] # cpu of nuc is powerful, so it is no necessary to use jit
        self.opts["print_time"] = 0
        self.opts["ipopt"]["acceptable_tol"] = 1e-8
        self.opts["ipopt"]["acceptable_obj_change_tol"] = 1e-6
        self.opts["ipopt"]["fixed_variable_treatment"] = "make_parameter"
        # Nonlinear problem formulation with solver initialization
        self.nlp_prob = {'f': self.obj, 'x': OPT_variables, 'g': self.g, 'p': self.P}
        self.solver = nlpsol('solver', 'ipopt', self.nlp_prob, self.opts)

    def init_constraints(self):
        '''Initialize constraints for states, dynamic model state transitions and control inputs of the system'''
        self.lbg = np.zeros((self.n_states * (self.N + 1) + self.N, 1))
        self.ubg = np.zeros((self.n_states * (self.N + 1) + self.N, 1))
        self.lbx = np.zeros((self.n_states + (self.n_states + self.n_controls) * self.N, 1))
        self.ubx = np.zeros((self.n_states + (self.n_states + self.n_controls) * self.N, 1))

        for k in range(self.N + 1):
            self.lbx[self.n_states * k:self.n_states * (k + 1), 0] = np.array(
                [[self.x_min, self.y_min, self.psi_min, self.s_min]])
            self.ubx[self.n_states * k:self.n_states * (k + 1), 0] = np.array(
                [[self.x_max, self.y_max, self.psi_max, self.s_max]])
        state_count = self.n_states * (self.N + 1)
        # Upper and lower bounds for the control optimization variables
        for k in range(self.N):
            self.lbx[state_count:state_count + self.n_controls, 0] = np.array(
                [[self.v_min, self.theta_min, self.p_min]])  
            self.ubx[state_count:state_count + self.n_controls, 0] = np.array(
                [[self.v_max, self.theta_max, self.p_max]])  
            state_count += self.n_controls
        
    def init_mpc_start_conditions(self):
        self.u0 = np.zeros((self.N, self.n_controls))
        self.X0 = np.zeros((self.N + 1, self.n_states))

    def get_angle_at_centerline(self, s):
        dx, dy = self.center_lut_dx(s), self.center_lut_dy(s)
        return np.arctan2(dy, dx)

    def get_point_at_centerline(self, s):
        return self.center_lut_x(s), self.center_lut_y(s)

    def get_path_constraints_points(self, prev_soln):
        right_points = np.zeros((self.N, 2))
        left_points = np.zeros((self.N, 2))
        for k in range(1, self.N + 1):
            right_points[k - 1, :] = np.array([self.right_lut_x(prev_soln[k, 3]),
                                      self.right_lut_y(prev_soln[k, 3])], dtype=object).squeeze()  # Right boundary
            left_points[k - 1, :] = np.array([self.left_lut_x(prev_soln[k, 3]),
                                     self.left_lut_y(prev_soln[k, 3])], dtype=object).squeeze()  # Left boundary

        return right_points, left_points

    def construct_warm_start_soln(self, initial_state):
        if initial_state[3] >= self.arc_lengths_orig_l:
            initial_state[3] -= self.arc_lengths_orig_l
        initial_state[2] = self.get_angle_at_centerline(initial_state[3])
        self.X0[0, :] = initial_state
        for k in range(1, self.N + 1):
            init_speed = self.p_initial/10
            s_next = self.X0[k - 1, 3] + init_speed * self.dT
            psi_next = self.get_angle_at_centerline(s_next)
            x_next, y_next = self.get_point_at_centerline(s_next)
            phi_dot = (psi_next - self.X0[k - 1, 2]) / self.dT
            theta_init = atan2((phi_dot * self.vheid["l_wb"]), init_speed)
            self.X0[k, :] = np.array([x_next, y_next, psi_next, s_next], dtype=object)
            
    def filter_estimate(self, initial_arc_pos):
        if (self.X0[0, 3] >= self.arc_lengths_orig_l) and ((initial_arc_pos >= self.arc_lengths_orig_l) or (initial_arc_pos <= 5)):
            self.X0[:, 3] = self.X0[:, 3] - self.arc_lengths_orig_l
        # every time of the vehicle pos should be adjust
        if initial_arc_pos >= self.arc_lengths_orig_l:
            initial_arc_pos -= self.arc_lengths_orig_l
        return initial_arc_pos

    def solve(self, initial_state, obstacles):
        p = np.zeros(self.n_states + 2 * self.N + self.X_OBST + self.SIDE_DECISION)
        
        delta_yaw = self.X0[1, 2] - initial_state[2]
        if abs(delta_yaw) >= np.pi:
            new_val_ceil = initial_state[2] + np.ceil(delta_yaw / (2 * np.pi)) * (2 * np.pi)
            new_val_floor = initial_state[2] + np.floor(delta_yaw / (2 * np.pi)) * (2 * np.pi)
            if abs(new_val_ceil - self.X0[1, 2]) < abs(new_val_floor - self.X0[1, 2]):
                initial_state[2] = new_val_ceil
            else:
                initial_state[2] = new_val_floor
        if not self.WARM_START:
            self.X0 = np.zeros((self.N + 1, self.n_states))
            rospy.loginfo("Warm start started")
            self.construct_warm_start_soln(initial_state)
            rospy.loginfo("Warm start accomplished")

        initial_state[3] = self.filter_estimate(initial_state[3])
        p[0:self.n_states] = initial_state  # initial condition of the robot posture
        right_points, left_points = self.get_path_constraints_points(self.X0)
        # print(f"right_points: {right_points}, left_points: {left_points}")
        select_front_obstacle_result = self.select_front_obstacle(initial_state[0], initial_state[1], initial_state[2], obstacles, D_max=10.0, D_min_trig=5.0) # should be [dmin, x_obs, y_obs]
        p[self.n_states + 2 * self.N:self.n_states + 2 * self.N + self.X_OBST] = np.array(select_front_obstacle_result)
        obs_choosen = p[self.n_states + 2 * self.N + 1: self.n_states + 2 * self.N + self.X_OBST] # should be [x_obs, y_obs]
        side_pref = self.decide_side_pref(obs_choosen, left_points, right_points)
        p[self.n_states + 2 * self.N + self.X_OBST + self.SIDE_DECISION - 1] = side_pref
        self.publish_boundary_markers(right_points, left_points)

        for k in range(self.N):  # set the reference controls and path boundary conditions to track
            delta_x_path = right_points[k, 0] - left_points[k, 0]
            delta_y_path = right_points[k, 1] - left_points[k, 1]
            p[self.n_states + 2 * k:self.n_states + 2 * k + 2] = [-delta_x_path, delta_y_path]
            up_bound = max(-delta_x_path * right_points[k, 0] - delta_y_path * right_points[k, 1],
                           -delta_x_path * left_points[k, 0] - delta_y_path * left_points[k, 1])
            low_bound = min(-delta_x_path * right_points[k, 0] - delta_y_path * right_points[k, 1],
                            -delta_x_path * left_points[k, 0] - delta_y_path * left_points[k, 1])
            self.lbg[self.n_states - 1 + (self.n_states + 1) * (k + 1), 0] = low_bound
            self.ubg[self.n_states - 1 + (self.n_states + 1) * (k + 1), 0] = up_bound
        
        x_init = vertcat(reshape(self.X0.T, self.n_states * (self.N + 1), 1),
                         reshape(self.u0.T, self.n_controls * self.N, 1))

        sol = self.solver(x0=x_init, lbx=self.lbx, ubx=self.ubx, lbg=self.lbg, ubg=self.ubg, p=p)
        opti_value = sol['f'].full().item()

        # Get state and control solution
        self.X0 = reshape(sol['x'][0:self.n_states * (self.N + 1)], self.n_states, self.N + 1).T  # get soln trajectory
        u = reshape(sol['x'][self.n_states * (self.N + 1):], self.n_controls, self.N).T  
        con_first = u[0, :].T
        trajectory = self.X0.full()  # size is (N+1,n_states)
        inputs = u.full()
        self.X0 = vertcat(self.X0[1:, :], self.X0[self.X0.size1() - 1, :])
        self.u0 = vertcat(u[1:, :], u[u.size1() - 1, :])

        return con_first, trajectory, inputs, opti_value

    def heading(self, yaw):
        q = quaternion_from_euler(0, 0, yaw)
        return Quaternion(*q)

    def publish_boundary_markers(self, right_points, left_points):
        boundary_array = MarkerArray()
        combined_points = np.row_stack((right_points, left_points))
        delta = right_points - left_points
        angles = np.arctan2(delta[:, 0], -delta[:, 1])
        for i in range(combined_points.shape[0]):
            path_marker = Marker()
            path_marker.header.frame_id = "map"
            path_marker.id = i
            path_marker.type = path_marker.ARROW
            path_marker.action = path_marker.ADD
            path_marker.scale = Vector3(0.25, 0.05, 0.05)
            path_marker.color = ColorRGBA(0.0, 0.0, 1.0, 0.8)
            path_marker.pose.orientation = self.heading(angles[i % right_points.shape[0]])
            path_marker.pose.position = Point(float(combined_points[i, 0]), float(combined_points[i, 1]), 0.0)
            boundary_array.markers.append(path_marker)
        self.boundary_pub.publish(boundary_array)

    def decide_side_pref(self, obstacle_pos, left_points, right_points, margin=0.1):
        """
        Decide which side (left or right) the vehicle should overtake from,
        based on the obstacle's Euclidean distance to both lane boundaries.

        Parameters
        ----------
        obstacle_pos : tuple (x, y)
            The obstacle center position in global coordinates.
        left_points : np.ndarray, shape = (N, 2)
            Array of points representing the left lane boundary.
        right_points : np.ndarray, shape = (N, 2)
            Array of points representing the right lane boundary.
        margin : float
            If the absolute difference between left/right average distances 
            is smaller than this threshold, no preference is returned (0).

        Returns
        -------
        side_pref : int
            +1 → Prefer overtaking on the left side  
            -1 → Prefer overtaking on the right side  
            0 → Nearly equal spacing (keep current direction or no preference)
        """

        x_o, y_o = obstacle_pos

        if x_o > 1e5 and y_o > 1e5:
            # No obstacle detected
            return 0

        # Compute Euclidean distance from obstacle to each boundary point
        dist_L = np.sqrt((left_points[:, 0] - x_o)**2 + (left_points[:, 1] - y_o)**2)
        dist_R = np.sqrt((right_points[:, 0] - x_o)**2 + (right_points[:, 1] - y_o)**2)

        # Take the smallest two distances (closest boundary points) to smooth noise
        top2_L = np.sort(dist_L)[:2] if len(dist_L) >= 2 else dist_L
        top2_R = np.sort(dist_R)[:2] if len(dist_R) >= 2 else dist_R
        mean_L = np.mean(top2_L)
        mean_R = np.mean(top2_R)

        # Determine preference by comparing the distances
        diff = mean_L - mean_R
        
        if diff > margin:
            return +1   # Left side is wider → prefer left overtaking
        elif diff < -margin:
            return -1   # Right side is wider → prefer right overtaking
        else:
            return 0    # Roughly equal → no preference


    def select_front_obstacle(self, curr_x, curr_y, curr_yaw,
                          obstacles, D_max=5.0, D_min_trig=2.0):
        """
        Select the nearest obstacle in front of the vehicle within a given range.

        Parameters
        ----------
        curr_x, curr_y, curr_yaw : float
            Current vehicle position and heading (in world coordinates).
        obstacles : list of (x_o, y_o)
            List of obstacle centers (and optionally radius if available).
        D_max : float
            Maximum distance threshold. Obstacles farther than this are ignored.
        D_min_trig : float
            "Trigger distance" threshold. Obstacles closer than this are considered
            immediate and returned directly.

        Returns
        -------
        tuple :
            (d_min, x_o_min, y_o_min)
                If a valid obstacle is found ahead of the vehicle.  
            (self.inf, self.inf, self.inf)
                If no valid obstacle exists within range or field of view.
        """

        pos = np.array([curr_x, curr_y])
        t = np.array([np.cos(curr_yaw), np.sin(curr_yaw)])  # Vehicle forward direction

        candidates = []

        for (x_o, y_o) in obstacles:
            obs = np.array([x_o, y_o])
            v = obs - pos
            dist = np.linalg.norm(v)

            # 1. Distance filter: ignore obstacles that are too far
            if dist > D_max:
                continue

            # 2. Only consider obstacles in front of the vehicle (dot product > 0)
            if np.dot(t, v) <= 0.0:
                continue

            candidates.append((dist, x_o, y_o))

        if len(candidates) == 0:
            # No obstacle found
            return self.inf, self.inf, self.inf

        # Sort by distance (ascending)
        candidates.sort(key=lambda c: c[0])
        d_min, x_min, y_min = candidates[0]

        # If the nearest obstacle is within the trigger distance, return it;
        # otherwise, treat as no obstacle.
        if d_min < D_min_trig:
            return d_min, x_min, y_min
        else:
            return self.inf, self.inf, self.inf

