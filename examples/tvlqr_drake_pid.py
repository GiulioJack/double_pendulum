import os
from datetime import datetime
import numpy as np

from double_pendulum.model.symbolic_plant import SymbolicDoublePendulum
from double_pendulum.model.model_parameters import model_parameters
from double_pendulum.simulation.simulation import Simulator
from double_pendulum.controller.tvlqr.tvlqr_controller_drake import TVLQRController
from double_pendulum.controller.pid.point_pid_controller import PointPIDController
from double_pendulum.controller.combined_controller import CombinedController
from double_pendulum.utils.plotting import plot_timeseries
from double_pendulum.utils.wrap_angles import wrap_angles_top
from double_pendulum.utils.csv_trajectory import save_trajectory, load_trajectory

# model parameters
urdf_path = "../data/urdfs/acrobot.urdf"
robot = "acrobot"

# damping = [0.081, 0.0]
cfric = [0., 0.]
motor_inertia = 0.
torque_limit = [0.0, 6.0]
torque_limit_pid = [6.0, 6.0]

model_par_path = "../data/system_identification/identified_parameters/tmotors_v1.0/model_parameters.yml"
#model_par_path = "../data/system_identification/identified_parameters/tmotors_v2.0/model_parameters_est.yml"
mpar = model_parameters()
mpar.load_yaml(model_par_path)
mpar.set_motor_inertia(motor_inertia)
# mpar.set_damping(damping)
mpar.set_cfric(cfric)
mpar.set_torque_limit(torque_limit)

mpar_dp = model_parameters()
mpar_dp.load_yaml(model_par_path)
mpar_dp.set_motor_inertia(motor_inertia)
# mpar_dp.set_damping(damping)
mpar_dp.set_cfric(cfric)
mpar_dp.set_torque_limit(torque_limit_pid)
# trajectory parameters
## tmotors v1.0
#csv_path = "../data/trajectories/acrobot/dircol/acrobot_tmotors_swingup_1000Hz.csv"
#read_with = "pandas"  # for dircol traj
#keys = "shoulder-elbow"

# tmotors v1.0
csv_path = "../data/trajectories/acrobot/ilqr_v1.0/trajectory.csv"
read_with = "numpy"
keys = ""

# tmotors v2.0
#csv_path = "../data/trajectories/acrobot/ilqr/trajectory.csv"
#read_with = "numpy"
#keys = ""

# load reference trajectory
T_des, X_des, U_des = load_trajectory(csv_path, read_with)
dt = T_des[1] - T_des[0]
t_final = T_des[-1] + 3
goal = [np.pi, 0., 0., 0.]

# simulation parameters
x0 = [0.0, 0.0, 0.0, 0.0]

process_noise_sigmas = [0., 0., 0., 0.]
meas_noise_sigmas = [0., 0., 0.0, 0.0]
meas_noise_cut = 0.0
meas_noise_vfilter = "none"
meas_noise_vfilter_args = {"alpha": [1., 1., 1., 1.]}
delay_mode = "None"
delay = 0.0
u_noise_sigmas = [0., 0.]
u_responsiveness = 1.0
perturbation_times = []
perturbation_taus = []

# controller parameters
Q = np.diag([0.64, 0.56, 0.13, 0.037])
R = np.eye(1)*0.82
Qf = np.copy(Q)

Kp = 10.
Ki = 0.
Kd = 0.1

def condition1(t, x):
    return False

def condition2(t, x):
    goal = [np.pi, 0., 0., 0.]
    eps = [0.2, 0.2, 0.8, 0.8]

    y = wrap_angles_top(x)

    delta = np.abs(np.subtract(y, goal))
    max_diff = np.max(np.subtract(delta, eps))
    if max_diff > 0.:
        return False
    else:
        return True

# init plant, simulator and controller
plant = SymbolicDoublePendulum(model_pars=mpar_dp)

sim = Simulator(plant=plant)
sim.set_process_noise(process_noise_sigmas=process_noise_sigmas)
sim.set_measurement_parameters(meas_noise_sigmas=meas_noise_sigmas,
                               delay=delay,
                               delay_mode=delay_mode)
sim.set_filter_parameters(meas_noise_cut=meas_noise_cut,
                          meas_noise_vfilter=meas_noise_vfilter,
                          meas_noise_vfilter_args=meas_noise_vfilter_args)
sim.set_motor_parameters(u_noise_sigmas=u_noise_sigmas,
                         u_responsiveness=u_responsiveness)

controller1 = TVLQRController(
        csv_path=csv_path,
        urdf_path=urdf_path,
        read_with=read_with,
        torque_limit=torque_limit,
        robot=robot)

controller1.set_cost_parameters(Q=Q, R=R, Qf=Qf)
controller1.init()

controller2 = PointPIDController(
        torque_limit=torque_limit_pid,
        goal=goal,
        dt=dt)
controller2.set_parameters(
        Kp=Kp,
        Ki=Ki,
        Kd=Kd)
controller2.init()

controller = CombinedController(
        controller1=controller1,
        controller2=controller2,
        condition1=condition1,
        condition2=condition2)

# simulate
T, X, U = sim.simulate_and_animate(t0=0.0, x0=x0,
                                   tf=t_final, dt=dt, controller=controller,
                                   integrator="runge_kutta",# imperfections=imperfections,
                                   plot_inittraj=True)
# if imperfections:
X_meas = sim.meas_x_values
X_filt = sim.filt_x_values
U_con = sim.con_u_values

# saving and plotting
timestamp = datetime.today().strftime("%Y%m%d-%H%M%S")
save_dir = os.path.join("data", robot, "tvlqr_pid", timestamp)
os.makedirs(save_dir)

os.system(f"cp {csv_path} " + os.path.join(save_dir, "init_trajectory.csv"))
save_trajectory(os.path.join(save_dir, "trajectory.csv"), T, X, U)

plot_timeseries(T, X, U, None,
                plot_energy=False,
                pos_y_lines=[0.0, np.pi],
                T_des=T_des,
                X_des=X_des,
                U_des=U_des,
                X_meas=X_meas,
                U_con=U_con)
