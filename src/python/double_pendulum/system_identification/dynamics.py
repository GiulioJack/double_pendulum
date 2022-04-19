import math
import numpy as np
import pandas as pd

from double_pendulum.system_identification.data_prep import smooth_data_butter


def yb_matrix(g, n, L1, q_vec=None, dq_vec=None, ddq_vec=None):
    """
    g: float
        gravity
    n: int
        gear ratio
    L1: float
        length of first link
    """
    s1_yb = -g*math.sin(q_vec[0] + q_vec[1])  # sigma1 in the regressor matrix

    y_1_1 = g*math.sin(q_vec[0])
    y_1_2 = ddq_vec[0]
    y_1_3 = math.atan(50*dq_vec[0])
    y_1_4 = dq_vec[0]
    y_1_5 = ddq_vec[0]*(n**2+1)+ddq_vec[1]*n
    y_1_6 = -L1*math.sin(q_vec[1])*dq_vec[1]**2 \
            - 2*L1*dq_vec[0]*math.sin(q_vec[1])*dq_vec[1] - s1_yb \
            + 2*L1*ddq_vec[0]*math.cos(q_vec[1]) \
            + L1*ddq_vec[1]*math.cos(q_vec[1])
    y_1_7 = ddq_vec[0]*L1**2 + g*math.sin(q_vec[0])*L1
    y_1_8 = ddq_vec[0] + ddq_vec[1]
    y_1_9 = 0
    y_1_10 = 0

    y_2_1 = 0
    y_2_2 = 0
    y_2_3 = 0
    y_2_4 = 0
    y_2_5 = ddq_vec[0]*n + ddq_vec[1]*n**2
    y_2_6 = L1*math.sin(q_vec[1])*dq_vec[0]**2 - s1_yb \
            + L1*ddq_vec[0]*math.cos(q_vec[1])
    y_2_7 = 0
    y_2_8 = ddq_vec[0] + ddq_vec[1]
    y_2_9 = math.atan(50*dq_vec[1])
    y_2_10 = dq_vec[1]

    yb = np.array([[y_1_1, y_1_2, y_1_3, y_1_4, y_1_5, y_1_6, y_1_7, y_1_8, y_1_9, y_1_10],
                  [y_2_1, y_2_2, y_2_3, y_2_4, y_2_5, y_2_6, y_2_7, y_2_8,  y_2_9,  y_2_10]])
    return yb


def build_identification_matrices(g, n, L1, num_params, measured_data_filepath):
    """
    g: float
        gravity
    n: int
        gear ratio
    L1: float
        length of first link
    """
    data = pd.read_csv(measured_data_filepath)
    print("Measured Data Shape = ", data.shape)
    time = data["time"].tolist()
    shoulder_pos = data["shoulder_pos"].tolist()
    shoulder_vel = data["shoulder_vel"].tolist()
    shoulder_trq = data["shoulder_torque"].tolist()

    elbow_pos = data["elbow_pos"].tolist()
    elbow_vel = data["elbow_vel"].tolist()
    elbow_trq = data["elbow_torque"].tolist()

    (filtered_time,
     filtered_shoulder_pos,
     filtered_elbow_pos,
     filtered_shoulder_vel,
     filtered_elbow_vel,
     filtered_shoulder_acc,
     filtered_elbow_acc,
     filtered_shoulder_trq,
     filtered_elbow_trq) = smooth_data_butter(time,
                                              shoulder_pos,
                                              shoulder_vel,
                                              shoulder_trq,
                                              elbow_pos,
                                              elbow_vel,
                                              elbow_trq,
                                              )

    num_samples = len(filtered_time)
    phi = np.empty((num_samples*2, num_params))
    Q = np.empty((num_samples*2, 1))
    b = 0
    for i in range(num_samples):
        # Q contains measured torques of both joints for every time step (target)
        Q[b:b+2, 0] = np.array([filtered_shoulder_trq[i], elbow_trq[i]])
        q_vec = np.array([filtered_shoulder_pos[i], filtered_elbow_pos[i]])
        dq_vec = np.array([filtered_shoulder_vel[i], filtered_elbow_vel[i]])
        ddq_vec = np.array([filtered_shoulder_acc[i], filtered_elbow_acc[i]])
        # phi contains the regressor matrix (yb) for every time step
        phi[b:b+2, :] = yb_matrix(g, n, L1, q_vec, dq_vec, ddq_vec)
        b += 2
    # r = np.linalg.matrix_rank(phi, tol=0.1)
    # print("rank:", r)
    return Q, phi
