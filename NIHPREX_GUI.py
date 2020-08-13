"""
Python implementation of a GUI to interact with the redesign of the NIH P-Rex (FAB Lab Exoskeleton).

Tested with Python 3.7.3 interpreter.

This GUI will receive and save data over wire or over Bluetooth. It should operate at around 20kHz during data
collection. System was tested with Pybluez 0.22, which requires the following build tools on Windows 10.

Pybluez Build Tools: [Visual Studio Build Tools 2017, Windows SDK AddOn, Windows Software Development Kit - Windows]

As of December 2019, additional versions of Pybluez have been released that are easier to install, though these have
not been tested with this system.

Plotting of data is performed on the backend, after sending data to Lab Streaming Layer (LSL), so as to avoid slowing
down operating ability on the front end (faster data receiving/saving). Reference unity_plotting for data plotting, it's
called as an executable towards the beginning of this script.

IMPORTANT INSTRUCTIONS:
Before Use:
1) Make sure all the libraries imported below are installed in your Python.
2) Reset Teensy (microcontroller) so it starts up and looks for a settings string.

During Use:
3) Update and click 'Save' on LabRecorder11.b. Otherwise the data WILL NOT BE SAVED.
4) Check plots periodically.
"""

import time
import tkinter as tk
from tkinter import *
from tkinter import scrolledtext
from tkinter import ttk
import os.path

myDir = os.path.normpath(".pylsl")
import sys

sys.path.append(myDir)
from pylsl import StreamInfo
from pylsl import StreamOutlet
import serial
import subprocess

# Library Note: pybluez is only loaded if Bluetooth is chosen later on

# if a library is misplaced (outside of your typical python library), you can use code the below to import it
# import os.path
# myDir2 = os.path.normpath("/Users/lukeandrewtucker/Library/Python/2.7/site-packages/pyserial-3.4")
# sys.path.append(myDir2)

# Really nifty way to figure out which lines run too slow. Add "@profile" above a function you want to profile.
# import line_profiler
# profile = line_profiler.LineProfiler()
# # builtins.__dict__['profile'] = prof
# import atexit
# atexit.register(profile.print_stats)


# ============================= external executables ==================================================================
# Lab Recorder Application
# lab_recorder_subprocess = subprocess.Popen(os.path.normpath("./LabRecorder/LabRecorder.exe"))

# Unity Plotting Application
# plotting_subprocess = subprocess.Popen(os.path.normpath("./backend_plotting/Static Grip Device.exe"))

# ============================ important string info ==================================================================
# important characters for interfacing with GUI
prompt_char = "^"
trial_start_char = "$"
trial_stop_char = "@"
end_string = '\n'

# ============================ globals ================================================================================

global control_type  # type of control (torque control, impedance control, etc.)
global fsm_type  # finite state machine type. (2 states, 3 states, 4 states, etc.)
old_fsm_option = 0  # set this to whatever fsm_option starts on ('0' == 2 states)
old_controller_option = 0  # set this to whatever controller_option starts on
global test_button  # tracks which test button has been selected (motor, torq control, imped control, etc.) (5-9)
global page  # which page the GUI is on (Instructions, Prelim Testing, Run Trial, etc.)
old_torq_option = 0  # tracks what the previous torq option was to know what buttons to delete
old_imped_option = 0  # tracks what the previous imped option was to know what buttons to delete
old_option_motor = 0  # tracks what the previous option_motor was to know what buttons to delete


# ======================== Functions to construct string for Arduino ==================================================
""" For an overview of what the following "contruct___()" functions do, 
visit: https://github.com/NIHFAB/PREX-GUI-FAB/wiki , section 3a. Function to Encode Communication String
"""

def construct_data_string_left():  # pulls data from buttons and formats into proper string, separated with '/'
    """ This function pulls data from the GUI widgets and formats into a single string (settsStrML), which can then be
    sent to Arduino code. The delimiter is a forward slash ("/"), and each string begins with a "10" to tell the
    exoskeleton to enter the state machine and begin a trial. This structure is mirrored in Button_Parameters.ino
    (to decode the string) for reference. The names for the strings pulled from widgets exactly match the variable
    names in the Arduino code (exo_teensy_menu___.09).
    """
    global settsStrML
    global fsm_type
    global control_type

    fsm_type = str(main.p1.FSMOPTIONS.get())  # pulls data out of FSMOPTIONS entry widget
    control_type = str(main.p1.CONTROLLEROPTIONS.get())
    sendgains = main.p1.SENDGAINSONOFF.get()
    save_settings_oi_s = str(main.p1.SAVESETTINGS.get())  # str(main.p1.SAVESETTINGS.get()) # 0 is no, 1 is yes

    if fsm_type == "0" and control_type == "0":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        states_2_FSM_stance_torq_setpoint_left = str(main.p1.STANCESET_LEFT.get())
        states_2_FSM_swing_torq_setpoint_left = str(main.p1.SWINGSET_LEFT.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + states_2_FSM_stance_torq_setpoint_left + "/" \
                     + states_2_FSM_swing_torq_setpoint_left + "/" + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing + settsStrG

    elif fsm_type == "1" and control_type == "0":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        states_3_FSM_stance_torq_setpoint_left = str(main.p1.STANCESET_LEFT.get())
        states_3_FSM_early_swing_torq_setpoint_left = str(main.p1.ESWINGSET_LEFT.get())
        states_3_FSM_late_swing_torq_setpoint_left = str(main.p1.LSWINGSET_LEFT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + states_3_FSM_stance_torq_setpoint_left + "/" \
                     + states_3_FSM_early_swing_torq_setpoint_left + "/" + states_3_FSM_late_swing_torq_setpoint_left + "/" \
                     + motor_vel_thresh_swing_s + "/" + estim_onoff_s_stance + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "2" and control_type == "0":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        states_4_FSM_early_stance_torq_setpoint_left = str(main.p1.ESTANCESET_LEFT.get())
        states_4_FSM_late_stance_torq_setpoint_left = str(main.p1.LSTANCESET_LEFT.get())
        states_4_FSM_early_swing_torq_setpoint_left = str(main.p1.ESWINGSET_LEFT.get())
        states_4_FSM_late_swing_torq_setpoint_left = str(main.p1.LSWINGSET_LEFT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + states_4_FSM_early_stance_torq_setpoint_left + "/" \
                     + states_4_FSM_late_stance_torq_setpoint_left + "/" \
                     + states_4_FSM_early_swing_torq_setpoint_left + "/" + states_4_FSM_late_swing_torq_setpoint_left + "/" \
                     + motor_vel_thresh_swing_s + "/" + motor_vel_thresh_e2mstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "3" and control_type == "0":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        states_5_FSM_early_stance_torq_setpoint_left = str(main.p1.ESTANCESET_LEFT.get())
        states_5_FSM_mid_stance_torq_setpoint_left = str(main.p1.MSTANCESET_LEFT.get())
        states_5_FSM_late_stance_torq_setpoint_left = str(main.p1.LSTANCESET_LEFT.get())
        states_5_FSM_early_swing_torq_setpoint_left = str(main.p1.ESWINGSET_LEFT.get())
        states_5_FSM_late_swing_torq_setpoint_left = str(main.p1.LSWINGSET_LEFT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + states_5_FSM_early_stance_torq_setpoint_left + "/" \
                     + states_5_FSM_mid_stance_torq_setpoint_left + "/" + states_5_FSM_late_stance_torq_setpoint_left + "/" \
                     + states_5_FSM_early_swing_torq_setpoint_left + "/" + states_5_FSM_late_swing_torq_setpoint_left + "/" \
                     + motor_vel_thresh_swing_s + "/" + motor_vel_thresh_e2mstance_s + "/" \
                     + motor_vel_thresh_m2Lstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "0" and control_type == "1":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + closeness_thresh + "/" + virtual_wall_thresh + "/" + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing + settsStrG

    elif fsm_type == "1" and control_type == "1":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + virtual_wall_thresh + "/" + estim_onoff_s_stance + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "2" and control_type == "1":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + virtual_wall_thresh + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "3" and control_type == "1":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + motor_vel_thresh_m2Lstance_s + "/" \
                     + virtual_wall_thresh + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "0" and control_type == "2":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + \
                     "/" + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing

    elif fsm_type == "1" and control_type == "2":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                         + estim_onoff_s_stance + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing

    elif fsm_type == "2" and control_type == "2":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance\
                     + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing

    elif fsm_type == "3" and control_type == "2":
        fsr_thresh_left = str(main.p1.FSRTHRESH_LEFT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrML = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_left + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + motor_vel_thresh_m2Lstance_s + "/" \
                     + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing

    return settsStrML


def construct_data_string_right():  # pulls data from buttons and formats into proper string, separated with '/'
    """ This function pulls data from the GUI widgets and formats into a single string (settsStrML), which can then be
    sent to Arduino code. The delimiter is a forward slash ("/"), and each string begins with a "10" to tell the
    exoskeleton to enter the state machine and begin a trial. This structure is mirrored in Button_Parameters.ino
    (to decode the string) for reference. The names for the strings pulled from widgets exactly match the variable
    names in the Arduino code (exo_teensy_menu___.09).
    """

    global settsStrMR
    global fsm_type
    global control_type

    fsm_type = str(main.p1.FSMOPTIONS.get())  # pulls data out of FSMOPTIONS entry widget
    control_type = str(main.p1.CONTROLLEROPTIONS.get())
    sendgains = main.p1.SENDGAINSONOFF.get()
    save_settings_oi_s = str(main.p1.SAVESETTINGS.get())  # str(main.p1.SAVESETTINGS.get()) # 0 is no, 1 is yes

    if fsm_type == "0" and control_type == "0":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        states_2_FSM_stance_torq_setpoint_right = str(main.p1.STANCESET_RIGHT.get())
        states_2_FSM_swing_torq_setpoint_right = str(main.p1.SWINGSET_RIGHT.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + states_2_FSM_stance_torq_setpoint_right + "/" \
                     + states_2_FSM_swing_torq_setpoint_right + "/" + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing + settsStrG

    elif fsm_type == "1" and control_type == "0":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        states_3_FSM_stance_torq_setpoint_right = str(main.p1.STANCESET_RIGHT.get())
        states_3_FSM_early_swing_torq_setpoint_right = str(main.p1.ESWINGSET_RIGHT.get())
        states_3_FSM_late_swing_torq_setpoint_right = str(main.p1.LSWINGSET_RIGHT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + states_3_FSM_stance_torq_setpoint_right + "/" \
                     + states_3_FSM_early_swing_torq_setpoint_right + "/" + states_3_FSM_late_swing_torq_setpoint_right + "/" \
                     + motor_vel_thresh_swing_s + "/" + estim_onoff_s_stance + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "2" and control_type == "0":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        states_4_FSM_early_stance_torq_setpoint_right = str(main.p1.ESTANCESET_RIGHT.get())
        states_4_FSM_late_stance_torq_setpoint_right = str(main.p1.LSTANCESET_RIGHT.get())
        states_4_FSM_early_swing_torq_setpoint_right = str(main.p1.ESWINGSET_RIGHT.get())
        states_4_FSM_late_swing_torq_setpoint_right = str(main.p1.LSWINGSET_RIGHT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + states_4_FSM_early_stance_torq_setpoint_right + "/" \
                     + states_4_FSM_late_stance_torq_setpoint_right + "/" \
                     + states_4_FSM_early_swing_torq_setpoint_right + "/" + states_4_FSM_late_swing_torq_setpoint_right + "/" \
                     + motor_vel_thresh_swing_s + "/" + motor_vel_thresh_e2mstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "3" and control_type == "0":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        states_5_FSM_early_stance_torq_setpoint_right = str(main.p1.ESTANCESET_RIGHT.get())
        states_5_FSM_mid_stance_torq_setpoint_right = str(main.p1.MSTANCESET_RIGHT.get())
        states_5_FSM_late_stance_torq_setpoint_right = str(main.p1.LSTANCESET_RIGHT.get())
        states_5_FSM_early_swing_torq_setpoint_right = str(main.p1.ESWINGSET_RIGHT.get())
        states_5_FSM_late_swing_torq_setpoint_right = str(main.p1.LSWINGSET_RIGHT.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        if sendgains == 1:
            kp_torq_s = str(main.p1.PGAIN.get())
            ip_torq_s = str(main.p1.IGAIN.get())
            dp_torq_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + states_5_FSM_early_stance_torq_setpoint_right + "/" \
                     + states_5_FSM_mid_stance_torq_setpoint_right + "/" + states_5_FSM_late_stance_torq_setpoint_right + "/" \
                     + states_5_FSM_early_swing_torq_setpoint_right + "/" + states_5_FSM_late_swing_torq_setpoint_right + "/" \
                     + motor_vel_thresh_swing_s + "/" + motor_vel_thresh_e2mstance_s + "/" \
                     + motor_vel_thresh_m2Lstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "0" and control_type == "1":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + closeness_thresh + "/" + virtual_wall_thresh + "/" \
                     + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing + settsStrG

    elif fsm_type == "1" and control_type == "1":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + virtual_wall_thresh + "/" + estim_onoff_s_stance + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "2" and control_type == "1":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + virtual_wall_thresh + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "3" and control_type == "1":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        closeness_thresh = str(main.p1.CLOSENESS.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())

        if sendgains == 1:
            kp_pos_s = str(main.p1.PGAIN.get())
            ip_pos_s = str(main.p1.IGAIN.get())
            dp_pos_s = str(main.p1.DGAIN.get())
            gains_oi = "1"

            settsStrG = "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s
        elif sendgains == 0:
            settsStrG = ''
            gains_oi = "0"

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + closeness_thresh + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + motor_vel_thresh_m2Lstance_s + "/" \
                     + virtual_wall_thresh + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing + settsStrG

    elif fsm_type == "0" and control_type == "2":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_swing = str(main.p1.estimSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + \
                     "/" + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_swing


    elif fsm_type == "1" and control_type == "2":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        estim_onoff_s_stance = str(main.p1.estimStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                     + estim_onoff_s_stance + "/" \
                     + estim_onoff_s_early_swing + "/" + estim_onoff_s_late_swing

    elif fsm_type == "2" and control_type == "2":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + estim_onoff_s_early_stance + "/" + estim_onoff_s_late_stance\
                     + "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing

    elif fsm_type == "3" and control_type == "2":
        fsr_thresh_right = str(main.p1.FSRTHRESH_RIGHT.get())
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())
        motor_vel_thresh_swing_s = str(main.p1.MOTORSWINGTHRESH.get())
        motor_vel_thresh_e2mstance_s = str(main.p1.MOTORE2MSTANCETHRESH.get())
        motor_vel_thresh_m2Lstance_s = str(main.p1.MOTORM2LSTANCETHRESH.get())
        estim_onoff_s_early_stance = str(main.p1.estimEarlyStanceVariable.get())
        estim_onoff_s_middle_stance = str(main.p1.estimMiddleStanceVariable.get())
        estim_onoff_s_late_stance = str(main.p1.estimLateStanceVariable.get())
        estim_onoff_s_early_swing = str(main.p1.estimEarlySwingVariable.get())
        estim_onoff_s_late_swing = str(main.p1.estimLateSwingVariable.get())
        gains_oi = "0"  # no PID gains for this controller mode

        settsStrMR = "10/" + fsm_type + "/" + control_type + "/" + gains_oi + "/" + save_settings_oi_s + "/" \
                     + fsr_thresh_right + "/" + adaptive_weight + "/" + theta_WA + "/" \
                     + change_in_theta_WA + "/" + theta_MS + "/" \
                     + assist_percentage + "/" + motor_vel_thresh_swing_s + "/" \
                     + motor_vel_thresh_e2mstance_s + "/" + motor_vel_thresh_m2Lstance_s + "/" \
                     + estim_onoff_s_early_stance + "/" + estim_onoff_s_middle_stance + "/" \
                     + estim_onoff_s_late_stance + \
                     "/" + estim_onoff_s_early_swing + "/" \
                     + estim_onoff_s_late_swing
    return settsStrMR


def construct_test_param_string():  # pulls data from buttons and formats into proper string, separated with '/'
    """This method pulls data from page two (Testing Parameters) and packages them into a single string (settsStrM) for
    the Arduino code, depending on which button is selected on the Main Menu page. The names for the strings
    pulled from widgets exactly match the variable names in the Arduino code (exo_teensy_menu___.09). This method
    is very similar to construct_data_string, except these parameters are only for pretrial testing, not for running
    a full trial. The delimeter is a forward slash "/" and the numbers at the beginning indicate to the exoskeleton
    what menu setting has been chosen (5 is for motor testing, 6 is for torque controller testing, etc.)"""

    global settsStrM
    global fsm_type
    global control_type
    global test_button

    option_motor = str(main.p2.MOTOROPTIONS.get())  # const, ramp, sine wave
    option_controller = str(main.p2.TORQOPTIONS.get())  # const, stepwise, sine wave
    option_impedance = str(main.p2.IMPEDOPTIONS.get())  # static, sweep (closeness), sweep (time based)

    if test_button == 5 and (option_motor == "0" or option_motor == "1"):  # for option_motor == 0 or 1
        amps = str(main.p2.MOCURRENT.get())  # motor current

        settsStrM = "5/" + option_motor + "/" + amps

    elif test_button == 5 and option_motor == "2":  # motor
        sine_amps = str(main.p2.MOCURRENT.get())  # motor current
        sine_hz = str(main.p2.MOFREQ.get())
        offset_amps_sine = str(main.p2.MOCURROFFSET.get())

        settsStrM = "5/" + option_motor + "/" + sine_hz + "/" + sine_amps + "/" + offset_amps_sine

    elif test_button == 6 and option_controller == "0":  # torque controller
        t_setpoint = str(main.p2.TORQ.get())

        settsStrM = "6/" + option_controller + "/" + t_setpoint

    elif test_button == 6 and option_controller == "1":
        interval_t = str(main.p2.TIMESTEP.get())
        torq_step_s = str(main.p2.TORQ.get())

        settsStrM = "6/" + option_controller + "/" + interval_t + "/" + torq_step_s

    elif test_button == 6 and option_controller == "2":
        sine_torq_hlimit = str(main.p2.TORQUL.get())
        sine_torq_llimit = str(main.p2.TORQLL.get())
        time_length = str(main.p2.WAVET.get())

        settsStrM = "6/" + option_controller + "/" + sine_torq_hlimit + "/" + sine_torq_llimit + "/" + time_length

    elif test_button == 7 and option_impedance == "0":  # impedance controller
        virtual_wall_thresh = str(main.p1.VIRWALL.get())
        setpoint_pos = str(main.p2.IMPEDANGLE.get())

        settsStrM = "7/" + option_impedance + "/" + virtual_wall_thresh + "/" + setpoint_pos

    elif test_button == 7 and option_impedance == "1":  # impedance controller, closeness based
        closeness_thresh = str(main.p1.CLOSENESS.get())
        option_sweep = "0"
        option_impedance = "1"  # change to 1 for arduino code

        settsStrM = "7/" + option_impedance + "/" + option_sweep + "/" + closeness_thresh

    elif test_button == 7 and option_impedance == "2":  # impedance controller, time based
        impedance_sweep_test_t_switch = str(main.p2.TIMEBTSWEEP.get())
        option_sweep = "1"
        option_impedance = "1"  # change to 1 for arduino code

        settsStrM = "7/" + option_impedance + "/" + option_sweep + "/" + impedance_sweep_test_t_switch

    elif test_button == 8:  # adaptive controller (still need to rewrite arduino code for this to work)
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())

        settsStrM = "8/" + adaptive_weight + "/" + theta_WA + "/" \
                    + change_in_theta_WA + "/" + theta_MS + "/" \
                    + assist_percentage

    elif test_button == 9:  # speed controller
        Setpoint_vel = str(main.p2.SPEED.get())
        time_to_run = str(main.p2.RUNTIME.get())

        settsStrM = "9/" + Setpoint_vel + "/" + time_to_run

    return settsStrM


def construct_gains_string():
    """This function constructs the settings string 'settsStrG', which contains controller gains. For most controllers,
    these are PID gains. For adaptive control, these are weight, angle thresholds and desired assistance"""
    global settsStrG
    global test_button

    gains_menu_opt = main.p2.CONGAINSOPT.get()
    if gains_menu_opt == "Torque":
        gains_controller_opt = 6
    elif gains_menu_opt == "Impedance":
        gains_controller_opt = 7
    elif gains_menu_opt == "Adaptive":
        gains_controller_opt = 8
    elif gains_menu_opt == "Speed":
        gains_controller_opt = 9

    if gains_controller_opt == 6:  # torque controller
        controller_type = "g/6"
        kp_torq_s = str(main.p2.PGAIN.get())
        ip_torq_s = str(main.p2.IGAIN.get())
        dp_torq_s = str(main.p2.DGAIN.get())

        settsStrG = controller_type + "/" + kp_torq_s + "/" + ip_torq_s + "/" + dp_torq_s

    elif gains_controller_opt == 7:  # impedance controller
        controller_type = "g/7"
        kp_pos_s = str(main.p2.PGAIN.get())
        ip_pos_s = str(main.p2.IGAIN.get())
        dp_pos_s = str(main.p2.DGAIN.get())

        settsStrG = controller_type + "/" + kp_pos_s + "/" + ip_pos_s + "/" + dp_pos_s

    elif gains_controller_opt == 9:  # velocity controller
        controller_type = "g/9"
        kp_vel_s = str(main.p2.PGAIN.get())
        ip_vel_s = str(main.p2.IGAIN.get())
        dp_vel_s = str(main.p2.DGAIN.get())

        settsStrG = controller_type + "/" + kp_vel_s + "/" + ip_vel_s + "/" + dp_vel_s

    elif gains_controller_opt == 8:  # adaptive controller
        controller_type = "g/8"
        adaptive_weight = str(main.p1.WEIGHT.get())
        theta_WA = str(main.p1.PEAKFLEXION.get())
        change_in_theta_WA = str(main.p1.KNEEROM.get())
        theta_MS = str(main.p1.STANCEMIN.get())
        assist_percentage = str(main.p1.DESASSIST.get())

        settsStrG = controller_type + "/" + adaptive_weight + "/" + theta_WA + "/" \
                    + change_in_theta_WA + "/" + theta_MS + "/" \
                    + assist_percentage

    return settsStrG


def construct_pot_string(leg):
    """This functions collects the settings for setting the potentiometer calibration for each leg of the exo."""
    if leg == 'L':
        left_pot_0 = str(main.p2.LPOTLOW.get())
        left_pot_90 = str(main.p2.LPOTHIGH.get())
        settsStrP = "P/" + left_pot_0 + "/" + left_pot_90
    elif leg == 'R':
        right_pot_0 = str(main.p2.RPOTLOW.get())
        right_pot_90 = str(main.p2.RPOTHIGH.get())
        settsStrP = "P/" + right_pot_0 + "/" + right_pot_90

    return settsStrP


# ======================= establish communication (Bluetooth or Serial) connections ====================================
global comType
global ser
global ser1
global client_socket
global client_socket1
global size


def connect_to_exo(comType, address1, address2):
    """This function establishes a connection with the exo, either over bluetooth or over a wire by connecting to
    the serial port of a Teensy. comType = 'Ser'  # set to either 'BLE' or 'Ser' (bluetooth or serial (wire via usb))
    This function is called by the 'Wire' and 'Bluetooth' buttons on the GUI."""

    print("syncing...")
    if comType == 'Ser':
        global ser
        global ser1

        ser = serial.Serial(address1, 115200, timeout=0, bytesize=8, stopbits=1, parity='N')  # left leg
        # ser.write(b'-99')
        print("Left leg Connected ")
        main.SERCONBOX['text'] = "Connection Confirmation:\nLeft Leg Connected!"
        ser1 = serial.Serial(address2, 115200, timeout=0, bytesize=8, stopbits=1, parity='N')  # right leg
        # ser1.write(b'-99')
        main.SERCONBOX['text'] = "Connection Confirmation:\nLeft Leg Connected!\nRight Leg Connected!"
        print("Right leg Connected!")

    elif comType == 'BLE':
        import bluetooth
        # mac address from GUI
        serverMACAddress = address1
        serverMACAddress1 = address2

        global client_socket
        global client_socket1
        global size

        client_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # left leg
        client_socket1 = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # right leg
        size = 1  # set to 1. This way, only 1 byte is received at a time. Otherwise end character will be found too
        # late and print incorrectly.
        time2Receive = 3  # 3 seconds, time until Bluetooth .connect() stops trying to connect

        # connect to sockets
        client_socket.connect((serverMACAddress, 1))  # establish connection
        client_socket.settimeout(time2Receive)  # increase timeout for connection to be established
        client_socket.setblocking(
            0)  # make socket non-blocking; otherwise, if receives 0 bytes, will stall whole program
        print("Left leg Connected ")
        main.BLECONBOX['text'] = "Connection Confirmation:\nLeft Leg Connected!"
        client_socket1.connect((serverMACAddress1, 1))
        client_socket1.settimeout(time2Receive)
        client_socket1.setblocking(0)
        print("Right leg Connected ")
        main.BLECONBOX['text'] = "Connection Confirmation:\nLeft Leg Connected!\nRight Leg Connected!"


# ================================ setup LabStreamingLayer (LSL) streams ==============================================
"""Lab Streaming Layer is an open source project that handles, amongst other things, networking & time-synchronization 
of measurement time series. Two streams are created in this project; a right leg and a left leg stream. Each stream 
contains 8 pieces of data, including things such as time, angle, and torque. Data are pushed to these streams in 
receive_ser_data_and_send2LSL() and receive_BLE_data_and_send2LSL().
"""
# == Right Leg LSL ===
info_RL = StreamInfo('RightLeg', 'Exoskeleton', 8, 100, 'float32', 'YourComp')  # creates 8 channel LSL stream

# append some meta-data
channels = info_RL.desc().append_child("channels")
for c in ["TimeRL", "AngleRL", "TorqueRL", "FSR RL", "CurrentRL", "FSM StateRL", "Torque SetpointRL",
          "Position SetpointRL"]:
    channels.append_child("channel") \
        .append_child_value("label", c)

outlet_RL = StreamOutlet(info_RL)  # creates outlet for right leg

# == Left Leg LSL ===
info_LL = StreamInfo('LeftLeg', 'Exoskeleton', 8, 100, 'float32', 'YourComp')  # creates 8 channel LSL stream

# append some meta-data
channels = info_LL.desc().append_child("channels")
for c in ["TimeLL", "AngleLL", "TorqueLL", "FSR LL", "CurrentLL", "FSM StateLL", "Torque SetpointLL",
          "Position SetpointLL"]:
    channels.append_child("channel") \
        .append_child_value("label", c)

outlet_LL = StreamOutlet(info_LL)  # creates outlet for left leg

# =================================== Globals for receiving/saving data ===============================================
# these variables break out of the receiving data loops when the appropriate buttons are selected
# These might seem excessive, but they stand for the different ways the receiving protocol needs to finish:
# 1) When communication from Arduino is over,
# 2) When a trial is starting/stopping (data saved versus not saved), and
# 3) When the 'stop' button is selected.

received_data_L = ""  # data received from left leg Teensy
received_data_R = ""  # data received from right leg Teensy
buttons_state = "on"  # GUI buttons state to define interaction b/t Application and receive_data.
L_state = 'rec'  # 'receiving', for conditionals, so one leg's data can be received even when the other is finished
R_state = 'rec'  # 'receiving'
switch2Save = False  # variable to switch from receive_serial_data to receive_serial_dataAndSend2LSL. Ends receive_serial_data
trial_start_L = False  # variable to indicate start of a trial from left leg
trial_start_R = False  # variable to indicate start of a trial from right leg
trial_stop_L = False  # variable to indicate stop of a trial from left leg
trial_stop_R = False  # variable to indicate stop of a trial from right leg


# ================== Universal communication functions (BLE or Ser) ===========================
"""For an overview of how the receive___() and send___() functions work with the rest of the code, vist
https://github.com/NIHFAB/PREX-GUI-FAB/wiki , 3b. Function to Send Data over Bluetooth, and 
2. Receive and Parse Data (Python)
"""

def receive_data():
    """Universal function to received data, either from bluetooth or wire."""
    global comType

    if comType == 'Ser':  # from wire
        receive_serial_data()
    elif comType == 'BLE':  # from bluetooth
        receive_ble_data()


def send_data(data, prefix='Y', parse='Y',
              leg='B'):  # no parse for immediate commands, like stop, walking, standby, etc.
    """Universal function to send data, either to Bluetooth or wire.
    'Parse' adds a prefix of data length to the communication."""
    global comType
    # leg denotes with leg to send to; L = left, R = right, B = both
    if comType == 'Ser':
        if parse == 'Y':  # send length of data before data, and parse with ~ and >
            data = str(len(data)) + '~' + data + '>'
        dataB = bytes(data, encoding='utf-8')  # converts strings to binary
        if leg == 'B':
            ser.write(dataB)  # left
            ser1.write(dataB)  # right
        elif leg == 'L':  # L and R used for calibrating potentiometers
            ser.write(dataB)
        elif leg == 'R':
            ser1.write(dataB)

    elif (comType == 'BLE'):  # and (prefix == 'Y'):
        if parse == 'Y':
            data = str(len(data)) + '~' + data + '>'
        # dataP = ">" + data  # prefixes data with '>', as Arduino expects
        if leg == 'B':
            client_socket.send(data)  # left
            client_socket1.send(data)  # right
        elif leg == 'L':  # L and R used for calibrating potentiometers
            client_socket.send(data)
        elif leg == 'R':
            client_socket1.send(data)


def receive_and_save_data():
    """Universal function for receiving and saving data, either over bluetooth or wire."""
    global comType

    if comType == 'Ser':
        receive_ser_data_and_send2LSL()
    elif comType == 'BLE':
        receive_ble_data_and_send2LSL()


def start_trial():
    message = "Click 'Start Trial' to begin. DATA WILL NOT PRINT DURING A TRIAL. Check the graphing application to monitor data. \n"
    main.p1.LeftConsole.insert(INSERT, message)  # insert text to scrolled text widget
    main.p1.LeftConsole.see("end")  # autoscroll to bottom
    main.p1.RightConsole.insert(INSERT, message)  # insert text to scrolled text widget
    main.p1.RightConsole.see("end")  # autoscroll to bottom


# def stop_trial():
#     message = "Click 'Continue' to run another trial, or 'Finish' to finish trial. \n"
#     main.p1.LeftConsole.insert(INSERT, message)  # insert text to scrolled text widget
#     main.p1.LeftConsole.see("end")  # autoscroll to bottom
#     main.p1.RightConsole.insert(INSERT, message)  # insert text to scrolled text widget
#     main.p1.RightConsole.see("end")  # autoscroll to bottom


# ================= Serial communication functions ==================================
"""For an overview of how the following receive____() functions parse and save data, visit
https://github.com/NIHFAB/PREX-GUI-FAB/wiki , 2. Receive and Parse Data (Python) and 3. Save Data
"""

def receive_serial_data():
    """INPUT: None (uses received_data_L and received_data_R, but these are globals)
    OUTPUT: Prints received serial data to console, and to tkinter GUI

    Menu communication is over when '^\n' has been received. That's what all these conditionals are checking for.
    A line is over when '\n' has been received. This function waits until '^\n' has been received: otherwise,
    it reads data indefinitely."""

    global ser
    global ser1

    global received_data_L
    global received_data_R
    global L_state
    L_state = 'rec'  # reset these every time 'receive_data' is called
    global R_state
    R_state = 'rec'
    global buttons_state  # to know button states for app object (GUI state)
    buttons_state = "on"
    global switch2Save
    switch2Save = False
    global trial_start_L
    trial_start_L = False
    global trial_start_R
    trial_start_R = False
    global page

    while (L_state == 'rec' or R_state == 'rec') and buttons_state == 'on' and (switch2Save == False):
        # L & R states are changed by finding end communication characters; buttons_state is changed by 'stop' button
        main.update()
        # === receiving & decoding of data ====
        data_L = ser.read(1)  # limits buffer size to 1 byte: controls data flow since whatever
        data_L = data_L.decode('utf-8')  # decodes characters according to utf-8
        received_data_L = received_data_L + data_L  # adds up characters until newline character is received

        data_R = ser1.read(1)
        data_R = data_R.decode('utf-8')
        received_data_R = received_data_R + data_R

        # == checks for end_string (end communication) and prints ====
        if end_string in received_data_L and L_state != 'fin':
            # send text to it's respective locations
            if page == "trialpage":
                main.p1.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
                main.p1.LeftConsole.see("end")  # autoscroll to bottom
            elif page == "testpage":
                main.p2.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
                main.p2.LeftConsole.see("end")  # autoscroll to bottom

            if prompt_char in received_data_L and end_string in received_data_L:  # these lines stopped ability to input
                L_state = 'fin'
            if trial_start_char in received_data_L:
                trial_start_L = True
            received_data_L = ""
            main.update()

        if end_string in received_data_R and R_state != 'fin':
            if page == "trialpage":
                main.p1.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
                main.p1.RightConsole.see("end")  # autoscroll to bottom
            elif page == "testpage":
                main.p2.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
                main.p2.RightConsole.see("end")  # autoscroll to bottom

            if prompt_char in received_data_R and end_string in received_data_R:  # set to 'or' in case one teensy gets
                R_state = 'fin'  # 'finished'                                    # multiple bytes ahead of the other
            if trial_start_char in received_data_R:
                trial_start_R = True
            received_data_R = ""
            main.update()

        # === conditionals to end loop: conditions are prompt character or change in button state or start trial ====
        # checks to see if the prompt character is in communication to end bluetooth sending communication
        if (trial_start_L == True) and (trial_start_R == True):
            start_trial()
            break
        if L_state == 'fin' and R_state == 'fin':  # 'finished'
            main.update()
            break

        main.update()  # updates


def receive_ser_data_and_send2LSL():
    """INPUT: None (uses received_data_L and received_data_R, but these are globals)
    OUTPUT: Sends received serial data to LSL to be saved.

    Menu communication is over when '^\n' has been received. That's what all these conditionals are checking for.
    A line is over when '\n' has been received. This function waits until '^\n' has been received: otherwise,
    it reads data indefinitely."""

    print("receive_serial_dataAndSend2LSL is running... I promise...")

    global ser
    global ser1

    global received_data_L
    global received_data_R
    global L_state
    L_state = 'rec'  # reset these every time 'receive_data' is called
    global R_state
    R_state = 'rec'
    global buttons_state  # to know button states for main object (GUI state)
    buttons_state = "on"
    global trial_stop_L
    trial_stop_L = False
    global trial_stop_R
    trial_stop_R = False

    # counter = 1  # for clocking how fast the GUI works

    main.p1.LeftConsole.insert(INSERT,
                               'Trial is running... press "Finish Trial" to end\n')  # insert text to scrolled text widget
    main.p1.RightConsole.insert(INSERT,
                                'Trial is running... press "Finish Trial" to end\n')  # insert text to scrolled text widget

    while (L_state == 'rec' or R_state == 'rec') and buttons_state == 'on':
        # L & R states are changed by finding end communication characters; buttons_state is changed by 'stop' button
        # === receiving & decoding of data ====
        data_L = ser.read(1)  # limits buffer size to 1 byte: controls data flow since whatever
        data_L = data_L.decode('utf-8')  # decodes characters according to utf-8
        received_data_L = received_data_L + data_L  # adds up characters until newline character is received

        data_R = ser1.read(1)
        data_R = data_R.decode('utf-8')
        received_data_R = received_data_R + data_R

        # outlet_GUI.push_sample([counter])
        # counter += 1

        # === checks for end_string (end communication) and prints ====
        if end_string in received_data_L and L_state != 'fin':
            # send text to it's respective locations
            # main.p1.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
            # main.p1.LeftConsole.see("end")  # autoscroll to bottom. This line takes ridiculously long to execute

            # splits lines into the 8 different data types being received
            data2SaveLL = received_data_L.split("\t")

            try:  # pushes samples to LSL
                data2SaveLL_Floats = [float(i) for i in data2SaveLL]  # converts a list of strings to floats
                outlet_LL.push_sample(data2SaveLL_Floats)
            except Exception:  # value error when '@' symbol is received
                # global trial_stop_L
                trial_stop_L = True
                print("Ending trial, couldn't push to LSL...")
                data2SaveLL = ''

            if prompt_char in received_data_L and end_string in received_data_L:
                L_state = 'fin'
            if trial_stop_char in received_data_L and end_string in received_data_L:
                trial_stop_L = True

            received_data_L = ""
            main.update()

        if end_string in received_data_R and R_state != 'fin':
            # main.p1.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
            # main.p1.RightConsole.see("end")  # autoscroll to bottom. This line takes ridiculously long to execute

            # splits lines into the 8 different data types being received
            data2SaveRL = received_data_R.split("\t")  # parses data by tab character
            try:
                data2SaveRL_Floats = [float(i) for i in data2SaveRL]  # converts strings to floats
                outlet_RL.push_sample(data2SaveRL_Floats)
            except Exception:
                # global trial_stop_R
                trial_stop_R = True
                print("Ending trial, couldn't push to LSL...")
                data2SaveRL = ''

            if prompt_char in received_data_R and end_string in received_data_R:  # set to 'or' in case one teensy gets
                R_state = 'fin'  # 'finished'                                    # multiple bytes ahead of the other
            if trial_stop_char in received_data_R and end_string in received_data_R:
                trial_stop_R = True  # checks for '@' during trial to finish trial

            received_data_R = ""
            main.update()

        # === conditionals to end loop: conditions are prompt character or change in button state ====
        # checks to see if the prompt character is in communication to end bluetooth sending communication or if
        # trial stop character is in communication
        if (trial_stop_L == True) and (trial_stop_R == True):
            main.update()
            received_data_R = ""
            received_data_L = ""
            print("Made it to trail stop evaluations")
            # stop_trial()
            break
        if L_state == 'fin' and R_state == 'fin':  # 'finished'
            main.update()
            print("Ended on this state change")
            break
        # checks to see if buttons have been turned off
        if buttons_state == "off":  # button is turned to 'off' by stop button
            main.update()
            print("Ended cause of comma?")
            break

    print("receive_serial_dataAndSend2LSL finished")


# ======================= Bluetooth communication functions ===========================================================
def receive_ble_data():
    """INPUT: None (uses received_data_L and received_data_R, but these are globals)
    OUTPUT: Prints received bluetooth data to console, and to tkinter GUI

    Menu communication is over when '^\n' has been received. That's what all these conditionals are checking for.
    A line is over when '\n' has been received. This function waits until '^\n' has been received: otherwise,
    it reads data indefinitely."""

    global client_socket
    global client_socket1

    global received_data_L
    global received_data_R
    global L_state
    L_state = 'rec'  # reset these every time 'receive_data' is called
    global R_state
    R_state = 'rec'
    global buttons_state  # to know button states for main object (GUI state)
    buttons_state = "on"
    global switch2Save
    switch2Save = False
    global trial_start_L
    trial_start_L = False
    global trial_start_R
    trial_start_R = False

    global size

    while (L_state == 'rec' or R_state == 'rec') and buttons_state == 'on' and (
            switch2Save == False):
        # L & R states are changed by finding end communication characters; buttons_state is changed by 'stop' button
        main.update()
        # === receiving & decoding of data ====
        try:  # this statement should pass the .recv() call if .recv() receives 0 bytes. Google for more info.
            data_L = client_socket.recv(size)  # limits buffer size to 1 byte: controls data flow since whatever
            # bluetooth protocol doesn't package data like Arduino sends it
            data_L = data_L.decode('utf-8')  # decodes characters according to utf-8
            received_data_L = received_data_L + data_L  # adds up characters until newline character is received

        except OSError as err:
            # print("OS Error: {0}".format(err))
            pass

        try:  # this statement should pass the .recv() call if it receives 0 bytes
            data_R = client_socket1.recv(size)
            data_R = data_R.decode('utf-8')
            received_data_R = received_data_R + data_R

        except OSError as err:
            # print("OS Error: {0}".format(err))
            pass

        # === checks for end_string (end communication) and prints ====
        if end_string in received_data_L and L_state != 'fin':
            # send text to it's respective locations
            if page == "trialpage":
                main.p1.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
                main.p1.LeftConsole.see("end")  # autoscroll to bottom
            elif page == "testpage":
                main.p2.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
                main.p2.LeftConsole.see("end")  # autoscroll to bottom

            if prompt_char in received_data_L and end_string in received_data_L:
                L_state = 'fin'
            if trial_start_char in received_data_L:
                trial_start_L = True
            received_data_L = ""
            main.update()

        if end_string in received_data_R and R_state != 'fin':
            if page == "trialpage":
                main.p1.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
                main.p1.RightConsole.see("end")  # autoscroll to bottom
            elif page == "testpage":
                main.p2.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
                main.p2.RightConsole.see("end")  # autoscroll to bottom

            if prompt_char in received_data_R and end_string in received_data_R:  # set to 'or' in case one teensy gets
                R_state = 'fin'  # 'finished'                                    # multiple bytes ahead of the other
            # if prompt character is received, terminates receive_data()
            if trial_start_char in received_data_R:
                trial_start_R = True
            received_data_R = ""
            main.update()

        # === conditionals to end loop: conditions are prompt character or change in button state or start trial ====
        # checks to see if the prompt character is in communication to end bluetooth sending communication
        if (trial_start_L == True) and (trial_start_R == True):
            start_trial()
            print("ReceiveBLE broke on trial_start variables")
            break
        if L_state == 'fin' and R_state == 'fin':  # 'finished'
            print("receiveBLE broke on state variables")
            main.update()
            break
        # checks to see if buttons have been turned off
        if buttons_state == "off":  # button is turned to 'off' by stop button
            print("ReceiveBLE btroke on button_state")
            main.update()
            break

        main.update()
    print("receive_ble_data finished")


def receive_ble_data_and_send2LSL():
    """INPUT: None (uses received_data_L and received_data_R, but these are globals)
    OUTPUT: Sends received data to LSL to be saved.

    Menu communication is over when '^\n' has been received. That's what all these conditionals are checking for.
    A line is over when '\n' has been received. This function waits until '^\n' has been received: otherwise,
    it reads data indefinitely."""

    print("receive_ble_data_and_send2LSL is running... I promise...")

    global client_socket
    global client_socket1

    global received_data_L
    global received_data_R
    global L_state
    L_state = 'rec'  # reset these every time 'receive_data' is called
    global R_state
    R_state = 'rec'
    global buttons_state  # to know button states for main object (GUI state)
    buttons_state = "on"
    global trial_stop_L
    trial_stop_L = False
    global trial_stop_R
    trial_stop_R = False

    global size

    # counter = 1  # for clocking how fast the GUI collects data, uncomment to use

    main.p1.LeftConsole.insert(INSERT,
                               'Trial is running... press "Finish Trial" to end\n')  # insert text to scrolled text widget
    main.p1.RightConsole.insert(INSERT,
                                'Trial is running... press "Finish Trial" to end\n')  # insert text to scrolled text widget

    while (L_state == 'rec' or R_state == 'rec') and buttons_state == 'on':
        # L & R states are changed by finding end communication characters; buttons_state is changed by 'stop' button
        main.update()

        # === receiving & decoding of data ====
        try:  # this statement should pass the .recv() call if .recv() receives 0 bytes. Google for more info.
            data_L = client_socket.recv(size)  # limits buffer size to 1 byte: controls data flow since whatever
            data_L = data_L.decode('utf-8')  # decodes characters according to utf-8
            received_data_L = received_data_L + data_L  # adds up characters until newline character is received

        except OSError as err:
            # print("OS Error: {0}".format(err))
            pass

        try:  # this statement should pass the .recv() call if it receives 0 bytes
            data_R = client_socket1.recv(size)
            data_R = data_R.decode('utf-8')
            received_data_R = received_data_R + data_R

        except OSError as err:
            # print("OS Error: {0}".format(err))
            pass

        # outlet_GUI.push_sample([counter])  # for clocking how fast the GUI collects data, uncomment to use
        # counter += 1  # uncomment to for clocking how fast GUI collects data

        # === checks for end_string (end communication) and prints ====
        if end_string in received_data_L and L_state != 'fin':
            # send text to it's respective locations
            # main.p1.LeftConsole.insert(INSERT, received_data_L)  # insert text to scrolled text widget
            # main.p1.LeftConsole.see("end")  # autoscroll to bottom. This line takes ridiculously long to execute
            main.update()

            # splits lines into the 8 different data types being received
            data2SaveLL = received_data_L.split("\t")

            try:  # pushes samples to LSL
                data2SaveLL_Floats = [float(i) for i in data2SaveLL]  # converts a list of strings to floats
                outlet_LL.push_sample(data2SaveLL_Floats)
            except ValueError:
                # global trial_stop_L
                trial_stop_L = True
                print("Ending trial...")

            if prompt_char in received_data_L and end_string in received_data_L:
                L_state = 'fin'

            received_data_L = ""  # resets received_data_L for next pass

        if end_string in received_data_R and R_state != 'fin':
            # main.p1.RightConsole.insert(INSERT, received_data_R)  # insert text to scrolled text widget
            # main.p1.RightConsole.see("end")  # autoscroll to bottom. This line takes ridiculously long to execute
            main.update()

            # splits lines into the 8 different data types being received
            data2SaveRL = received_data_R.split("\t")  # parses data by tab character
            try:
                data2SaveRL_Floats = [float(i) for i in data2SaveRL]  # converts strings to floats
                outlet_RL.push_sample(data2SaveRL_Floats)
            except ValueError:
                # global trial_stop_R
                trial_stop_R = True
                print("Ending trial...")

            if prompt_char in received_data_R and end_string in received_data_R:  # set to 'or' in case one teensy gets
                R_state = 'fin'  # 'finished'                                    # multiple bytes ahead of the other

            received_data_R = ""

        main.update()

        # === conditionals to end loop: conditions are prompt character or change in button state ===
        # checks to see if the prompt character is in communication to end bluetooth sending communication or if
        # trial stop character is in communication
        if (trial_stop_L == True) and (trial_stop_R == True):
            main.update()
            received_data_R = ""
            received_data_L = ""
            print("Made it to trail stop evaluations")
            stop_trial()
            break
        if L_state == 'fin' and R_state == 'fin':  # 'finished'
            main.update()
            print("Ended on this state change")
            break
        # checks to see if buttons have been turned off
        if buttons_state == "off":  # button is turned to 'off' by stop button
            main.update()
            print("Ended cause of comma?")
            break

    print("receive_ble_data_and_send2LSL finished")

# ======================= GUI code (Tkinter) ========================================================================
"""For an overview of the funcitonal purpose of the widgets and how they interact with the rest of the code, visit
https://github.com/NIHFAB/PREX-GUI-FAB/wiki , 1. User Text Entry, 2. User Control to Send Text, and
3. Function to Pull Text from Entry Widget and Send Text to Microcontroller
"""

class Page(tk.Frame):
    """Page inherits from tk.Frame, and has children 'LandingPage', 'TestingPage', and 'MainMenuPage', 'EstimPage'.
    Just allows for these children to easily inherit from tk.Frame.
    """
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

    def show(self):  # shows the page selected
        self.lift()


class LandingPage(Page):
    """The landing page is just the page with basic instructions. createWidgets() creates Label and PhotoImage()
    widgets with instructions and fun images.
    """
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        # Page.configure(self, background="white")
        self.landingframe = tk.Frame(self, width=1100, height=700)
        self.landingframe.pack(side=TOP)

        self.createWidgets()

    def createWidgets(self):
        TitleText = "NIH P.Rex GUI"
        self.TITLE = tk.Label(self.landingframe, text=TitleText)
        self.TITLE.config(font=
                          ('TKDefaultFont', 22, 'bold'))
        self.TITLE.place(x=1100 / 2, y=100 / 2, anchor="center")

        SubtitleText = "Pediatric-Robotic Exoskeleton"
        self.SUBTITLE = tk.Label(self.landingframe, text=SubtitleText)
        self.SUBTITLE.config(font=
                             ('TKDefaultFont', 16))
        self.SUBTITLE.place(x=1100 / 2, y=160 / 2, anchor="center")

        AuthorText = "Made By: Luke Tucker"
        self.AUTHORTEXT = tk.Label(self.landingframe, text=AuthorText)
        self.AUTHORTEXT.config(font=
                               ('TKDefaultFont', 16))
        self.AUTHORTEXT.place(x=1100 / 2, y=210 / 2, anchor="center")

        Instructions = ("It is suggested that you start on 'Prelim Tests.' This page contains everything related to "
                        "preliminary testing before \nstarting a trial, such as controller testings, motor testing, and "
                        "sensor checking. \n\nAfter checking all sensors and controllers, move to the 'Trial Menu' page. "
                        "This page is where you set trial parameters,\nsuch as which controller you want to use and desired "
                        "state machine. \n\nImportant Notes: \n1) On the 'Prelim' page, testing the Adaptive Controller pulls "
                        "parameters from the 'Trial' page to save space. \n2) The gains set for any controller during "
                        "preliminary testing will be retained during the trial.\n3) DO NOT move/grab the GUI when data is "
                        "being collected. This will pause the data from being saved.")
        # Instructions = "Test text"
        self.INSTRUCTIONS = tk.Label(self.landingframe, text=Instructions, justify=LEFT)
        self.INSTRUCTIONS.config(font=
                                 ('TKDefaultFont', 16))
        self.INSTRUCTIONS.place(x=1100 / 2, y=250, anchor="center")

        self.nihlogoimage = PhotoImage(file="./graphics/nih_logo_4.png")  # NIH logo
        self.nihlogo = tk.Label(self.landingframe, image=self.nihlogoimage)
        self.nihlogo.place(x=1100 * 4 / 12, y=550, anchor="center")

        self.preximage = PhotoImage(file="./graphics/prex.png")  # Prex logo
        self.prexlogo = tk.Label(self.landingframe, image=self.preximage)
        self.prexlogo.place(x=1100 * 8 / 12, y=550, anchor="center")


class MainMenuPage(Page):
    """ MainMenuPage is the page labeled 'RunTrial' in the actual GUI. The different frames hold the different options
    for each controller/other important groups of settings.

    The create___() and delete____() functions can get lengthy,
    but these are the buttons that track what widgets to create and destroy based on certain options being
    chosen. For instance, if you choose a Constant Torque controller with 2 states, you need different text entry
    widgets that a Constant Torque controller with 4 states. The create____() and delete____() functions make sure the
    proper widgets are displayed.

    Functions such as receive() and uploadsettings2() are commanded by buttons on teh GUI and facilitate communication
    with the the microcontroller.

    createWidgets() creates all of the widgets that are initially displayed on MainMenuPage when instantiated as an
    object.
    """
    trial_num = 1

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)

        self.toprow = tk.Frame(self)
        self.midrow = tk.Frame(self)
        self.botrow = tk.Frame(self)

        self.conoptframe = tk.LabelFrame(self.toprow, text="Controller Options",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.impconframe = tk.LabelFrame(self.toprow, text="Impedance Controller",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.adaconframe = tk.LabelFrame(self.toprow, text="Adaptive Controller",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.torconframe = tk.LabelFrame(self.toprow, text="Constant Torque Controller",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.estimframe = tk.LabelFrame(self.toprow, text="E Stim Options",
                                        font=("TkDefaultFont", 9, "bold"),
                                        padx=10, pady=10)
        self.uniconframe = tk.LabelFrame(self.midrow, text="Universal Controller Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.datcolframe = tk.LabelFrame(self.midrow, text="Data Collection Options",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.leftconsoleframe = tk.LabelFrame(self.botrow, text="Left Leg Output",
                                              font=("TkDefaultFont", 9, "bold"),
                                              padx=10, pady=10)
        self.rightconsoleframe = tk.LabelFrame(self.botrow, text="Right Leg Output",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)

        self.conoptframe.pack(side=LEFT, padx=10, pady=10)
        self.impconframe.pack(side=LEFT, padx=10, pady=10)
        self.adaconframe.pack(side=LEFT, padx=10, pady=10)
        self.torconframe.pack(side=LEFT, padx=10, pady=10)
        self.uniconframe.pack(side=LEFT, padx=10, pady=10)
        self.datcolframe.pack(side=LEFT, padx=10, pady=10)
        self.estimframe.pack(side=LEFT, padx=10, pady=10)
        self.leftconsoleframe.pack(side=LEFT, padx=10, pady=10)
        self.rightconsoleframe.pack(side=LEFT, padx=10, pady=10)

        self.toprow.pack(side=TOP)
        self.midrow.pack(side=TOP)
        self.botrow.pack(side=TOP)

        self.createWidgets()

    # == State option functions ===
    # These functions are for creating/deleting torqsetpoint options
    # depending on how many states are selected.

    # 'Next' and 'Upload' are mutually exclusive, therefore, when one is created, the other is deleted.
    # After uploading settings, a 'Next' button is needed to proceed after a built-in pretrial data check.

    def createUploadButton(self):

        self.deleteNextButton()

        # upload settings button
        self.UPLOADSETTINGS = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.UPLOADSETTINGS["text"] = "Upload Settings"
        self.UPLOADSETTINGS["fg"] = "blue"
        self.UPLOADSETTINGS.config(font=
                                   ('TKDefaultFont', 10, 'bold'))
        self.UPLOADSETTINGS.grid(row=0, column=3)
        self.UPLOADSETTINGS["command"] = self.uploadsettings2

    def deleteUploadButton(self):
        self.UPLOADSETTINGS.destroy()

    def createNextButton(self):

        self.deleteUploadButton()  # destroys upload button

        # upload settings button
        self.NEXT_STEP = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.NEXT_STEP["text"] = "Next"
        self.NEXT_STEP["fg"] = "blue"
        self.NEXT_STEP.config(font=
                              ('TKDefaultFont', 10, 'bold'))
        self.NEXT_STEP.grid(row=0, column=3)
        self.NEXT_STEP["command"] = self.next_step

        # print("About to receive data...")
        receive_data()  # need this here so that after 'Upload Settings' button is deleted, still receive data

    def deleteNextButton(self):
        self.NEXT_STEP.destroy()

    def createStartStopButtons(self):

        self.deleteBtTrialButtons()

        # start trial button
        self.STARTTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.STARTTRIAL["text"] = "Start Trial"
        self.STARTTRIAL["fg"] = "green"
        self.STARTTRIAL.config(font=
                               ('TKDefaultFont', 10, 'bold'))
        self.STARTTRIAL.grid(row=2, column=3)
        self.STARTTRIAL["command"] = self.starttrial

        # stop trial button
        self.STOPTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.STOPTRIAL["text"] = "Stop Trial"
        self.STOPTRIAL["fg"] = "red"
        self.STOPTRIAL.config(font=
                              ('TKDefaultFont', 10, 'bold'))
        self.STOPTRIAL.grid(row=4, column=3)
        self.STOPTRIAL["command"] = self.stoptrial

    def deleteStartStopButtons(self):
        self.STOPTRIAL.destroy()
        self.STARTTRIAL.destroy()

    def createBtTrialButtons(self):

        self.deleteStartStopButtons()

        # start trial button
        self.CONTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.CONTRIAL["text"] = "Continue Trials"
        self.CONTRIAL["fg"] = "green"
        self.CONTRIAL.config(font=
                             ('TKDefaultFont', 10, 'bold'))
        self.CONTRIAL.grid(row=2, column=3)
        self.CONTRIAL["command"] = self.continuetrial

        # finish run of trials button
        self.FINISHTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.FINISHTRIAL["text"] = "Finish Trials"
        self.FINISHTRIAL["fg"] = "red"
        self.FINISHTRIAL.config(font=
                                ('TKDefaultFont', 10, 'bold'))
        self.FINISHTRIAL.grid(row=4, column=3)
        self.FINISHTRIAL["command"] = self.finishtrial

    def deleteBtTrialButtons(self):
        self.FINISHTRIAL.destroy()
        self.CONTRIAL.destroy()

    def createStateInputs(self):
        # special function for recreating torq setpoint text inputs

        print("createStateInputs called")

        fsm_option = self.FSMOPTIONS.get()
        controller_option = self.CONTROLLEROPTIONS.get()

        self.deleteStateInputs()

        if fsm_option == 0 and controller_option == 0:
            # text input for desired assistance
            self.STANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.STANCESET_LEFT.grid(row=1, column=7)

            # text input for desired assistance
            self.SWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.SWINGSET_LEFT.grid(row=2, column=7)

            self.stancesetLabel_left = tk.Label(self.torconframe, text="Stance Setpoint")
            self.stancesetLabel_left.grid(row=1, column=6)

            self.swingsetLabel_left = tk.Label(self.torconframe, text=" Swing Setpoint")
            self.swingsetLabel_left.grid(row=2, column=6)

            self.STANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.STANCESET_RIGHT.grid(row=1, column=9)

            # text input for desired assistance
            self.SWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.SWINGSET_RIGHT.grid(row=2, column=9)

            self.stancesetLabel_right = tk.Label(self.torconframe, text="Stance Setpoint")
            self.stancesetLabel_right.grid(row=1, column=8)

            self.swingsetLabel_right = tk.Label(self.torconframe, text="Swing Setpoint")
            self.swingsetLabel_right.grid(row=2, column=8)

            self.legLabelleft = tk.Label(self.torconframe, text="LEFT")
            self.legLabelleft.grid(row=4, column=6)

            self.legLabelright = tk.Label(self.torconframe, text="RIGHT")
            self.legLabelright.grid(row=4, column=8)

            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            self.estimSwingVariable = tk.IntVar()
            self.ESTIMONOFF_SWING = tk.Checkbutton(self.estimframe,
                                                   text="Swing O/I",
                                                   variable=self.estimSwingVariable)
            self.ESTIMONOFF_SWING.grid(row=1, column=0)

        elif fsm_option == 1 and controller_option == 0:

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.STANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.STANCESET_LEFT.grid(row=1, column=7)

            # text input for desired assistance
            self.ESWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_LEFT.grid(row=2, column=7)

            # text input for desired assistance
            self.LSWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_LEFT.grid(row=3, column=7)

            ###
            self.STANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.STANCESET_RIGHT.grid(row=1, column=9)

            # text input for desired assistance
            self.ESWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_RIGHT.grid(row=2, column=9)

            # text input for desired assistance
            self.LSWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_RIGHT.grid(row=3, column=9)

            # input labels for left
            self.stancesetLabel_left = tk.Label(self.torconframe, text="Stance Setpoint")
            self.stancesetLabel_left.grid(row=1, column=6)

            self.eswingsetLabel_left = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_left.grid(row=2, column=6)

            self.lswingsetLabel_left = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_left.grid(row=3, column=6)

            self.legLabelleft = tk.Label(self.torconframe, text="LEFT")
            self.legLabelleft.grid(row=4, column=6)

            # input labels for right
            self.stancesetLabel_right = tk.Label(self.torconframe, text="Stance Setpoint")
            self.stancesetLabel_right.grid(row=1, column=8)

            self.eswingsetLabel_right = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_right.grid(row=2, column=8)

            self.lswingsetLabel_right = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_right.grid(row=3, column=8)

            self.legLabelright = tk.Label(self.torconframe, text="RIGHT")
            self.legLabelright.grid(row=4, column=8)

            # text input for desired velocity threshold
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)
            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            # estim stance
            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=1, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=2, column=0)

        elif fsm_option == 2 and controller_option == 0:
            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.ESTANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.ESTANCESET_LEFT.grid(row=1, column=7)

            # text input for desired assistance
            self.LSTANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.LSTANCESET_LEFT.grid(row=2, column=7)

            # text input for desired assistance
            self.ESWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_LEFT.grid(row=3, column=7)

            # text input for desired assistance
            self.LSWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_LEFT.grid(row=4, column=7)

            # labels for the left leg
            self.estancesetLabel_left = tk.Label(self.torconframe, text="EStance Setpoint")
            self.estancesetLabel_left.grid(row=1, column=6)

            self.lstancesetLabel_left = tk.Label(self.torconframe, text="LStance Setpoint")
            self.lstancesetLabel_left.grid(row=2, column=6)

            self.eswingsetLabel_left = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_left.grid(row=3, column=6)

            self.lswingsetLabel_left = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_left.grid(row=4, column=6)

            self.legLabelleft = tk.Label(self.torconframe, text="LEFT")
            self.legLabelleft.grid(row=5, column=6)

            # text input for desired assistance for right leg
            self.ESTANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.ESTANCESET_RIGHT.grid(row=1, column=9)

            # text input for desired assistance
            self.LSTANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.LSTANCESET_RIGHT.grid(row=2, column=9)

            # text input for desired assistance
            self.ESWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_RIGHT.grid(row=3, column=9)

            # text input for desired assistance
            self.LSWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_RIGHT.grid(row=4, column=9)

            # labels for the right leg

            self.estancesetLabel_right = tk.Label(self.torconframe, text="EStance Setpoint")
            self.estancesetLabel_right.grid(row=1, column=8)

            self.lstancesetLabel_right = tk.Label(self.torconframe, text="LStance Setpoint")
            self.lstancesetLabel_right.grid(row=2, column=8)

            self.eswingsetLabel_right = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_right.grid(row=3, column=8)

            self.lswingsetLabel_right = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_right.grid(row=4, column=8)

            self.legLabelright = tk.Label(self.torconframe, text="RIGHT")
            self.legLabelright.grid(row=5, column=8)

            #####
            # text input for swing velocity threshold shifting from early swing to late swing
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for stance velocity threshold shifting from early stance to late stance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            # label inputs for swing and stance velocity.
            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=1, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=2, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=3, column=0)

        elif fsm_option == 3 and controller_option == 0:
            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.ESTANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.ESTANCESET_LEFT.grid(row=1, column=7)

            # text input for desired assistance
            self.MSTANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.MSTANCESET_LEFT.grid(row=2, column=7)

            # text input for desired assistance
            self.LSTANCESET_LEFT = tk.Entry(self.torconframe, width=8)
            self.LSTANCESET_LEFT.grid(row=3, column=7)

            # text input for desired assistance
            self.ESWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_LEFT.grid(row=4, column=7)

            # text input for desired assistance
            self.LSWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_LEFT.grid(row=5, column=7)

            #  labels for the five states of left leg
            self.estancesetLabel_left = tk.Label(self.torconframe, text="EStance Setpoint")
            self.estancesetLabel_left.grid(row=1, column=6)

            self.mstancesetLabel_left = tk.Label(self.torconframe, text="MStance Setpoint")
            self.mstancesetLabel_left.grid(row=2, column=6)

            self.lstancesetLabel_left = tk.Label(self.torconframe, text="LStance Setpoint")
            self.lstancesetLabel_left.grid(row=3, column=6)

            self.eswingsetLabel_left = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_left.grid(row=4, column=6)

            self.lswingsetLabel_left = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_left.grid(row=5, column=6)

            #####
            self.legLabelleft = tk.Label(self.torconframe, text="LEFT")
            self.legLabelleft.grid(row=6, column=6)

            # text input for desired assistance for right leg 
            self.ESTANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.ESTANCESET_RIGHT.grid(row=1, column=9)

            # text input for desired assistance
            self.MSTANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.MSTANCESET_RIGHT.grid(row=2, column=9)

            # text input for desired assistance
            self.LSTANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.LSTANCESET_RIGHT.grid(row=3, column=9)

            # text input for desired assistance
            self.ESWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.ESWINGSET_RIGHT.grid(row=4, column=9)

            # text input for desired assistance
            self.LSWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
            self.LSWINGSET_RIGHT.grid(row=5, column=9)

            #  labels for the five states of right leg
            self.estancesetLabel_right = tk.Label(self.torconframe, text="EStance Setpoint")
            self.estancesetLabel_right.grid(row=1, column=8)

            self.mstancesetLabel_right = tk.Label(self.torconframe, text="MStance Setpoint")
            self.mstancesetLabel_right.grid(row=2, column=8)

            self.lstancesetLabel_right = tk.Label(self.torconframe, text="LStance Setpoint")
            self.lstancesetLabel_right.grid(row=3, column=8)

            self.eswingsetLabel_right = tk.Label(self.torconframe, text="ESwing Setpoint")
            self.eswingsetLabel_right.grid(row=4, column=8)

            self.lswingsetLabel_right = tk.Label(self.torconframe, text="LSwing Setpoint")
            self.lswingsetLabel_right.grid(row=5, column=8)

            self.legLabelright = tk.Label(self.torconframe, text="RIGHT")
            self.legLabelright.grid(row=6, column=8)

            #####
            # text input for velocity shifting from early swing to late swing
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for velocity shifting from early stance to mid stance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            # text input for velocity shifting from mid stance to late stance
            self.MOTORM2LSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORM2LSTANCETHRESH.grid(row=10, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            self.motorm2lstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr M2L Stance")
            self.motorm2lstancethLabel.grid(row=10, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim mid stance
            self.estimMiddleStanceVariable = tk.IntVar()
            self.ESTIMONOFF_MIDDLE_STANCE = tk.Checkbutton(self.estimframe,
                                                           text="Mid Stance O/I",
                                                           variable=self.estimMiddleStanceVariable)
            self.ESTIMONOFF_MIDDLE_STANCE.grid(row=1, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=2, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=3, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=4, column=0)

        elif fsm_option == 0 and controller_option == 1:

            # text input for closeness
            self.CLOSENESS = tk.Entry(self.impconframe, width=8)
            self.CLOSENESS.grid(row=0, column=1, padx=8)
            self.CLOSENESS.insert(END, "2")

            # text input for closeness
            self.VIRWALL = tk.Entry(self.impconframe, width=8)
            self.VIRWALL.grid(row=1, column=1, padx=8)
            self.VIRWALL.insert(END, "6")

            self.closeLabel = tk.Label(self.impconframe, text="Closeness")
            self.closeLabel.grid(row=0, column=0)

            self.virwallLabel = tk.Label(self.impconframe, text="Virtual Wall (d)")
            self.virwallLabel.grid(row=1, column=0)

            # estim stance
            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            # estim swing
            self.estimSwingVariable = tk.IntVar()
            self.ESTIMONOFF_SWING = tk.Checkbutton(self.estimframe,
                                                   text="Swing O/I",
                                                   variable=self.estimSwingVariable)
            self.ESTIMONOFF_SWING.grid(row=1, column=0)

        elif fsm_option == 1 and controller_option == 1:

            # text input for closeness
            self.CLOSENESS = tk.Entry(self.impconframe, width=8)
            self.CLOSENESS.grid(row=0, column=1, padx=8)
            self.CLOSENESS.insert(END, "2")

            # text input for closeness
            self.VIRWALL = tk.Entry(self.impconframe, width=8)
            self.VIRWALL.grid(row=1, column=1, padx=8)
            self.VIRWALL.insert(END, "6")

            self.closeLabel = tk.Label(self.impconframe, text="Closeness")
            self.closeLabel.grid(row=0, column=0)

            self.virwallLabel = tk.Label(self.impconframe, text="Virtual Wall (d)")
            self.virwallLabel.grid(row=1, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            # estim stance
            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=1, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=2, column=0)

        elif fsm_option == 2 and controller_option == 1:
            # text input for closeness
            self.CLOSENESS = tk.Entry(self.impconframe, width=8)
            self.CLOSENESS.grid(row=0, column=1, padx=8)
            self.CLOSENESS.insert(END, "2")

            # text input for closeness
            self.VIRWALL = tk.Entry(self.impconframe, width=8)
            self.VIRWALL.grid(row=1, column=1, padx=8)
            self.VIRWALL.insert(END, "6")

            self.closeLabel = tk.Label(self.impconframe, text="Closeness")
            self.closeLabel.grid(row=0, column=0)

            self.virwallLabel = tk.Label(self.impconframe, text="Virtual Wall (d)")
            self.virwallLabel.grid(row=1, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for desired assistance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=1, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=2, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=3, column=0)

        elif fsm_option == 3 and controller_option == 1:

            # text input for closeness
            self.CLOSENESS = tk.Entry(self.impconframe, width=8)
            self.CLOSENESS.grid(row=0, column=1, padx=8)
            self.CLOSENESS.insert(END, "2")

            # text input for closeness
            self.VIRWALL = tk.Entry(self.impconframe, width=8)
            self.VIRWALL.grid(row=1, column=1, padx=8)
            self.VIRWALL.insert(END, "6")

            self.closeLabel = tk.Label(self.impconframe, text="Closeness")
            self.closeLabel.grid(row=0, column=0)

            self.virwallLabel = tk.Label(self.impconframe, text="Virtual Wall (d)")
            self.virwallLabel.grid(row=1, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for desired assistance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            # text input for desired assistance
            self.MOTORM2LSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORM2LSTANCETHRESH.grid(row=10, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            self.motorm2lstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr M2L Stance")
            self.motorm2lstancethLabel.grid(row=10, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim mid stance
            self.estimMiddleStanceVariable = tk.IntVar()
            self.ESTIMONOFF_MIDDLE_STANCE = tk.Checkbutton(self.estimframe,
                                                           text="Mid Stance O/I",
                                                           variable=self.estimMiddleStanceVariable)
            self.ESTIMONOFF_MIDDLE_STANCE.grid(row=1, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=2, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=3, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=4, column=0)

        elif fsm_option == 0 and controller_option == 2:
            self.WEIGHT = tk.Entry(self.adaconframe, width=8)
            self.WEIGHT.grid(row=0, column=1)


            # text input for peak knee flexion
            self.PEAKFLEXION = tk.Entry(self.adaconframe, width=8)
            self.PEAKFLEXION.grid(row=1, column=1)


            # text input for knee angle rom
            self.KNEEROM = tk.Entry(self.adaconframe, width=8)
            self.KNEEROM.grid(row=2, column=1)


            # text input for stance min
            self.STANCEMIN = tk.Entry(self.adaconframe, width=8)
            self.STANCEMIN.grid(row=3, column=1)


            # text input for desired assistance
            self.DESASSIST = tk.Entry(self.adaconframe, width=8)
            self.DESASSIST.grid(row=4, column=1)

            self.weightLabel = tk.Label(self.adaconframe, text="Weight (kg)")
            self.weightLabel.grid(row=0, column=0)

            self.kneeflexLabel = tk.Label(self.adaconframe, text="Peak Knee Flexion")
            self.kneeflexLabel.grid(row=1, column=0)

            self.kneeromLabel = tk.Label(self.adaconframe, text="Knee Angle ROM")
            self.kneeromLabel.grid(row=2, column=0)

            self.stanceminLabel = tk.Label(self.adaconframe, text="Stance Min")
            self.stanceminLabel.grid(row=3, column=0)

            self.desassistLabel = tk.Label(self.adaconframe, text="Desired Assistance")
            self.desassistLabel.grid(row=4, column=0)

            # estim stance
            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            # estim swing
            self.estimSwingVariable = tk.IntVar()
            self.ESTIMONOFF_SWING = tk.Checkbutton(self.estimframe,
                                                   text="Swing O/I",
                                                   variable=self.estimSwingVariable)
            self.ESTIMONOFF_SWING.grid(row=1, column=0)

        elif fsm_option == 1 and controller_option == 2:
            self.WEIGHT = tk.Entry(self.adaconframe, width=8)
            self.WEIGHT.grid(row=0, column=1)


            # text input for peak knee flexion
            self.PEAKFLEXION = tk.Entry(self.adaconframe, width=8)
            self.PEAKFLEXION.grid(row=1, column=1)


            # text input for knee angle rom
            self.KNEEROM = tk.Entry(self.adaconframe, width=8)
            self.KNEEROM.grid(row=2, column=1)


            # text input for stance min
            self.STANCEMIN = tk.Entry(self.adaconframe, width=8)
            self.STANCEMIN.grid(row=3, column=1)


            # text input for desired assistance
            self.DESASSIST = tk.Entry(self.adaconframe, width=8)
            self.DESASSIST.grid(row=4, column=1)


            self.weightLabel = tk.Label(self.adaconframe, text="Weight (kg)")
            self.weightLabel.grid(row=0, column=0)

            self.kneeflexLabel = tk.Label(self.adaconframe, text="Peak Knee Flexion")
            self.kneeflexLabel.grid(row=1, column=0)

            self.kneeromLabel = tk.Label(self.adaconframe, text="Knee Angle ROM")
            self.kneeromLabel.grid(row=2, column=0)

            self.stanceminLabel = tk.Label(self.adaconframe, text="Stance Min")
            self.stanceminLabel.grid(row=3, column=0)

            self.desassistLabel = tk.Label(self.adaconframe, text="Desired Assistance")
            self.desassistLabel.grid(row=4, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            # estim stance
            self.estimStanceVariable = tk.IntVar()
            self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                    text="Stance O/I",
                                                    variable=self.estimStanceVariable)
            self.ESTIMONOFF_STANCE.grid(row=0, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=1, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=2, column=0)

        elif fsm_option == 2 and controller_option == 2:
            self.WEIGHT = tk.Entry(self.adaconframe, width=8)
            self.WEIGHT.grid(row=0, column=1)


            # text input for peak knee flexion
            self.PEAKFLEXION = tk.Entry(self.adaconframe, width=8)
            self.PEAKFLEXION.grid(row=1, column=1)


            # text input for knee angle rom
            self.KNEEROM = tk.Entry(self.adaconframe, width=8)
            self.KNEEROM.grid(row=2, column=1)


            # text input for stance min
            self.STANCEMIN = tk.Entry(self.adaconframe, width=8)
            self.STANCEMIN.grid(row=3, column=1)


            # text input for desired assistance
            self.DESASSIST = tk.Entry(self.adaconframe, width=8)
            self.DESASSIST.grid(row=4, column=1)


            self.weightLabel = tk.Label(self.adaconframe, text="Weight (kg)")
            self.weightLabel.grid(row=0, column=0)

            self.kneeflexLabel = tk.Label(self.adaconframe, text="Peak Knee Flexion")
            self.kneeflexLabel.grid(row=1, column=0)

            self.kneeromLabel = tk.Label(self.adaconframe, text="Knee Angle ROM")
            self.kneeromLabel.grid(row=2, column=0)

            self.stanceminLabel = tk.Label(self.adaconframe, text="Stance Min")
            self.stanceminLabel.grid(row=3, column=0)

            self.desassistLabel = tk.Label(self.adaconframe, text="Desired Assistance")
            self.desassistLabel.grid(row=4, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for desired assistance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=1, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=2, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=3, column=0)

        elif fsm_option == 3 and controller_option == 2:
            self.WEIGHT = tk.Entry(self.adaconframe, width=8)
            self.WEIGHT.grid(row=0, column=1)


            # text input for peak knee flexion
            self.PEAKFLEXION = tk.Entry(self.adaconframe, width=8)
            self.PEAKFLEXION.grid(row=1, column=1)


            # text input for knee angle rom
            self.KNEEROM = tk.Entry(self.adaconframe, width=8)
            self.KNEEROM.grid(row=2, column=1)


            # text input for stance min
            self.STANCEMIN = tk.Entry(self.adaconframe, width=8)
            self.STANCEMIN.grid(row=3, column=1)


            # text input for desired assistance
            self.DESASSIST = tk.Entry(self.adaconframe, width=8)
            self.DESASSIST.grid(row=4, column=1)


            self.weightLabel = tk.Label(self.adaconframe, text="Weight (kg)")
            self.weightLabel.grid(row=0, column=0)

            self.kneeflexLabel = tk.Label(self.adaconframe, text="Peak Knee Flexion")
            self.kneeflexLabel.grid(row=1, column=0)

            self.kneeromLabel = tk.Label(self.adaconframe, text="Knee Angle ROM")
            self.kneeromLabel.grid(row=2, column=0)

            self.stanceminLabel = tk.Label(self.adaconframe, text="Stance Min")
            self.stanceminLabel.grid(row=3, column=0)

            self.desassistLabel = tk.Label(self.adaconframe, text="Desired Assistance")
            self.desassistLabel.grid(row=4, column=0)

            self.mothreshframe = tk.LabelFrame(self.midrow, text="Motor Threshold Options",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)
            self.mothreshframe.pack(side=LEFT, padx=10, pady=10)

            # text input for desired assistance
            self.MOTORSWINGTHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORSWINGTHRESH.grid(row=8, column=7)

            # text input for desired assistance
            self.MOTORE2MSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORE2MSTANCETHRESH.grid(row=9, column=7)

            # text input for desired assistance
            self.MOTORM2LSTANCETHRESH = tk.Entry(self.mothreshframe, width=8)
            self.MOTORM2LSTANCETHRESH.grid(row=10, column=7)

            self.motorswingthLabel = tk.Label(self.mothreshframe, text="Motor Thr Swing")
            self.motorswingthLabel.grid(row=8, column=6)

            self.motore2mstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr E2M Stance")
            self.motore2mstancethLabel.grid(row=9, column=6)

            self.motorm2lstancethLabel = tk.Label(self.mothreshframe, text="Motor Thr M2L Stance")
            self.motorm2lstancethLabel.grid(row=10, column=6)

            # estim early stance
            self.estimEarlyStanceVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_STANCE = tk.Checkbutton(self.estimframe,
                                                          text="Early Stance O/I",
                                                          variable=self.estimEarlyStanceVariable)
            self.ESTIMONOFF_EARLY_STANCE.grid(row=0, column=0)

            # estim mid stance
            self.estimMiddleStanceVariable = tk.IntVar()
            self.ESTIMONOFF_MIDDLE_STANCE = tk.Checkbutton(self.estimframe,
                                                           text="Mid Stance O/I",
                                                           variable=self.estimMiddleStanceVariable)
            self.ESTIMONOFF_MIDDLE_STANCE.grid(row=1, column=0)

            # estim late stance
            self.estimLateStanceVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_STANCE = tk.Checkbutton(self.estimframe,
                                                         text="Late Stance O/I",
                                                         variable=self.estimLateStanceVariable)
            self.ESTIMONOFF_LATE_STANCE.grid(row=2, column=0)

            # estim early swing
            self.estimEarlySwingVariable = tk.IntVar()
            self.ESTIMONOFF_EARLY_SWING = tk.Checkbutton(self.estimframe,
                                                         text="Early Swing O/I",
                                                         variable=self.estimEarlySwingVariable)
            self.ESTIMONOFF_EARLY_SWING.grid(row=3, column=0)

            # estim late swing
            self.estimLateSwingVariable = tk.IntVar()
            self.ESTIMONOFF_LATE_SWING = tk.Checkbutton(self.estimframe,
                                                        text="Late Swing O/I",
                                                        variable=self.estimLateSwingVariable)
            self.ESTIMONOFF_LATE_SWING.grid(row=4, column=0)

        global old_fsm_option
        old_fsm_option = fsm_option

        global old_controller_option
        old_controller_option = controller_option

    def deleteStateInputs(self):
        # special function for recreating torq setpoint text inputs
        global old_fsm_option
        global old_controller_option

        if old_fsm_option == 0 and old_controller_option == 0:
            # text deletion for left leg
            self.STANCESET_LEFT.destroy()
            self.SWINGSET_LEFT.destroy()

            # text deletion for right leg
            self.STANCESET_RIGHT.destroy()
            self.SWINGSET_RIGHT.destroy()

            self.stancesetLabel_left.destroy()
            self.swingsetLabel_left.destroy()

            self.stancesetLabel_right.destroy()
            self.swingsetLabel_right.destroy()

            self.legLabelright.destroy()
            self.legLabelleft.destroy()

            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim swing
            self.ESTIMONOFF_SWING.destroy()

        elif old_fsm_option == 1 and old_controller_option == 0:

            # text deletion for left leg
            self.STANCESET_LEFT.destroy()
            # text input for desired assistance
            self.ESWINGSET_LEFT.destroy()
            # text input for desired assistance
            self.LSWINGSET_LEFT.destroy()

            # label deletion for left leg
            self.stancesetLabel_left.destroy()
            self.eswingsetLabel_left.destroy()
            self.lswingsetLabel_left.destroy()

            # text deletion for right leg
            self.STANCESET_RIGHT.destroy()
            self.ESWINGSET_RIGHT.destroy()
            self.LSWINGSET_RIGHT.destroy()

            # label deletion for right leg
            self.stancesetLabel_right.destroy()
            self.eswingsetLabel_right.destroy()
            self.lswingsetLabel_right.destroy()

            self.legLabelright.destroy()
            self.legLabelleft.destroy()

            # motor info related deletion
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.motorswingthLabel.destroy()

            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 2 and old_controller_option == 0:

            # text deletion for left leg
            self.ESTANCESET_LEFT.destroy()
            self.LSTANCESET_LEFT.destroy()
            self.ESWINGSET_LEFT.destroy()
            self.LSWINGSET_LEFT.destroy()

            # label deletion for left leg
            self.estancesetLabel_left.destroy()
            self.lstancesetLabel_left.destroy()
            self.eswingsetLabel_left.destroy()
            self.lswingsetLabel_left.destroy()

            # text deletion for right leg
            self.ESTANCESET_RIGHT.destroy()
            self.LSTANCESET_RIGHT.destroy()
            self.ESWINGSET_RIGHT.destroy()
            self.LSWINGSET_RIGHT.destroy()

            # label deletion for right leg
            self.estancesetLabel_right.destroy()
            self.lstancesetLabel_right.destroy()
            self.eswingsetLabel_right.destroy()
            self.lswingsetLabel_right.destroy()

            # frame title deletion
            self.legLabelright.destroy()
            self.legLabelleft.destroy()

            # vel parameters deletion (label and input)
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 3 and old_controller_option == 0:

            # text deletion for left leg
            self.ESTANCESET_LEFT.destroy()
            self.MSTANCESET_LEFT.destroy()
            self.LSTANCESET_LEFT.destroy()
            self.ESWINGSET_LEFT.destroy()
            self.LSWINGSET_LEFT.destroy()

            # label deletion for left leg
            self.estancesetLabel_left.destroy()
            self.mstancesetLabel_left.destroy()
            self.lstancesetLabel_left.destroy()
            self.eswingsetLabel_left.destroy()
            self.lswingsetLabel_left.destroy()

            # frame title deletion
            self.legLabelright.destroy()
            self.legLabelleft.destroy()

            # text deletion for right leg
            self.ESTANCESET_RIGHT.destroy()
            self.MSTANCESET_RIGHT.destroy()
            self.LSTANCESET_RIGHT.destroy()
            self.ESWINGSET_RIGHT.destroy()
            self.LSWINGSET_RIGHT.destroy()

            # label deletion for right leg
            self.estancesetLabel_right.destroy()
            self.mstancesetLabel_right.destroy()
            self.lstancesetLabel_right.destroy()
            self.eswingsetLabel_right.destroy()
            self.lswingsetLabel_right.destroy()

            # vel parameters deletion including label and inputr
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.MOTORM2LSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()
            self.motorm2lstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim middle stance
            self.ESTIMONOFF_MIDDLE_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 0 and old_controller_option == 1:
            self.CLOSENESS.destroy()
            self.closeLabel.destroy()
            self.VIRWALL.destroy()
            self.virwallLabel.destroy()
            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim swing
            self.ESTIMONOFF_SWING.destroy()

        elif old_fsm_option == 1 and old_controller_option == 1:
            self.CLOSENESS.destroy()
            self.closeLabel.destroy()
            self.VIRWALL.destroy()
            self.virwallLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.motorswingthLabel.destroy()

            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 2 and old_controller_option == 1:
            self.CLOSENESS.destroy()
            self.closeLabel.destroy()
            self.VIRWALL.destroy()
            self.virwallLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 3 and old_controller_option == 1:
            self.CLOSENESS.destroy()
            self.closeLabel.destroy()
            self.VIRWALL.destroy()
            self.virwallLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.MOTORM2LSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()
            self.motorm2lstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim middle stance
            self.ESTIMONOFF_MIDDLE_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 0 and old_controller_option == 2:
            self.WEIGHT.destroy()
            self.PEAKFLEXION.destroy()
            self.KNEEROM.destroy()
            self.STANCEMIN.destroy()
            self.DESASSIST.destroy()
            self.weightLabel.destroy()
            self.kneeflexLabel.destroy()
            self.kneeromLabel.destroy()
            self.stanceminLabel.destroy()
            self.desassistLabel.destroy()
            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim swing
            self.ESTIMONOFF_SWING.destroy()

        elif old_fsm_option == 1 and old_controller_option == 2:
            self.WEIGHT.destroy()
            self.PEAKFLEXION.destroy()
            self.KNEEROM.destroy()
            self.STANCEMIN.destroy()
            self.DESASSIST.destroy()
            self.weightLabel.destroy()
            self.kneeflexLabel.destroy()
            self.kneeromLabel.destroy()
            self.stanceminLabel.destroy()
            self.desassistLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.motorswingthLabel.destroy()

            # estim stance
            self.ESTIMONOFF_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 2 and old_controller_option == 2:
            self.WEIGHT.destroy()
            self.PEAKFLEXION.destroy()
            self.KNEEROM.destroy()
            self.STANCEMIN.destroy()
            self.DESASSIST.destroy()
            self.weightLabel.destroy()
            self.kneeflexLabel.destroy()
            self.kneeromLabel.destroy()
            self.stanceminLabel.destroy()
            self.desassistLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

        elif old_fsm_option == 3 and old_controller_option == 2:
            self.WEIGHT.destroy()
            self.PEAKFLEXION.destroy()
            self.KNEEROM.destroy()
            self.STANCEMIN.destroy()
            self.DESASSIST.destroy()
            self.weightLabel.destroy()
            self.kneeflexLabel.destroy()
            self.kneeromLabel.destroy()
            self.stanceminLabel.destroy()
            self.desassistLabel.destroy()
            self.mothreshframe.destroy()
            self.MOTORSWINGTHRESH.destroy()
            self.MOTORE2MSTANCETHRESH.destroy()
            self.MOTORM2LSTANCETHRESH.destroy()
            self.motorswingthLabel.destroy()
            self.motore2mstancethLabel.destroy()
            self.motorm2lstancethLabel.destroy()

            # estim early stance
            self.ESTIMONOFF_EARLY_STANCE.destroy()

            # estim middle stance
            self.ESTIMONOFF_MIDDLE_STANCE.destroy()

            # estim late stance
            self.ESTIMONOFF_LATE_STANCE.destroy()

            # estim early swing
            self.ESTIMONOFF_EARLY_SWING.destroy()

            # estim late swing
            self.ESTIMONOFF_LATE_SWING.destroy()

    ### Basic button functions ###

    def receive(self):
        # Send 'H' which the Arduino
        # detects as turning the light on
        global buttons_state
        buttons_state = "off"  # ends previous receive_serial_data
        buttons_state = "on"
        receive_data()

    def uploadsettings2(self):
        data = construct_data_string_left()
        print("Data String: " + data)
        print("Uploading settings 2")
        send_data(data, leg='L')
        data1 = construct_data_string_right()
        print("Data String: " + data1)
        print("Uploading settings 2")
        send_data(data1, leg='R')

        self.createNextButton()  # creates Next button and deletes Upload Settings button

        print("About to receive data...")
        receive_data()

    def next_step(self):
        data = ","
        send_data(data, 'N', 'N')

        self.createUploadButton()

        self.STARTTRIAL["state"] = NORMAL  # enable start trial button
        self.UPLOADSETTINGS["state"] = DISABLED  # disable upload settings button

    def starttrial(self):
        data = str(self.TRIALNUM.get())
        print("Start Trial Data: " + data)
        send_data(data, parse='N')
        print("receive_and_save_data() was called...")

        self.STOPTRIAL["state"] = NORMAL
        self.STARTTRIAL["state"] = DISABLED

        receive_and_save_data()

    def stoptrial(self):
        data = ","
        send_data(data, 'N', 'N')
        self.createBtTrialButtons()

        receive_data()

        self.trial_num += 1
        self.TRIALNUM.delete(0, 'end')
        self.TRIALNUM.insert(END, str(self.trial_num))
        print("Trial Number: " + str(self.trial_num))

        self.EXOGAITMODE.set(0)  # reset 'Mode' to Standby

    def finishtrial(self):
        data = "0/"
        send_data(data, parse="N")

        self.createStartStopButtons()

        self.STARTTRIAL["state"] = DISABLED
        self.STOPTRIAL["state"] = DISABLED
        self.UPLOADSETTINGS["state"] = NORMAL
        receive_data()

    def continuetrial(self):
        data = "1/"
        send_data(data, parse="N")
        self.createStartStopButtons()
        self.STOPTRIAL["state"] = DISABLED
        receive_data()

    def sendmode(self):
        mode = self.EXOGAITMODE.get()
        if mode == 0:
            data = "s"
            send_data(data, 'N', 'N')
        elif mode == 1:
            data = "w"
            send_data(data, 'N', 'N')

        print(data)

    def createWidgets(self):
        """Creates all the buttons on the Run Trial page.
         Look at a Tkinter reference online for explanations."""

        # == Controller Options Frame =================================================================================
        # == controller type radio button ===
        controllers = [
            ("Constant Torque", 0),
            ("Impedance", 1),
            ("Adaptive", 2)
        ]

        self.CONTROLLEROPTIONS = tk.IntVar()
        self.CONTROLLEROPTIONS.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.CONTROLLEROPTIONS.get())

        for language, val in controllers:
            tk.Radiobutton(self.conoptframe,
                           text=language,
                           padx=20,
                           variable=self.CONTROLLEROPTIONS,
                           command=self.createStateInputs,
                           value=val).grid(row=(val))

        # == state parsing radio button ===
        fsmoptions = [
            ("2 State", 0),
            ("3 State", 1),
            ("4 State", 2),
            ("5 State", 3),
        ]

        self.FSMOPTIONS = tk.IntVar()
        self.FSMOPTIONS.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(FSMOPTIONS.get())

        for language, val in fsmoptions:
            tk.Radiobutton(self.conoptframe,
                           text=language,
                           padx=20,
                           variable=self.FSMOPTIONS,
                           command=self.createStateInputs,
                           value=val).grid(row=(val), column=1)

        # == Impedance Controller Frame ===============================================================================
        # text input for closeness
        self.CLOSENESS = tk.Entry(self.impconframe, width=8)
        self.CLOSENESS.grid(row=0, column=1, padx=8)
        self.CLOSENESS.insert(END, "2")

        # text input for closeness
        self.VIRWALL = tk.Entry(self.impconframe, width=8)
        self.VIRWALL.grid(row=1, column=1, padx=8)
        self.VIRWALL.insert(END, "6")

        closeLabel = tk.Label(self.impconframe, text="Closeness")
        closeLabel.grid(row=0, column=0)

        virwallLabel = tk.Label(self.impconframe, text="Virtual Wall (d)")
        virwallLabel.grid(row=1, column=0)

        # == Adaptive Controller Frame ================================================================================
        # text input for weight
        self.WEIGHT = tk.Entry(self.adaconframe, width=8)
        self.WEIGHT.grid(row=0, column=1)
        self.WEIGHT.insert(END, "35")

        # text input for peak knee flexion
        self.PEAKFLEXION = tk.Entry(self.adaconframe, width=8)
        self.PEAKFLEXION.grid(row=1, column=1)
        self.PEAKFLEXION.insert(END, "20.00")

        # text input for knee angle rom
        self.KNEEROM = tk.Entry(self.adaconframe, width=8)
        self.KNEEROM.grid(row=2, column=1)
        self.KNEEROM.insert(END, "15")

        # text input for stance min
        self.STANCEMIN = tk.Entry(self.adaconframe, width=8)
        self.STANCEMIN.grid(row=3, column=1)
        self.STANCEMIN.insert(END, "10.00")

        # text input for desired assistance
        self.DESASSIST = tk.Entry(self.adaconframe, width=8)
        self.DESASSIST.grid(row=4, column=1)
        self.DESASSIST.insert(END, "3")

        weightLabel = tk.Label(self.adaconframe, text="Weight (kg)")
        weightLabel.grid(row=0, column=0)

        kneeflexLabel = tk.Label(self.adaconframe, text="Peak Knee Flexion")
        kneeflexLabel.grid(row=1, column=0)

        kneeromLabel = tk.Label(self.adaconframe, text="Knee Angle ROM")
        kneeromLabel.grid(row=2, column=0)

        stanceminLabel = tk.Label(self.adaconframe, text="Stance Min")
        stanceminLabel.grid(row=3, column=0)

        desassistLabel = tk.Label(self.adaconframe, text="Desired Assistance")
        desassistLabel.grid(row=4, column=0)

        # == Constant Torque Controller Frame =========================================================================
        # text input for desired assistance
        # self.STANCESET_LEFT = tk.Entry(self.torconframe, width=8)
        # self.STANCESET_LEFT.grid(row=0, column=1)
        # self.STANCESET_LEFT.insert(END, "5")
        #
        # # text input for desired assistance
        # self.SWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
        # self.SWINGSET_LEFT.grid(row=1, column=1)
        # self.SWINGSET_LEFT.insert(END, "5")
        #
        # self.stancesetLabel_left = tk.Label(self.torconframe, text="Left Stance Setpoint")
        # self.stancesetLabel_left.grid(row=0, column=0)
        #
        # self.swingsetLabel_left = tk.Label(self.torconframe, text="Left Swing Setpoint")
        # self.swingsetLabel_left.grid(row=1, column=0)
        #
        # self.STANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
        # self.STANCESET_RIGHT.grid(row=2, column=1)
        # self.STANCESET_RIGHT.insert(END, "5")
        #
        # # text input for desired assistance
        # self.SWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
        # self.SWINGSET_RIGHT.grid(row=3, column=1)
        # self.SWINGSET_RIGHT.insert(END, "5")
        #
        # self.stancesetLabel_left = tk.Label(self.torconframe, text="Right Stance Setpoint")
        # self.stancesetLabel_left.grid(row=2, column=0)
        #
        # self.swingsetLabel_right = tk.Label(self.torconframe, text="Right Swing Setpoint")
        # self.swingsetLabel_right.grid(row=3, column=0)

        ######
        # text input for desired assistance
        self.STANCESET_LEFT = tk.Entry(self.torconframe, width=8)
        self.STANCESET_LEFT.grid(row=1, column=7)
        self.STANCESET_LEFT.insert(END, "5")

        # text input for desired assistance
        self.SWINGSET_LEFT = tk.Entry(self.torconframe, width=8)
        self.SWINGSET_LEFT.grid(row=2, column=7)
        self.SWINGSET_LEFT.insert(END, "5")

        self.stancesetLabel_left = tk.Label(self.torconframe, text="Stance Setpoint")
        self.stancesetLabel_left.grid(row=1, column=6)

        self.swingsetLabel_left = tk.Label(self.torconframe, text="Swing Setpoint")
        self.swingsetLabel_left.grid(row=2, column=6)

        self.STANCESET_RIGHT = tk.Entry(self.torconframe, width=8)
        self.STANCESET_RIGHT.grid(row=1, column=9)
        self.STANCESET_RIGHT.insert(END, "5")

        # text input for desired assistance
        self.SWINGSET_RIGHT = tk.Entry(self.torconframe, width=8)
        self.SWINGSET_RIGHT.grid(row=2, column=9)
        self.SWINGSET_RIGHT.insert(END, "5")

        self.stancesetLabel_right = tk.Label(self.torconframe, text="Stance Setpoint")
        self.stancesetLabel_right.grid(row=1, column=8)

        self.swingsetLabel_right = tk.Label(self.torconframe, text="Swing Setpoint")
        self.swingsetLabel_right.grid(row=2, column=8)

        self.legLabelleft = tk.Label(self.torconframe, text="LEFT")
        self.legLabelleft.grid(row=4, column=6)

        self.legLabelright = tk.Label(self.torconframe, text="RIGHT")
        self.legLabelright.grid(row=4, column=8)
        ######

        # == E Stim Options Frame =====================================================================================
        self.estimStanceVariable = tk.IntVar()
        self.ESTIMONOFF_STANCE = tk.Checkbutton(self.estimframe,
                                                text="Stance O/I",
                                                variable=self.estimStanceVariable)
        self.ESTIMONOFF_STANCE.grid(row=0, column=0)

        self.estimSwingVariable = tk.IntVar()
        self.ESTIMONOFF_SWING = tk.Checkbutton(self.estimframe,
                                               text="Swing O/I",
                                               variable=self.estimSwingVariable)
        self.ESTIMONOFF_SWING.grid(row=1, column=0)

        # == Universal Controller Parameters Frame ====================================================================
        # text input for pgain
        self.PGAIN = tk.Entry(self.uniconframe, width=8)
        self.PGAIN.grid(row=0, column=1)
        self.PGAIN.insert(END, "425")

        # text input for igain
        self.IGAIN = tk.Entry(self.uniconframe, width=8)
        self.IGAIN.grid(row=1, column=1)
        self.IGAIN.insert(END, "1300")

        # text input for dgain
        self.DGAIN = tk.Entry(self.uniconframe, width=8)
        self.DGAIN.grid(row=2, column=1)
        self.DGAIN.insert(END, ".3")

        # == radio button for sending PID gains o/i ===
        gains_onoff = [
            ("Off", 0),
            ("On", 1),
        ]

        self.SENDGAINSONOFF = tk.IntVar()
        self.SENDGAINSONOFF.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.SENDGAINSONOFF.get())

        for language, val in gains_onoff:
            tk.Radiobutton(self.uniconframe,
                           text=language,
                           padx=20,
                           variable=self.SENDGAINSONOFF,
                           command=ShowChoice,
                           value=val).grid(row=(val + 1), column=2, sticky=W)

        pLabel = tk.Label(self.uniconframe, text="P Gain: ")
        pLabel.grid(row=0, column=0)

        iLabel = tk.Label(self.uniconframe, text="I Gain: ")
        iLabel.grid(row=1, column=0)

        dLabel = tk.Label(self.uniconframe, text="D Gain: ")
        dLabel.grid(row=2, column=0)

        sendgainsLabel = tk.Label(self.uniconframe, text="Send Gains")
        sendgainsLabel.grid(row=0, column=2, sticky=W)

        # == Data Collection Options Frame ============================================================================
        # == radio button for estim on/off ===
        estimo = [
            ("Off", 0),
            ("On", 1),
        ]

        self.ESTIMONOFF = tk.IntVar()
        self.ESTIMONOFF.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.ESTIMONOFF.get())

        for language, val in estimo:
            tk.Radiobutton(self.datcolframe,
                           text=language,
                           padx=20,
                           variable=self.ESTIMONOFF,
                           command=ShowChoice,
                           value=val).grid(row=(val + 1), column=0)

        # == radio button for assistance mode (walking/standy) ===
        mode = [
            ("Standby", 0),
            ("Walking", 1),
        ]

        self.EXOGAITMODE = tk.IntVar()
        self.EXOGAITMODE.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(EXOGAITMODE.get())

        for language, val in mode:
            tk.Radiobutton(self.datcolframe,
                           text=language,
                           padx=20,
                           variable=self.EXOGAITMODE,
                           command=self.sendmode,
                           value=val).grid(row=(val + 1), column=1)

        # == save settings radio button ===
        mode = [
            ("No", 0),
            ("Yes", 1),
        ]

        self.SAVESETTINGS = tk.IntVar()
        self.SAVESETTINGS.set(0)

        for language, val in mode:
            tk.Radiobutton(self.datcolframe,
                           text=language,
                           padx=20,
                           variable=self.SAVESETTINGS,
                           value=val).grid(row=(val + 1), column=2)

        # text input for fsr threshold
        self.FSRTHRESH_LEFT = tk.Entry(self.datcolframe, width=8)
        self.FSRTHRESH_LEFT.grid(row=3, column=1)
        self.FSRTHRESH_LEFT.insert(END, "1.8")

        self.FSRTHRESH_RIGHT = tk.Entry(self.datcolframe, width=8)
        self.FSRTHRESH_RIGHT.grid(row=4, column=1)
        self.FSRTHRESH_RIGHT.insert(END, "2")

        # text input for trial number
        self.TRIALNUM = tk.Entry(self.datcolframe, width=8)
        self.TRIALNUM.grid(row=5, column=1)
        self.TRIALNUM.insert(END, "1")

        # upload settings button
        self.UPLOADSETTINGS = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.UPLOADSETTINGS["text"] = "Upload Settings"
        self.UPLOADSETTINGS["fg"] = "blue"
        self.UPLOADSETTINGS.config(font=
                                   ('TKDefaultFont', 10, 'bold'))
        self.UPLOADSETTINGS.grid(row=0, column=3, padx=10)
        self.UPLOADSETTINGS["command"] = self.uploadsettings2

        # start trial button
        self.STARTTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.STARTTRIAL["text"] = "Start Trial"
        self.STARTTRIAL["fg"] = "green"
        self.STARTTRIAL.config(font=
                               ('TKDefaultFont', 10, 'bold'))
        self.STARTTRIAL.grid(row=2, column=3, padx=10)
        self.STARTTRIAL["command"] = self.starttrial
        self.STARTTRIAL["state"] = DISABLED

        # stop trial button
        self.STOPTRIAL = tk.Button(self.datcolframe, relief="groove", overrelief="raised")
        self.STOPTRIAL["text"] = "Stop Trial"
        self.STOPTRIAL["fg"] = "red"
        self.STOPTRIAL.config(font=
                              ('TKDefaultFont', 10, 'bold'))
        self.STOPTRIAL.grid(row=4, column=3, padx=10)
        self.STOPTRIAL["command"] = self.stoptrial
        self.STOPTRIAL["state"] = DISABLED

        fsrLabel_left = tk.Label(self.datcolframe, text="Left FSR Threshold")
        fsrLabel_left.grid(row=3, column=0)

        fsrLabel_right = tk.Label(self.datcolframe, text="Right FSR Threshold")
        fsrLabel_right.grid(row=4, column=0)

        trialnumLabel = tk.Label(self.datcolframe, text="Trial Number: ")
        trialnumLabel.grid(row=5, column=0)

        estimLabel = tk.Label(self.datcolframe, text="E Stim Options")
        estimLabel.grid(row=0, column=0)

        modeLabel = tk.Label(self.datcolframe, text="Mode")
        modeLabel.grid(row=0, column=1)

        savesettsLabel = tk.Label(self.datcolframe, text="Save Setttings?")
        savesettsLabel.grid(row=0, column=2)

        # === Data Reception Frame ===================================================================================
        # left leg console scrolled text widget
        self.LeftConsole = scrolledtext.ScrolledText(
            master=self.leftconsoleframe,
            wrap=WORD,
            width=65,
            height=18
        )
        self.LeftConsole.grid(column=0, row=0, sticky=NSEW)

        # right leg console scrolled text widget
        self.RightConsole = scrolledtext.ScrolledText(
            master=self.rightconsoleframe,
            wrap=WORD,
            width=65,
            height=18
        )
        self.RightConsole.grid(column=0, row=0, sticky=NSEW)


class TestingPage(Page):
    """TestingPage is the page labeled 'Prelim Tests' in the actual GUI. The different frames hold the different options
    for each controller/other important groups of settings.

    The create___() and delete____() functions can get lengthy,
    but these are the buttons that track what widgets to create and destroy based on certain options being
    chosen. For instance, if you choose a Constant Torque controller with 2 states, you need different text entry
    widgets that a Constant Torque controller with 4 states. The create____() and delete____() functions make sure the
    proper widgets are displayed.

    Functions such as receive() and uploadsettings() are commanded by buttons on teh GUI and facilitate communication
    with the the microcontroller.

    createWidgets() creates all of the widgets that are initially displayed on MainMenuPage when instantiated as an
    object.
    """
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)

        self.toprow = tk.Frame(self)
        self.midrow = tk.Frame(self)
        self.botrow = tk.Frame(self)

        self.uniconframe = tk.LabelFrame(self.toprow, text="Universal Controller Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.motparframe = tk.LabelFrame(self.toprow, text="Motor Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.torconframe = tk.LabelFrame(self.toprow, text="Torque Controller Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.potconframe = tk.LabelFrame(self.toprow, text="Potentiometer Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.impconframe = tk.LabelFrame(self.midrow, text="Impedance Controller Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.speconframe = tk.LabelFrame(self.midrow, text="Speed Controller Parameters",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.sencheckframe = tk.LabelFrame(self.midrow, text="Sensor Checking",
                                           font=("TkDefaultFont", 9, "bold"),
                                           padx=10, pady=10)
        self.leftconsoleframe = tk.LabelFrame(self.botrow, text="Left Leg Output",
                                              font=("TkDefaultFont", 9, "bold"),
                                              padx=10, pady=10)
        self.rightconsoleframe = tk.LabelFrame(self.botrow, text="Right Leg Output",
                                               font=("TkDefaultFont", 9, "bold"),
                                               padx=10, pady=10)

        self.uniconframe.pack(side=LEFT, padx=10, pady=10)
        self.motparframe.pack(side=LEFT, padx=10, pady=10)
        self.torconframe.pack(side=LEFT, padx=10, pady=10)
        self.potconframe.pack(side=LEFT, padx=10, pady=10)
        self.impconframe.pack(side=LEFT, padx=10, pady=10)
        self.speconframe.pack(side=LEFT, padx=10, pady=10)
        self.sencheckframe.pack(side=LEFT, padx=10, pady=10)
        self.leftconsoleframe.pack(side=LEFT, padx=10, pady=10)
        self.rightconsoleframe.pack(side=LEFT, padx=10, pady=10)

        self.toprow.pack(side=TOP)
        self.midrow.pack(side=TOP)
        self.botrow.pack(side=TOP)

        self.createWidgets()

    """This page is for all the parameters that are solely for testing and determining gains and thresholds.
    The create and destroy functions are to make buttons only appear when certain radiobuttons are selected."""

    def createTorqInputs(self):
        # special function for recreating torq setpoint text inputs

        print("createTorqInputs called")

        option_torq = main.p2.TORQOPTIONS.get()

        self.deleteTorqInputs()

        if option_torq == 0:
            self.TORQ = tk.Entry(self.torconframe, width=8)
            self.TORQ.grid(row=3, column=1, sticky=W)
            self.TORQ.insert(END, "5")

            self.ENCODERTOGGLE = tk.Button(self.torconframe, text="Encoder Toggle", command=self.encodertoggle,
                                           relief="groove", overrelief="raised")
            self.ENCODERTOGGLE["fg"] = "blue"
            self.ENCODERTOGGLE.grid(row=1, column=1, sticky=W)

            self.torqLabel = tk.Label(self.torconframe, text="Torque Setpoint (Nm): ")
            self.torqLabel.grid(row=3, column=0)

        elif option_torq == 1:
            self.TORQ = tk.Entry(self.torconframe, width=8)
            self.TORQ.grid(row=3, column=1, sticky=W)
            self.TORQ.insert(END, "5")

            self.TIMESTEP = tk.Entry(self.torconframe, width=8)
            self.TIMESTEP.grid(row=4, column=1, sticky=W)
            self.TIMESTEP.insert(END, "10")

            self.torqLabel = tk.Label(self.torconframe, text="Torque Setpoint (Nm): ")
            self.torqLabel.grid(row=3, column=0)

            self.wavetLabel = tk.Label(self.torconframe, text="Time Step (ms): ")
            self.wavetLabel.grid(row=4, column=0)

        elif option_torq == 2:
            # text input for torque upper limit
            self.TORQUL = tk.Entry(self.torconframe, width=8)
            self.TORQUL.grid(row=3, column=1, sticky=W)
            self.TORQUL.insert(END, "5")

            # text input for torque lower limit
            self.TORQLL = tk.Entry(self.torconframe, width=8)
            self.TORQLL.grid(row=4, column=1, sticky=W)
            self.TORQLL.insert(END, "1")

            # text input for wave time
            self.WAVET = tk.Entry(self.torconframe, width=8)
            self.WAVET.grid(row=5, column=1, sticky=W)
            self.WAVET.insert(END, "1000")

            self.torqulLabel = tk.Label(self.torconframe, text="Torque Upper Limit (Nm): ")
            self.torqulLabel.grid(row=3, column=0)

            self.torqllLabel = tk.Label(self.torconframe, text="Torque Lower Limit (Nm): ")
            self.torqllLabel.grid(row=4, column=0)

            self.wavetLabel = tk.Label(self.torconframe, text="Wave Time (ms): ")
            self.wavetLabel.grid(row=5, column=0)

        global old_torq_option
        old_torq_option = option_torq

    def deleteTorqInputs(self):
        # special function for recreating torq setpoint text inputs
        global old_torq_option

        if old_torq_option == 0:
            self.TORQ.destroy()

            self.torqLabel.destroy()

            self.ENCODERTOGGLE.destroy()

        elif old_torq_option == 1:
            self.TORQ.destroy()

            self.TIMESTEP.destroy()

            self.torqLabel.destroy()

            self.wavetLabel.destroy()

        elif old_torq_option == 2:
            # text input for torque upper limit
            self.TORQUL.destroy()

            # text input for torque lower limit
            self.TORQLL.destroy()

            # text input for wave time
            self.WAVET.destroy()

            self.torqulLabel.destroy()

            self.torqllLabel.destroy()

            self.wavetLabel.destroy()

    def createImpedInputs(self):
        # special function for recreating torq setpoint text inputs

        print("createImpedInputs called")

        option_imped = main.p2.IMPEDOPTIONS.get()

        self.deleteImpedInputs()

        if option_imped == 0:
            self.IMPEDANGLE = tk.Entry(self.impconframe, width=8)
            self.IMPEDANGLE.grid(row=0, column=2, sticky=W)
            self.IMPEDANGLE.insert(END, "14")

            self.impedangleLabel = tk.Label(self.impconframe, text="Static Angle (deg): ")
            self.impedangleLabel.grid(row=0, column=1)

        if option_imped == 2:
            # text input for run time
            self.TIMEBTSWEEP = tk.Entry(self.impconframe, width=8)
            self.TIMEBTSWEEP.grid(row=0, column=2, sticky=W)
            self.TIMEBTSWEEP.insert(END, "10")

            self.timesweepLabel = tk.Label(self.impconframe, text="Time b/t Sweep Angle (ms): ")
            self.timesweepLabel.grid(row=0, column=1)

        global old_imped_option
        old_imped_option = option_imped

    def deleteImpedInputs(self):
        # special function for recreating torq setpoint text inputs
        global old_imped_option

        if old_imped_option == 0:
            self.IMPEDANGLE.destroy()

            self.impedangleLabel.destroy()

        if old_imped_option == 2:
            # text input for run time
            self.TIMEBTSWEEP.destroy()

            self.timesweepLabel.destroy()

    def createMotorInputs(self):
        # special function for recreating torq setpoint text inputs

        print("createImpedInputs called")

        option_motor = main.p2.MOTOROPTIONS.get()

        self.deleteMotorInputs()

        if option_motor == 2:
            # text input for frequency
            self.MOFREQ = tk.Entry(self.motparframe, width=8)
            self.MOFREQ.grid(row=1, column=2, sticky=W)
            self.MOFREQ.insert(END, "5")

            self.MOCURROFFSET = tk.Entry(self.motparframe, width=8)
            self.MOCURROFFSET.grid(row=2, column=2, sticky=W)
            self.MOCURROFFSET.insert(END, "6")

            self.freqLabel = tk.Label(self.motparframe, text="Frequency (Hz): ")
            self.freqLabel.grid(row=1, column=1)

            self.curroffLabel = tk.Label(self.motparframe, text="Current Offset (Hz): ")
            self.curroffLabel.grid(row=2, column=1)

        global old_option_motor
        old_option_motor = option_motor

    def deleteMotorInputs(self):
        # special function for recreating torq setpoint text inputs
        global old_option_motor

        if old_option_motor == 2:
            self.MOFREQ.destroy()
            self.MOCURROFFSET.destroy()

            self.freqLabel.destroy()
            self.curroffLabel.destroy()

    def receive(self):
        # Send 'H' which the Arduino
        # detects as turning the light on
        global buttons_state
        buttons_state = "off"  # ends previous receive_serial_data
        buttons_state = "on"
        receive_data()

    def uploadsettings(self):
        print("Uploading settings")
        send_data(str(len(settsStrML)) + '>', leg='L')
        send_data(settsStrML + '>', leg='L')
        send_data(str(len(settsStrMR)) + '>', leg='R')
        send_data(settsStrMR + '>', leg='R')

    def stop(self):
        # Send ',' to stop data flow from the Arduino
        global buttons_state
        buttons_state = "off"
        data = ","
        send_data(data, 'N', 'N')
        print(data)

    def gains(self):
        # Function makes you mad swole. Run with care
        # To set gains when running controller tests.
        global buttons_state
        buttons_state = "off"
        data = "g"
        send_data(data)  # puts teensy into mode to set gains

        gains_data = construct_gains_string()  # send string with gains data
        send_data(gains_data)

        print(data)
        print("Gains data: " + gains_data)
        receive_data()

    def encodertoggle(self):
        # Send ',' to stop data flow from the Arduino
        send_data('e', 'N', 'N')
        print('e')
        # receive_serial_data()

    def sendpot(self):
        dataL = construct_pot_string('L')
        print('Left Leg: ' + dataL)
        send_data(dataL, leg='L')

        dataR = construct_pot_string('R')
        print('Right Leg: ' + dataR)
        send_data(dataR, leg='R')

        print("Sent Potentiometer Calibration...")
        receive_data()

    def one(self):  # potentiometer
        global buttons_state
        buttons_state = "off"
        data = "1/"
        # send_data(",", 'N', 'N')
        send_data(data)
        buttons_state = "on"
        receive_data()

    def two(self):  # fsr
        global buttons_state
        buttons_state = "off"
        data = "2/"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def three(self):  # torque
        global buttons_state
        buttons_state = "off"
        data = "3/"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def four(self):  # encoder
        global buttons_state
        buttons_state = "off"
        data = "4/"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def five(self):  # motor
        global test_button  # reference for construct_test_param_string()
        test_button = 5

        data = construct_test_param_string()

        # data = "5/"
        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def six(self):  # torque controller
        global test_button  # reference for construct_test_param_string()
        test_button = 6

        self.CONGAINSOPT.set("Torque")

        data = construct_test_param_string()
        # data = "6/"
        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def seven(self):  # impedance based position control
        global test_button  # reference for construct_test_param_string()
        test_button = 7

        self.CONGAINSOPT.set("Impedance")

        data = construct_test_param_string()

        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def eight(self):  # adaptive control
        global test_button  # reference for construct_test_param_string()
        test_button = 8

        self.CONGAINSOPT.set("Adaptive")

        data = construct_test_param_string()
        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()

    def nine(self):  # speed control w/ modulated torque
        global test_button  # reference for construct_test_param_string()
        test_button = 9

        self.CONGAINSOPT.set("Speed")

        data = construct_test_param_string()
        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()
        print(data)

    def eleven(self):  # e stim
        data = "11/"
        global buttons_state
        buttons_state = "off"
        send_data(data)
        buttons_state = "on"
        receive_data()
        print(data)

    def createWidgets(self):
        """ Creates all the buttons on the preliminary testing page.
        Look at a Tkinter reference online for explanations. """

        # == Universal Controller Parameters Frame ====================================================================
        # text input for pgain
        self.PGAIN = tk.Entry(self.uniconframe, width=8)
        self.PGAIN.grid(row=0, column=1, sticky=W)
        self.PGAIN.insert(END, "425")

        # text input for igain
        self.IGAIN = tk.Entry(self.uniconframe, width=8)
        self.IGAIN.grid(row=1, column=1, sticky=W)
        self.IGAIN.insert(END, "1300")

        # text input for dgain
        self.DGAIN = tk.Entry(self.uniconframe, width=8)
        self.DGAIN.grid(row=2, column=1, sticky=W)
        self.DGAIN.insert(END, ".3")

        self.SETGAINS = Button(self.uniconframe, relief="groove", overrelief="raised")
        self.SETGAINS["text"] = "Set Gains"
        self.SETGAINS["fg"] = "blue"
        self.SETGAINS["command"] = self.gains
        self.SETGAINS.grid(row=0, column=2, sticky=W, padx=10)

        self.CONGAINSOPT = tk.StringVar(self)
        self.CONGAINSOPT.set("Torque")

        # change to combo box
        self.ConGainMenu = OptionMenu(self.uniconframe, self.CONGAINSOPT, "Torque", "Impedance", "Adaptive", "Speed")
        self.ConGainMenu.grid(row=1, column=2, sticky=W, padx=10)

        pLabel = tk.Label(self.uniconframe, text="P Gain: ")
        pLabel.grid(row=0, column=0)

        iLabel = tk.Label(self.uniconframe, text="I Gain: ")
        iLabel.grid(row=1, column=0)

        dLabel = tk.Label(self.uniconframe, text="D Gain: ")
        dLabel.grid(row=2, column=0)

        # == Motor Parameters Frame ===================================================================================
        # text input for current
        self.MOCURRENT = tk.Entry(self.motparframe, width=8)
        self.MOCURRENT.grid(row=0, column=2, sticky=W)
        self.MOCURRENT.insert(END, "4")

        # torque response radio button
        motorType = [
            ("Constant Current", 0),
            ("Ramp Up To Current", 1),
            ("Sine Wave", 2),
        ]

        self.MOTOROPTIONS = tk.IntVar()
        self.MOTOROPTIONS.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.MOTOROPTIONS.get())

        for language, val in motorType:
            tk.Radiobutton(self.motparframe,
                           text=language,
                           padx=20,
                           variable=self.MOTOROPTIONS,
                           command=self.createMotorInputs,
                           value=val).grid(row=(val), column=0)

        currentLabel = tk.Label(self.motparframe, text="Current (A): ")
        currentLabel.grid(row=0, column=1)

        # == Torque Controller Parameters Frame =======================================================================
        torqrType = [
            ("Constant Torque", 0),
            ("Stepwise Response", 1),
            ("Sinusoidal Wave (Bandwidth Test)", 2),
            # ("Sinusoidal Wave (Single Test)", 3),  # need to revise Arduino Left Leg code for this to work
        ]

        self.TORQOPTIONS = tk.IntVar()
        self.TORQOPTIONS.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.TORQOPTIONS.get())

        for language, val in torqrType:
            tk.Radiobutton(self.torconframe,
                           text=language,
                           padx=20,
                           variable=self.TORQOPTIONS,
                           command=self.createTorqInputs,
                           value=val).grid(row=(val), column=0)

        # text input for torque upper limit
        self.TORQ = tk.Entry(self.torconframe, width=8)
        self.TORQ.grid(row=3, column=1, sticky=W)
        self.TORQ.insert(END, "5")

        self.ENCODERTOGGLE = tk.Button(self.torconframe, text="Encoder Toggle", command=self.encodertoggle,
                                       relief="groove", overrelief="raised")
        self.ENCODERTOGGLE["fg"] = "blue"
        self.ENCODERTOGGLE.grid(row=1, column=1, sticky=W)

        self.torqLabel = tk.Label(self.torconframe, text="Torque Setpoint (Nm): ")
        self.torqLabel.grid(row=3, column=0)

        # == Potentiometer Parameters Frame ===========================================================================
        self.LPOTLOW = tk.Entry(self.potconframe, width=8)
        self.LPOTLOW.grid(row=0, column=1)
        self.LPOTLOW.insert(END, '3333')

        self.LPOTHIGH = tk.Entry(self.potconframe, width=8)
        self.LPOTHIGH.grid(row=1, column=1)
        self.LPOTHIGH.insert(END, '1827')

        lpotlowlbl = tk.Label(self.potconframe, text="Left Pot 0: ")
        lpotlowlbl.grid(row=0, column=0)

        lpothighlbl = tk.Label(self.potconframe, text="Left Pot 90: ")
        lpothighlbl.grid(row=1, column=0)

        self.RPOTLOW = tk.Entry(self.potconframe, width=8)
        self.RPOTLOW.grid(row=2, column=1)
        self.RPOTLOW.insert(END, '2743')

        self.RPOTHIGH = tk.Entry(self.potconframe, width=8)
        self.RPOTHIGH.grid(row=3, column=1)
        self.RPOTHIGH.insert(END, '1325')

        rpotlowlbl = tk.Label(self.potconframe, text="Right Pot 0: ")
        rpotlowlbl.grid(row=2, column=0)

        rpothighlbl = tk.Label(self.potconframe, text="Right Pot 90: ")
        rpothighlbl.grid(row=3, column=0)

        self.SENDPOT = Button(self.potconframe, relief="groove", overrelief="raised")
        self.SENDPOT["text"] = "Set Pots"
        self.SENDPOT["fg"] = "blue"
        self.SENDPOT["command"] = self.sendpot
        self.SENDPOT.grid(row=4, column=0, columnspan=2, pady=5)

        # == Impedance Controller Parameters Frame ====================================================================
        impedType = [
            ("Static", 0),
            ("Sweep (Closeness Based)", 1),
            ("Sweep (Timer Based)", 2),
        ]

        self.IMPEDOPTIONS = tk.IntVar()
        self.IMPEDOPTIONS.set(0)

        def ShowChoice():  # prints selected button; replace later
            print(self.IMPEDOPTIONS.get())

        for language, val in impedType:
            tk.Radiobutton(self.impconframe,
                           text=language,
                           padx=20,
                           variable=self.IMPEDOPTIONS,
                           command=self.createImpedInputs,
                           value=val).grid(row=(val), column=0)

        # impedance static angle entry
        self.IMPEDANGLE = tk.Entry(self.impconframe, width=8)
        self.IMPEDANGLE.grid(row=0, column=2, sticky=W)
        self.IMPEDANGLE.insert(END, "14")

        self.impedangleLabel = tk.Label(self.impconframe, text="Static Angle (deg): ")
        self.impedangleLabel.grid(row=0, column=1)

        # == Speed Controller Parameters Frame ========================================================================
        # text input for speed
        self.SPEED = tk.Entry(self.speconframe, width=8)
        self.SPEED.grid(row=0, column=1, sticky=W)
        self.SPEED.insert(END, "4")

        # text input for run time
        self.RUNTIME = tk.Entry(self.speconframe, width=8)
        self.RUNTIME.grid(row=1, column=1, sticky=W)
        self.RUNTIME.insert(END, "1000")

        speedLabel = tk.Label(self.speconframe, text="Speed (deg/s): ")
        speedLabel.grid(row=0, column=0)

        runtimeLabel = tk.Label(self.speconframe, text="Run Time (ms): ")
        runtimeLabel.grid(row=1, column=0)

        # == Sensor Checking Frame ====================================================================================
        # The numbers are the encodings for these sensors between Python/Arduino code

        self.ONE = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.ONE["text"] = "Potentiometer"
        self.ONE["fg"] = "#006400"
        self.ONE["command"] = self.one
        self.ONE.grid(row=0, column=0)

        self.TWO = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.TWO["text"] = "Force Sensitive Resistor"
        self.TWO["fg"] = "#006400"
        self.TWO["command"] = self.two
        self.TWO.grid(row=1, column=0)

        self.THREE = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.THREE["text"] = "Torque"
        self.THREE["fg"] = "#006400"
        self.THREE["command"] = self.three
        self.THREE.grid(row=2, column=0)

        self.FOUR = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.FOUR["text"] = "Encoder"
        self.FOUR["fg"] = "#006400"
        self.FOUR["command"] = self.four
        self.FOUR.grid(row=0, column=1)

        self.FIVE = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.FIVE["text"] = "Motor"
        self.FIVE["fg"] = "#006400"
        self.FIVE["command"] = self.five
        self.FIVE.grid(row=1, column=1)

        self.SIX = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.SIX["text"] = "Torque Controller"
        self.SIX["fg"] = "#006400"
        self.SIX["command"] = self.six
        self.SIX.grid(row=2, column=1)

        self.SEVEN = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.SEVEN["text"] = "Impedance Control"
        self.SEVEN["fg"] = "#006400"
        self.SEVEN["command"] = self.seven
        self.SEVEN.grid(row=0, column=2)

        self.EIGHT = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.EIGHT["text"] = "Adaptive Control"
        self.EIGHT["fg"] = "#006400"
        self.EIGHT["command"] = self.eight
        self.EIGHT.grid(row=1, column=2)

        self.NINE = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.NINE["text"] = "Speed Control"
        self.NINE["fg"] = "#006400"
        self.NINE["command"] = self.nine
        self.NINE.grid(row=2, column=2)

        self.STOP = Button(self.sencheckframe, relief="groove", overrelief="raised")
        self.STOP["text"] = "Stop"
        self.STOP["fg"] = "red"
        self.STOP["command"] = self.stop
        self.STOP.grid(row=0, column=3, padx=10)

        # == Console Frames ===========================================================================================
        # left leg console scrolled text widget
        self.LeftConsole = scrolledtext.ScrolledText(
            master=self.leftconsoleframe,
            wrap=WORD,
            width=65,
            height=18
        )
        self.LeftConsole.grid(column=0, row=0, sticky=W)

        # right leg console scrolled text widget
        self.RightConsole = scrolledtext.ScrolledText(
            master=self.rightconsoleframe,
            wrap=WORD,
            width=65,
            height=18
        )
        self.RightConsole.grid(column=0, row=0)


class EstimPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        # label = tk.Label(self, text="This is page 2")
        # label.pack(side="top", fill="both", expand=True)
        self.toprow = tk.Frame(self)
        self.botrow = tk.Frame(self)

        self.manbutframe = tk.LabelFrame(self.toprow, text="Manual Button Press",
                                         font=("TkDefaultFont", 9, "bold"),
                                         padx=10, pady=10)
        self.chanampframe = tk.Frame(self.toprow, padx=10, pady=10)
        self.sigoptframe = tk.Frame(self.botrow, padx=10, pady=10)
        self.otheroptframe = tk.Frame(self.botrow, padx=10, pady=10)

        self.manbutframe.pack(side=LEFT, padx=10, pady=10)
        self.chanampframe.pack(side=LEFT, padx=10, pady=10)
        self.sigoptframe.pack(side=LEFT, padx=10, pady=10)
        self.otheroptframe.pack(side=LEFT, padx=10, pady=10)

        self.toprow.pack(side=TOP)
        self.botrow.pack(side=TOP)

        self.createWidgets()

    def toggle_ch1(self):
        '''
        use
        t_btn.config('text')[-1]
        to get the present state of the toggle button
        '''
        if self.t_btn_ch1.config('text')[-1] == 'On':
            self.t_btn_ch1.config(text='Off',
                                  relief="sunken")
        else:
            self.t_btn_ch1.config(text='On',
                                  relief="groove")

    def toggle_ch2(self):
        '''
        use
        t_btn.config('text')[-1]
        to get the present state of the toggle button
        '''
        if self.t_btn_ch2.config('text')[-1] == 'On':
            self.t_btn_ch2.config(text='Off',
                                  relief="sunken")
        else:
            self.t_btn_ch2.config(text='On',
                                  relief="groove")

    def toggle_ch3(self):
        '''
        use
        t_btn.config('text')[-1]
        to get the present state of the toggle button
        '''
        if self.t_btn_ch3.config('text')[-1] == 'On':
            self.t_btn_ch3.config(text='Off',
                                  relief="sunken")
        else:
            self.t_btn_ch3.config(text='On',
                                  relief="groove")

    def toggle_ch4(self):
        '''
        use
        t_btn.config('text')[-1]
        to get the present state of the toggle button
        '''
        if self.t_btn_ch4.config('text')[-1] == 'On':
            self.t_btn_ch4.config(text='Off',
                                  relief="sunken")
        else:
            self.t_btn_ch4.config(text='On',
                                  relief="groove")

    def createWidgets(self):

        # == MANUAL BUTTON FRAME ===

        # upload button pictures
        self.up_button = PhotoImage(file="./graphics/up_button.gif")  # up button pic
        self.down_button = PhotoImage(file="./graphics/down_button.gif")  # down button pic

        # channel 1 up/down buttons
        self.ch1lab = tk.Label(self.manbutframe, text="CH 1")
        self.ch1lab.grid(row=0, column=0, padx=10, pady=10)

        self.t_btn_ch1 = tk.Button(self.manbutframe, text="On", width=6, command=self.toggle_ch1)
        self.t_btn_ch1.grid(row=1, column=0, padx=10, pady=10)

        self.ch1up = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.up_button)
        self.ch1up.grid(row=2, column=0, padx=10, pady=10)

        self.ch1down = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.down_button)
        self.ch1down.grid(row=3, column=0, padx=10, pady=10)

        self.inc_button = PhotoImage(file="./graphics/inc_button.gif")  # down button pic
        self.estim_increment = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.inc_button)
        self.estim_increment.grid(row=4, column=0, padx=10, pady=10)

        # channel 2 up/down buttons
        self.ch2lab = tk.Label(self.manbutframe, text="CH 2")
        self.ch2lab.grid(row=0, column=1, padx=10, pady=10)

        self.t_btn_ch2 = tk.Button(self.manbutframe, text="On", width=6, command=self.toggle_ch2)
        self.t_btn_ch2.grid(row=1, column=1, padx=10, pady=10)

        self.ch2up = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.up_button)
        self.ch2up.grid(row=2, column=1, padx=10, pady=10)

        self.ch2down = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.down_button)
        self.ch2down.grid(row=3, column=1, padx=10, pady=10)

        self.dec_button = PhotoImage(file="./graphics/dec_button.gif")  # decrement button pic
        self.estim_decrement = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.dec_button)
        self.estim_decrement.grid(row=4, column=1, padx=10, pady=10)

        # channel 3 up/down buttons
        self.ch3lab = tk.Label(self.manbutframe, text="CH 3")
        self.ch3lab.grid(row=0, column=2, padx=10, pady=10)

        self.t_btn_ch3 = tk.Button(self.manbutframe, text="On", width=6, command=self.toggle_ch3)
        self.t_btn_ch3.grid(row=1, column=2, padx=10, pady=10)

        self.ch3up = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.up_button)
        self.ch3up.grid(row=2, column=2, padx=10, pady=10)

        self.ch3down = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.down_button)
        self.ch3down.grid(row=3, column=2, padx=10, pady=10)

        self.set_button = PhotoImage(file="./graphics/set_button.gif")  # set button pic
        self.estim_set = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.set_button)
        self.estim_set.grid(row=4, column=2, padx=10, pady=10)

        # channel 4 up/down buttons
        self.ch4lab = tk.Label(self.manbutframe, text="CH 4")
        self.ch4lab.grid(row=0, column=3, padx=10, pady=10)

        self.t_btn_ch4 = tk.Button(self.manbutframe, text="On", width=6, command=self.toggle_ch4)
        self.t_btn_ch4.grid(row=1, column=3, padx=10, pady=10)

        self.ch4up = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.up_button)
        self.ch4up.grid(row=2, column=3, padx=10, pady=10)

        self.ch4down = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.down_button)
        self.ch4down.grid(row=3, column=3, padx=10, pady=10)

        self.mode_button = PhotoImage(file="./graphics/mode_button.gif")  # mode button pic
        self.estim_mode = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.mode_button)
        self.estim_mode.grid(row=4, column=3, padx=10, pady=10)

        self.pwr_button = PhotoImage(file="./graphics/pwr_button.gif")  # pwr button pic
        self.pwr_onoff = tk.Button(self.manbutframe, relief="groove", overrelief="raised", image=self.pwr_button)
        self.pwr_onoff.grid(row=5, column=3, padx=10, pady=10)

        # == CHANNEL AMPLITUDE FRAME ===

        self.chanamplabel = tk.Label(self.chanampframe, text="Channel Amplitude",
                                     font=("TkDefaultFont", 9, "bold"),
                                     padx=10, pady=10)
        self.chanamplabel.grid(row=0, column=0, columnspan=4)

        self.ch1lab = tk.Label(self.chanampframe, text="CH 1")
        self.ch1lab.grid(row=1, column=0, padx=5)

        self.MAGSLIDERCH1 = tk.Scale(self.chanampframe, from_=0, to=99, length=300, tickinterval=10, orient="vertical")
        self.MAGSLIDERCH1.set(50)
        self.MAGSLIDERCH1.grid(row=2, column=0, padx=10)

        self.ch2lab = tk.Label(self.chanampframe, text="CH 2")
        self.ch2lab.grid(row=1, column=2, padx=5)

        self.MAGSLIDERCH2 = tk.Scale(self.chanampframe, from_=0, to=99, length=300, tickinterval=10, orient="vertical")
        self.MAGSLIDERCH2.set(50)
        self.MAGSLIDERCH2.grid(row=2, column=2, padx=10)

        self.ch3lab = tk.Label(self.chanampframe, text="CH 3")
        self.ch3lab.grid(row=1, column=3, padx=5)

        self.MAGSLIDERCH3 = tk.Scale(self.chanampframe, from_=0, to=99, length=300, tickinterval=10, orient="vertical")
        self.MAGSLIDERCH3.set(50)
        self.MAGSLIDERCH3.grid(row=2, column=3, padx=10)

        self.ch4lab = tk.Label(self.chanampframe, text="CH 4")
        self.ch4lab.grid(row=1, column=4, padx=5)

        self.MAGSLIDERCH4 = tk.Scale(self.chanampframe, from_=0, to=99, length=300, tickinterval=10, orient="vertical")
        self.MAGSLIDERCH4.set(50)
        self.MAGSLIDERCH4.grid(row=2, column=4, padx=10)

        # == SIGNAL OPTIONs FRAME ===

        # signaloptionlbl = tk.Label(self.sigoptframe, text="Signal Options",
        #                                  font=("TkDefaultFont", 9, "bold"),
        #                                  padx=10, pady=10)
        # signaloptionlbl.grid(row=0, column=0)

        self.FREQSLIDER = tk.Scale(self.sigoptframe, from_=2, to=150, length=300,
                                   tickinterval=18, orient="horizontal")
        self.FREQSLIDER.set(23)
        self.FREQSLIDER.grid(row=2, column=0)

        self.PWSLIDER = tk.Scale(self.sigoptframe, from_=50, to=300, length=300,
                                 tickinterval=30, orient="horizontal", resolution=10)
        self.PWSLIDER.set(23)
        self.PWSLIDER.grid(row=4, column=0)

        freqLabel = tk.Label(self.sigoptframe, text="Frequency (Hz) ")
        freqLabel.grid(row=1, column=0)

        pulseLabel = tk.Label(self.sigoptframe, text="Pulse Width (ms)")
        pulseLabel.grid(row=3, column=0)

        # == OTHER OPTIONS FRAME ===

        # signaloptionlbl = tk.Label(self.otheroptframe, text="Other Options",
        #                                  font=("TkDefaultFont", 9, "bold"),
        #                                  padx=10, pady=10)
        # signaloptionlbl.grid(row=0, column=0)

        timeLabel = tk.Label(self.otheroptframe, text="Time")
        timeLabel.grid(row=1, column=0)

        self.TIMEOPT = tk.StringVar(self)
        self.TIMEOPT.set("Infinite")

        self.TimeMenu = OptionMenu(self.otheroptframe, self.TIMEOPT, "Infinite")
        self.TimeMenu.grid(row=2, column=0)

        modeLabel = tk.Label(self.otheroptframe, text="Mode")
        modeLabel.grid(row=3, column=0)

        self.MODEOPT = tk.StringVar(self)
        self.MODEOPT.set("EMS Constant")

        self.ModeMenu = OptionMenu(self.otheroptframe, self.MODEOPT, "EMS Constant")
        self.ModeMenu.grid(row=4, column=0)

        # upload settings button
        self.UPLOADSETTINGS = tk.Button(self.otheroptframe, relief="groove", overrelief="raised")
        self.UPLOADSETTINGS["text"] = "Upload Settings"
        self.UPLOADSETTINGS["fg"] = "blue"
        self.UPLOADSETTINGS.config(font=
                                   ('TKDefaultFont', 10, 'bold'))
        self.UPLOADSETTINGS.grid(row=1, column=1, padx=5, pady=5)
        # self.UPLOADSETTINGS["command"] = self.uploadsettings2


# need MainView to inherit MainMenuPage & Estim Pages so widgets from MainMenuPage & Estim can be accessed
class MainView(tk.Frame):  # MainMenuPage,
    """MainView instantiates all of the GUI pages (LandingPage(), TestingPage(), MainMenuPage(), and EstimPage(),
    places them on the screen, and allows them to be called by the buttons that constantly appear at the bottom of
    the GUI.
    """
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.p7 = LandingPage(self)
        self.p2 = TestingPage(self)  # originally, MainMenu came first. Too lazy to rewrite all this.
        self.p1 = MainMenuPage(self)
        self.p3 = EstimPage(self)

        self.winfo_toplevel().title("NIH P.Rex GUI")

        buttonframe = tk.Frame(self)
        container = tk.Frame(self)

        buttonframe.pack(side="bottom", anchor=E, fill="x", expand=False)
        container.pack(side="top", fill="both", expand=True)

        self.p1.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        self.p2.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        self.p3.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        self.p7.place(in_=container, x=0, y=0, relwidth=1, relheight=1)

        self.b7 = tk.Button(buttonframe, text="Instructions", command=self.p7.lift, relief="groove",
                            overrelief="raised")
        self.b2 = tk.Button(buttonframe, text="Prelim Tests", command=self.p2fun, relief="groove", overrelief="raised")
        self.b1 = tk.Button(buttonframe, text="Run Trial", command=self.p1fun, relief="groove", overrelief="raised")
        self.b3 = tk.Button(buttonframe, text="E Stim", command=self.p3.lift, relief="groove", overrelief="raised")
        self.b8 = tk.Button(buttonframe, text="Bluetooth", command=self.create_ble_window, relief="groove",
                            overrelief="raised")
        self.b9 = tk.Button(buttonframe, text="Wire", command=self.create_ser_window, relief="groove",
                            overrelief="raised")

        self.lab1 = tk.Label(buttonframe, text="Connection Type: ")
        self.logoimage = PhotoImage(file="./graphics/nih_logo_3.gif")  # NIH logo in the bottom righthand corner
        self.lablogo = tk.Label(buttonframe, image=self.logoimage)

        self.b7.pack(side=LEFT)
        self.b2.pack(side=LEFT)
        self.b1.pack(side=LEFT)
        self.b3.pack(side=LEFT)
        self.lablogo.pack(side=RIGHT)
        self.b8.pack(side=RIGHT)
        self.b9.pack(side=RIGHT)
        self.lab1.pack(side=RIGHT)

        self.p7.show()
        global page
        page = "trialpage"

    def p2fun(self):  # stuff to do when the Prelim Test button is pressed
        """This function insures that if the PID gains text inputs on the Prelim Tests page are changed,
        the change will be seen on for the PID gains text inputs Run Trial page"""
        self.p2.lift()
        global page
        page = "testpage"

        p = self.p1.PGAIN.get()
        i = self.p1.IGAIN.get()
        d = self.p1.DGAIN.get()

        self.p2.PGAIN.delete(0, 'end')
        self.p2.IGAIN.delete(0, 'end')
        self.p2.DGAIN.delete(0, 'end')

        self.p2.PGAIN.insert(END, p)
        self.p2.IGAIN.insert(END, i)
        self.p2.DGAIN.insert(END, d)

    def p1fun(self):  # stuff to do when the Trial Menu button is pressed
        """This function insures that if the PID gains text inputs on the Prelim Tests page are changed,
        the change will be seen on for the PID gains text inputs Run Trial page"""
        self.p1.lift()
        global page
        page = "trialpage"

        p = self.p2.PGAIN.get()
        i = self.p2.IGAIN.get()
        d = self.p2.DGAIN.get()

        self.p1.PGAIN.delete(0, 'end')
        self.p1.IGAIN.delete(0, 'end')
        self.p1.DGAIN.delete(0, 'end')

        self.p1.PGAIN.insert(END, p)
        self.p1.IGAIN.insert(END, i)
        self.p1.DGAIN.insert(END, d)

    def connectBLE(self):
        global comType
        comType = 'BLE'

        add1 = str(self.LMACADDRESS.get())  # address 1
        add2 = str(self.RMACADDRESS.get())
        connect_to_exo(comType, add1, add2)

    def create_ble_window(self):  # creates subwindow with mac addresses, facilitates initial connection to Arduino
        bluetooth_menu = tk.Toplevel(self)
        self.bt_menu_frame = tk.Frame(bluetooth_menu)
        self.bt_menu_frame.pack(side=TOP, padx=20, pady=20)
        # t.wm_title("Window" % self.counter)
        self.bt_lbl = tk.Label(self.bt_menu_frame, text="Bluetooth Setup Window")
        self.bt_lbl.config(font=
                           ('TKDefaultFont', 9, 'bold'))
        self.bt_lbl.grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.LMACADDRESS = tk.Entry(self.bt_menu_frame, width=20)
        self.LMACADDRESS.grid(row=1, column=1)

        self.RMACADDRESS = tk.Entry(self.bt_menu_frame, width=20)
        self.RMACADDRESS.grid(row=2, column=1)

        self.BLECONBOX = tk.Label(self.bt_menu_frame, width=40, height=10)
        self.BLECONBOX.grid(row=4, column=0, columnspan=2)
        self.BLECONBOX['text'] = "Connection Confirmation:"

        # testing mac addresses
        # serverMACAddress = '00:06:66:FB:AD:2B'  # left leg
        # serverMACAddress1 = '00:06:66:FB:AD:C7'  # right leg

        # for real mac addresses
        # serverMACAddress = '00:06:66:84:86:32'  # left leg
        # serverMACAddress1 = '00:06:66:8C:9B:B9'  # right leg

        self.LMACADDRESS.insert(END, '00:06:66:84:86:32')
        self.RMACADDRESS.insert(END, '00:06:66:8C:9B:B9')

        #self.LMACADDRESS.insert(END, '00:06:66:FB:AD:C7')
        #self.RMACADDRESS.insert(END, '00:06:66:FB:AD:2B')

        #self.LMACADDRESS.insert(END, '00:06:66:CF:B6:11')
        #self.RMACADDRESS.insert(END, '00:06:66:CF:BE:17')

        left_mac_lbl = tk.Label(self.bt_menu_frame, text="Left Mac Address")
        left_mac_lbl.grid(row=1, column=0)

        right_mac_lbl = tk.Label(self.bt_menu_frame, text="Right Mac Address")
        right_mac_lbl.grid(row=2, column=0)

        self.CONNECT_BLE = tk.Button(self.bt_menu_frame, text="Connect Bluetooth", command=self.connectBLE)
        self.CONNECT_BLE.grid(row=3, column=0, columnspan=2, pady=10)

    def connectSER(self):
        global comType
        comType = 'Ser'

        add1 = str(self.LCOMPORT.get())  # address 1
        add2 = str(self.RCOMPORT.get())
        connect_to_exo(comType, add1, add2)

    def create_ser_window(self):  # creates subwindow with USB ports, facilitates initial connection to Arduino
        serial_menu = tk.Toplevel(self)
        self.ser_menu_frame = tk.Frame(serial_menu)
        self.ser_menu_frame.pack(side=TOP, padx=20, pady=20)
        # t.wm_title("Window" % self.counter)
        self.ser_lbl = tk.Label(self.ser_menu_frame, text="Serial Setup Window")
        self.ser_lbl.config(font=
                            ('TKDefaultFont', 9, 'bold'))
        self.ser_lbl.grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.LCOMPORT = tk.Entry(self.ser_menu_frame, width=20)
        self.LCOMPORT.grid(row=1, column=1)

        self.RCOMPORT = tk.Entry(self.ser_menu_frame, width=20)
        self.RCOMPORT.grid(row=2, column=1)

        self.SERCONBOX = tk.Label(self.ser_menu_frame, width=40, height=10)
        self.SERCONBOX.grid(row=4, column=0, columnspan=2)
        self.SERCONBOX['text'] = "Connection Confirmation:"

        # testing mac addresses
        # serverMACAddress = '00:06:66:FB:AD:2B'  # left leg
        # serverMACAddress1 = '00:06:66:FB:AD:C7'  # right leg

        # for real mac addresses
        # serverMACAddress = '00:06:66:84:86:32'  # left leg
        # serverMACAddress1 = '00:06:66:8C:9B:B9'  # right leg

        self.LCOMPORT.insert(END, 'COM5')
        self.RCOMPORT.insert(END, 'COM6')

        left_com_lbl = tk.Label(self.ser_menu_frame, text="Left Com Port")
        left_com_lbl.grid(row=1, column=0)

        right_com_lbl = tk.Label(self.ser_menu_frame, text="Right Com Port")
        right_com_lbl.grid(row=2, column=0)

        self.CONNECT_SER = tk.Button(self.ser_menu_frame, text="Connect Serial", command=self.connectSER)
        self.CONNECT_SER.grid(row=3, column=0, columnspan=2, pady=10)


root = tk.Tk()
root.wm_geometry("1330x750")  # overall size of the GUI
# can't exceed 1336x768 for HP Elitebook 850, 15.6 inch computer

main = MainView(master=root)  # instantiates MainView, which instantiates all pages and widgets
main.pack(side="top", fill="both", expand=True)
root.mainloop()  # constantly updates main to look for user interaction and display things on the GUI
