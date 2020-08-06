## Table of contents
* [Overview](#Overview)
* [System requirements](#system-requirements)
* [Software installation](#software-installation)
* [Functionalities of the script](#functionalities-of-the-script)
* [Step-by-step tutorial](#step-by-step-tutorial)
* [Publications](#publications)


# Overview
Open source code for the NIH PRex Exoskeleton Graphical User Interface (GUI). Includes shell AVR-C (Arduino) operating system, Python GUI, Unity plotting application, and an MIT App Inventor project (phone app for Android).

All software is protected under the GNU General Public License, version 3 (GPLv3), found in 'LICENSE.md'. 

# System requirements
1. 64-bit versions of Microsoft Windows 10, 8
2. 2 GB RAM minimum, 8 GB RAM recommended
3. 2.5 GB hard disk space, SSD recommended
4. 1024x768 minimum screen resolution
5. Python 3.5 or newer

# Software installation
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

## Block 1: setup communication
* This block is to set up the communication mode by either cable-based serial or bluetooth.
```
connect_to_exo(comType, address1, address2)
```

## Block 2: data entry functions
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
## Block 3: data receiving functions
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
## Block 4: Modular control panel (written in class)

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
## Block 5: Real-time data streaming

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
## Block 6: Real-time data visualization

* Unity interface is created to visualize all sensor data
```
plotting_subprocess = subprocess.Popen(os.path.normpath("./backend_plotting/Static Grip Device.exe"))
```

# Step-by-step tutorial
Before using the code in this repository on a project, it is helpful to understand how information flows in the code. First, let’s look at how data might travel from the graphical user interface (GUI) to an embedded microcontroller (i.e. a Teensy or Arduino).

Say the user wants to send a single numerical value to a Teensy microcontroller over Bluetooth. Let’s see how the software sends the proportional gain (labeled ‘P Gain’) for a PID controller to the microcontroller.


## 1. User Text Entry

Suppose the user needs a text entry widget to enter a value, and additional text identifying what the entry widget is for. Here’s an example of what that looks like in the GUI:

![Image of PGain Button + Text](images4rm/pgain.png)

In Python, a library called Tkinter is used to produce widgets like this for a GUI. For more information on the Tkinter library, see the Software Installation section for a link to further documentation. Here’s what the text entry widget looks like in Python code:

```
self.PGAIN = tk.Entry(self.uniconframe, width=8)
self.PGAIN.grid(row=0, column=1)
self.PGAIN.insert(END, "425")
```

The first line instantiates an ‘Entry’ class from the Tkinter library as ‘PGAIN.’ (Technically, PGAIN is a child class of the class TestingPage until TestingPage is instantiated, hence ‘self.PGAIN.’) The grid() command tells PGAIN where to appear on the page, and the insert() command inserts starting text in the box, in this case “425.” 

Additionally, here’s what the text label that says ‘P Gain:’ looks like in code:

```
pLabel = tk.Label(self.uniconframe, text="P Gain: ")
pLabel.grid(row=0, column=0)
```

The ‘Label’ class is instantiated as “pLabel” and is told where to appear by grid().


## 2. User Control to Send Text

Next, the user needs a way to tell the software to send the data (a P Gain of 425) to the microcontroller. This is accomplished with a button, in this case, the ‘Set Gains’ button:

![Image of Set Gains Button](images4rm/setgains.png)

Here’s what that looks like in code, again using the Tkinter library:

```
self.SETGAINS = Button(self.uniconframe, relief="groove", overrelief="raised")
self.SETGAINS["text"] = "Set Gains"
self.SETGAINS["fg"] = "blue"
self.SETGAINS["command"] = self.gains
self.SETGAINS.grid(row=0, column=2, sticky=W, padx=10)
```

Similar to before, the ‘Button’ class is instantiated as ‘SETGAINS’ as a child object of TestingPage(). The text in the button is set to “Set Gains,” the color is set to blue, and the button commands the function ‘gains.’ 


## 3. Function to Pull Text from Entry Widget and Send Text to Microcontroller

A nifty feature of the Tkinter library is that it can link buttons in the user interface to functions in the code. The “Set Gains” button in this example commands the gains() function. When the button is pressed by the user, the gains() function is called, executing some task. In this case, the gains() function (1) changes important states that execute universal control over the code, (2) sends a ‘g’ to tell the microcontroller to expect to receive values containing P, I, and D gains, (3) calls the function construct_gains_string(), and (4) calls send_data() again to actually send the P, I, and D gains.  

```
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
```


## 3a. Function to Encode Communication String

To really understand what the gains() function does, though, you need to understand the construct_gains_string() function it calls! In essence, it goes and look in the text entry widgets PGAIN, IGAIN, and DGAIN, uses .get() to acquire the values in those text entry widgets, and then squishes all of those values into a single string for transport. That string is called “settsStrG”, as seen in the return statement. 

```
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
```
… (more nested if logic)
```
return settsStrG
```


## 3b. Function to Send Data over Bluetooth

So now the user has entered a value for PGAIN, pressed a button to calls the gains() function, which in turn calls construct_gains_string() and organizes the P, I, and D gains into a single string. Now all that’s left is actually sending that data over to the microcontroller. That’s what the function send_data() (called in by the gains() function) does. It simply takes that string, encodes it using a utf-8 format, and either (1) writes it serially to a USB port or (2) uses a client/socket relationship to send the string over Bluetooth. 

```
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
```

And from there, the data is sent via a Bluetooth dongle to a receiving bluetooth modem wired to the microcontroller!

While this all might seem rather complicated at first, once you understand these fundamentals, you’ll begin to recognize patterns that you can efficiently adapt for your own project. 


# 4. Function to Receive Data from Bluetooth on the Microcontroller

Of course, for this data to be useful, the microcontroller needs an equally sophisticated way to breakdown the encoded information. Let’s look at one implementation of that in AVR-C (Arduino programming). 

In the main while loop of your Arduino code, you might have a function like this that looks for data from an input pin during every loop:

```
void update_settings() { // this function continuously checks for serial input or bluetooth input
  if (Serial.available()) {
    settsLen = Serial.readStringUntil(midMarker); // Python sends # of characters first (gets an int)
    settsLenI = settsLen.toInt();
    Serial.print("\nSettings Length: " + String(settsLenI) + "\n");
    settsStrM = Serial.readStringUntil(endMarker); //
    Serial.print("Settings String: " + settsStrM + "\n\n");
    parseSetts(settsLenI, settsStrM);
  }
  else if (BLE.available()) {
    settsLen = BLE.readStringUntil(midMarker);
    settsLenI = settsLen.toInt();
    settsStrM = BLE.readStringUntil(endMarker);
    parseSetts(settsLenI, settsStrM);
  }
}
```

When data is received, parseSetts() is called.


# 5. Function to Decode Communication String and Assign Values

Lastly, you need a function to decode that “squished” string of P, I, and D gains. In our implementation, we convert the string a character array, then tokenize the string using strtok(), which essentially picks the string apart using some delimiter. 

```
void parseSetts(int len, String str) { // parses settings string.
  char strInChar[len]; // make character array of settings of proper length. len might not be necessary
  str.toCharArray(strInChar, len + 1);
```
... (Nest if logic to direct the values to the proper variables for assignment, depending on what kind of information was sent.)

```
      kp_torq_s = strtok(NULL, delim);
      update_double_b(kp_torq_s, kp_torq);
      allprint("P Gain: " + kp_torq_s + "\n");
```

And at long last, kp_torq_s, or the 'P Gain' is assigned on the microcontroller. 

# Publications
If using this software, please cite "An Open Source Graphical User Interface for Wearable Robotic Technology." This work provides an overview of the software and recommendations for how to modify this software for your project. 
