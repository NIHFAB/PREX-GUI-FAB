# PRex-Interface
Open source code for the NIH PRex Exoskeleton Graphical User Interface (GUI). Includes shell AVR-C (Arduino) operating system, Python GUI, Unity plotting application, and an MIT App Inventor project (phone app for Android).

All software is protected under the GNU General Public License, version 3 (GPLv3), found in 'LICENSE.md'. 

# System requirements
1. 64-bit versions of Microsoft Windows 10, 8
2. 2 GB RAM minimum, 8 GB RAM recommended
3. 2.5 GB hard disk space, SSD recommended
4. 1024x768 minimum screen resolution
5. Python 3.5 or newer

# Required softwares
To implement the GUI 
1. Python: installation link: https://www.python.org/downloads/ (The minimum 3.5 version)
2. Two additional python libraries
   1) pyserial (for serial communication between GUI and exoskeleton): 
      How to install: go to your command prompt and run it as administrator and type: pip install pyserial
   2) pybluez  (for bluetooth communication between GUI and exoskeleton):
      How to install: follow this link to install pybluez: https://pybluez.readthedocs.io/en/latest/install.html
3. Pycharm (python IDE for code development): installation link: https://www.jetbrains.com/pycharm/download/#section=windows
3. Lab Streaming Layer (data synchronization and saving): download link: https://github.com/sccn/labstreaminglayer
4. Unity (for realtime data visualization): download link: https://store.unity.com/download-nuo 

# Step 1. data entry functions

The first step is to draw user input from the GUI widgets into a single string, which can ten be sent to Arduino code. The following functions are created to draw the inputs. 

construct_data_string_left():..
'''

def construct_data_string_left(): 
    #  pulls data from buttons and formats into proper string, separated with '/'
    This function pulls data from the GUI widgets and formats into a single string, which can then be sent to
    Arduino code. This structure is mirrored in Button_Parameters.ino (to decode the string) for reference. The
    names for the strings pulled from widgets exactly match the variable names in the Arduino code
    (exo_teensy_menu___.09).
   
    global settsStrML
    global fsm_type
    global control_type

    fsm_type = str(main.p1.FSMOPTIONS.get())  # pulls data out of FSMOPTIONS entry widget
    control_type = str(main.p1.CONTROLLEROPTIONS.get())
    sendgains = main.p1.SENDGAINSONOFF.get()
    save_settings_oi_s = str(main.p1.SAVESETTINGS.get())  # str(main.p1.SAVESETTINGS.get()) # 0 is no, 1 is 
'''

construct_data_string_right():..

construct_test_param_string():..

construct_gains_string():..

construct_pot_string(leg):..


# Important Dependencies:
1. Lab Streaming Layer (LSL)
2. Python Libraries (time, tkinter, os, sys, pylsl, pyserial, subprocess, PyBluez)

After downloading the PRex-GUI folder, add a working copy of pylsl (from Lab Streaming Layer) and a folder containing a working copy of LabRecorder to the folder to make PRex-GUI.py run.

# Publications
If using this software, please cite "An Open Source Graphical User Interface for Wearable Robotic Technology." This work provides an overview of the software and recommendations for how to modify this software for your project. 
