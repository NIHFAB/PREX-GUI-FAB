# PRex-Interface
Open source code for the NIH PRex Exoskeleton Graphical User Interface (GUI). Includes shell AVR-C (Arduino) operating system, Python GUI, Unity plotting application, and an MIT App Inventor project (phone app for Android).

All software is protected under the GNU General Public License, version 3 (GPLv3), found in 'LICENSE.md'. 

# Step 1. data entry functions

The first step is to draw user input from the GUI widgets into a single string, which can ten be sent to Arduino code. The following functions are created to draw the inputs. 

construct_data_string_left():..

'''
def construct_data_string_left():  # pulls data from buttons and formats into proper string, separated with '/'
    """ This function pulls data from the GUI widgets and formats into a single string, which can then be sent to
    Arduino code. This structure is mirrored in Button_Parameters.ino (to decode the string) for reference. The
    names for the strings pulled from widgets exactly match the variable names in the Arduino code
    (exo_teensy_menu___.09).
    """
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
