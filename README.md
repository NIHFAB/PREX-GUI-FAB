## Table of Contents
* [Overview](#Overview)
* [System Requirements](#system-requirements)
* [Software Installation](#software-installation)
* [Functionalities of the script](#functionalities-of-the-script)
* [Step-by-Step Tutorial](#step-by-step-tutorial)
* [Publications](#publications)


# Overview
Open source code for the NIH PRex Exoskeleton Graphical User Interface (GUI). Includes shell AVR-C (Arduino) operating system, Python GUI, Unity plotting application, and an MIT App Inventor project (phone app for Android).

All software is protected under the GNU General Public License, version 3 (GPLv3), found in 'LICENSE.md'. 

# System Requirements
1. 64-bit versions of Microsoft Windows 10, 8
2. 2 GB RAM minimum, 8 GB RAM recommended
3. 2.5 GB hard disk space, SSD recommended
4. 1024x768 minimum screen resolution
5. Python 3.5 or newer

# Software Installation
To implement the GUI 
1. Python: installation link: https://www.python.org/downloads/ (The minimum 3.5 version)
2. Three additional python libraries
   1) pyserial (for serial communication between GUI and exoskeleton): 
      How to install: go to your command prompt and run it as administrator and type: pip install pyserial
   2) pybluez  (for bluetooth communication between GUI and exoskeleton):
      How to install: follow this link to install pybluez: https://pybluez.readthedocs.io/en/latest/install.html
   3) TkInter (for GUI features such as buttons, bars, and textboxes to be created): 
      How to install: download Active Tcl-8.6 (or Active Tcl-8.5).https://www.activestate.com/products/tcl/downloads/
3. Pycharm (python IDE for code development): installation link: https://www.jetbrains.com/pycharm/download/#section=windows
3. Lab Streaming Layer (data synchronization and saving): download link: https://github.com/sccn/labstreaminglayer
4. Unity (for realtime data visualization): download link: https://store.unity.com/download-nuo 

## Important Dependencies (Python script need them to run properly)
1. Lab Streaming Layer (LSL)  Libararies (the LabRecorder control panel and LabRecorder interface in python environment)
2. Python Libraries (time, tkinter, os, sys, pylsl, pyserial, subprocess, PyBluez)

After downloading the PRex-GUI folder, add a working copy of pylsl (from Lab Streaming Layer) and a folder containing a working copy of LabRecorder to the folder to make PRex-GUI.py run.

# Functionalities of the script
The script can be categorized into the following blocks to help understand its overall structure. 

## Block 1: Setup Communication
* This block is to set up the communication mode by either cable-based serial or bluetooth.
```
connect_to_exo(comType, address1, address2)
```

## Block 2: Data Entry Functions
* This block is to draw user input from the GUI widgets into a single string, which can then be sent to Arduino controller in exoskeleton. The following functions are created to draw the inputs. 

### Prepare the input data
```
construct_data_string_left():..
construct_data_string_right():..
construct_test_param_string():..
construct_gains_string():..
construct_pot_string(leg):..
```
### Send the input data to the micro-controller in the robotic
```
Send_data(data, prefix = ‘Y’, parse = ‘Y’, leg = ‘B’)
```
## Block 3: Data Receiving Functions
* This block is to control data collection cycle and perform data collection in calibration mode, and coordinate with lab streaming layer to collect the walking data during walking mode. 

### start/stop the data collection cycle
```
start_trial();
```
### receiving data functions for device calibration mode
```
receive_data();
receive_serial_data();
receive_ble_data();
```
### receiving data functions for walking mode
```
receive_and_save_data(); (work together with LSL package)
receive_ser_data_and_send2LSL();
receive_ble_data_and_send2LSL();
```
## Block 4: Modular Control Panel (written in class)

* MainView is created as a frame to inherit different control pages using TkInter functionalities
```
root = tk.Tk()
root.wm_geometry("1330x750")
main = MainView(master=root)
main.pack(side="top", fill="both", expand=True)
root.mainloop()
```

MainView(tk.Frame): construct the frame with configurable control panels.

Page(tk.Frame): view the selected page

The individual panels are customized to meet the purpose of controlling and communicating with a robotic exoskeleton.
```
LandingPage(Page);
MainMenuPage(Page);
TestingPage(Page);
EstimPage(Page);
```
## Block 5: Real-Time Data Streaming

* Lab streaming layer interface is created in the script to collect the exoskeleton data from both left and right leg
```
lab_recorder_subprocess = subprocess.Popen(os.path.normpath("./LabRecorder/LabRecorder.exe"))
# == Left Leg LSL ===
info_LL = StreamInfo('LeftLeg', 'Exoskeleton', 8, 100, 'float32', 'JiComp')  # creates 8 channel LSL stream
channels = info_LL.desc().append_child("channels") # append some meta-data
for c in ["TimeLL", "AngleLL", "TorqueLL", "FSR LL", "CurrentLL", "FSM StateLL", "Torque SetpointLL",
          "Position SetpointLL"]:
    channels.append_child("channel") \
        .append_child_value("label", c)
outlet_LL = StreamOutlet(info_LL)  # creates outlet for left leg

# == Right Leg LSL ===
info_RL = StreamInfo('RightLeg', 'Exoskeleton', 8, 100, 'float32', 'JiComp')  # creates 8 channel LSL stream
channels = info_RL.desc().append_child("channels") # append some meta-data
for c in ["TimeRL", "AngleRL", "TorqueRL", "FSR RL", "CurrentRL", "FSM StateRL", "Torque SetpointRL",
          "Position SetpointRL"]:
    channels.append_child("channel") \
        .append_child_value("label", c)
outlet_RL = StreamOutlet(info_RL)  # creates outlet for right leg
```
## Block 6: Real-Time Data Visualization

* Unity interface is created to visualize all sensor data
```
plotting_subprocess = subprocess.Popen(os.path.normpath("./backend_plotting/Static Grip Device.exe"))
```

# Step-by-Step Tutorial
Before using the code in this repository on a project, it is helpful to understand how information flows in the code. To really understand how the software works, one must understand how data might travel from the graphical user interface (GUI) to an embedded microcontroller (i.e. a Teensy or Arduino) and vice versa. Visit the Wiki page (https://github.com/NIHFAB/PREX-GUI-FAB/wiki) for more details.


# Publications
If using this software, please cite "An Open Source Graphical User Interface for Wearable Robotic Technology." This work provides an overview of the software and recommendations for how to modify this software for your project. 
