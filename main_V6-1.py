import serial
from tkinter import *
import tkinter as tk
import tkinter.messagebox
import numpy as np
import time

# Important: Change comport to what the motor is connected to. Depends on running mac or windows. 
# Windows will be COM3 etc. Can find this by checking device manager and under 'Ports (COM & LPT) find the motor and which COM port its connected to.
commPort = '/dev/tty.usbserial-110'

# Define parameters for the motor serial comm here to communicate.
# CHECK: Play with timeout, if we need high speed communication with motor. delay may be changed. Should parity be None or true?
ser = None


# Define initial_velocity, time_step (eg. 1000 / 1 sec), and interval to increase
time_step = 1000
speed_increase_interval = 0
initial_value = 0
motor_speed = 0  # tracks motor speed at all times

# var to see timer done
peaked = True

# Global unitstep duration
max_duration = 0
duration_begin = 0

# Sine input params. Change to 100 later

# amplitude = 1 # multiply sine y by amplitude 
# period = 2 * np.pi  # amount of time to go through an oscilation . some number (2 pi / period) multiplied by x

curr_speed = initial_value
# Todo: get currvalue to start from the initial value? and 
# todo: initialvelocity doesnt rly do anything yet... besides display the number and have ui
# todo: important!: Ramp up starts velocity from 0, and not the initial velocity
# if the button is pressed, ramps up starting from . start bool, create true hwen button pressed, set the speed to something in

# idk what it should do.. MAYBE: have initialvalue set to getinitialvalue in a separate function and run at initial
# value for 10 seconds, then  ramp up?
ramp_again = None
sine_again = None

def connectToCOMPort():
    global ser
    commPort = box_COM.get() # Get comm port from UI
    try:
        ser = serial.Serial(port=commPort, baudrate=38400, bytesize=serial.EIGHTBITS, timeout=None,
                            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        print("Connected!")
        label_COM_connection.config(text="Connected!")
    except:
        print("Failed to connect to COMPort. Restart the application to try again")
        label_COM_connection.config(text="Failed to connect to COMPort. Try a different input")


# Prep for rampup (sets inital value)
def rampUpMotorPrep():
    global curr_speed
    global initial_value

    global duration_begin  # unnecessary tbh, cuz its done in unit step
    global max_duration  # unnecessary tbh, cuz its done in unit step

    # Ramps up for 10 seconds (not based on actual speed)
    init_rampup_speed = getInitialRampUpValue()
    rampup_max_speed = getFinalRampUpValue()  # Gets final value of rampup
    curr_speed = init_rampup_speed
    initial_value = getInitialRampUpValue()

    unitStep(init_rampup_speed)  # Starts unit step and ALSO STARTS TIMER

    # Ramps up motor after 10 seconds
    root.after(10000, rampUpMotor, rampup_max_speed)


def rampUpMotor(max_speed=None):
    global curr_speed
    global ramp_again
    global speed_increase_interval
    # calculate speed increase interval
    init_rampup_speed = getInitialRampUpValue()
    rampup_max_speed = getFinalRampUpValue()  # Gets final value of rampup
    ramp_duration = getRampUpDurationValue() * 1000
    if ramp_duration == 0:
        ramp_duration = 1
    speed_increase_interval = 1000 * (rampup_max_speed - init_rampup_speed) / ramp_duration
    # Try serial communication.
    # Uncomment when need to try.
    bytes_curr_speed = bytes(str(curr_speed * 10), 'utf-8')

    clockwise = cw_var.get()  # Check if clockwise setting True or not.
    if (clockwise):
        print("Ramping Now")
        ser.write(b'@0D\r@0S\r@0+\r@0M' + bytes_curr_speed + b'\r')
    else:
        print("Ramping Now")
        ser.write(b'@0D\r@0S\r@0-\r@0M' + bytes_curr_speed + b'\r')

    if rampup_max_speed - init_rampup_speed > 0:
        # print("Speed is at", curr_speed, "RPM starting from ", initial_value, "RPM")
        # Update speed for next iteration
        if curr_speed < max_speed:
            curr_speed = int(speed_increase_interval + curr_speed)
    elif curr_speed > max_speed:
        curr_speed = int(curr_speed + speed_increase_interval)
    else:
        curr_speed = max_speed  # Redundant, but dont want to fix. Ideally return function, and STOP ramp_again,
        # because it's just a unit step after that.

    # Ramp up motor again after x seconds (time_step )
    ramp_again = root.after(time_step, rampUpMotor, max_speed)


# Methods to send serial data to motor.
# Prefaced with a 'b' to signify byte of data, may replace for motor.
# Constant RPM function
def unitStep(init_speed=0):
    global max_duration
    global duration_begin
    global peaked

    if (
            init_speed > 0):  # If user defined a speed in RAMPUP and called Ramp up motor function, use that for constant rpm.
        initial_value = init_speed
    else:  # Else, use standard constant rpm function.
        initial_value = getInitialValue()

    duration = getDurationValue()  # Get duration specified by user in UI
    if (duration > 0):
        max_duration = duration  # set global duration variable for unitstep if param is not none.
        duration_begin = time.time()  # gets the time NOW (to calculate end time - beginning time later)
        peaked = False  # Sets peaked to false

    bytes_rpm = bytes(str(initial_value * 10), 'utf-8')

    clockwise = cw_var.get()  # Check if clockwise setting True or not.
    if (clockwise):
        ser.write(b'@0D\r@0S\r@0\r@0+\r@0M' + bytes_rpm + b'\r')
    else:
        ser.write(b'@0D\r@0S\r@0\r@0-\r@0M' + bytes_rpm + b'\r')

    print("Started")
    # print("Constant RPM set to at: ", initial_value)
    # print("Clockwise? : ", clockwise)


# Prints motor speed to terminal (with blocking. try remove) doesnt work idk y
def checkMotorSpeed():
    global motor_speed  # wasnt here, maybe delete
    if ser is None:
        return
    ser.write(b'@0VM\r')  # Request rpm
    if (ser.inWaiting() > 0):
        motor_speed = ser.read(ser.inWaiting()).decode('ascii')
        motor_speed = motor_speed[1:]
        motor_speed = int(motor_speed)
        print(motor_speed / 10, end='\n')
        mSpeed = 'Motor RPM\n' + str(motor_speed / 10)
        label_motor_speed.config(text=mSpeed)


# Routine checks for motor speed, and unitstep/rampup function durations EVERY 5 SECONDS
def routineCheck():
    global peaked
    global duration_begin
    global max_duration

    checkMotorSpeed()  # checks motor speed

    if peaked == True:
        root.after(500, routineCheck)
        return
    currTime = time.time()
    time_passed = currTime - duration_begin
    print("Time passed from timer start: ", time_passed)

    print("This is how much time you set for max duration")
    print(max_duration)

    # While peaked is false (functions running), check motor


    # Assumes peaked is false, and only turnso ff motor once until turned on by peak again
    if (time_passed >= max_duration):
        turnOffMotor()
        peaked = True

    root.after(500, routineCheck)


def turnOffMotor():
    ser.write(b'@0,\r')
    # Reset curr_speed var to 0
    curr_speed = 0
    print("Turned off")
    # Attempt close recursive ramping functions if not None
    if ramp_again:
        root.after_cancel(ramp_again)


# Close GUI code
def ask_quit():
    if tkinter.messagebox.askokcancel("Quit", "Quit the application?"):
        # Close serial connection on quit.
        if ser != None:
            ser.close()
        root.destroy()


# Returns initial value
def getInitialValue():
    initValue = 0
    try:
        initValue = int(box_initial_value.get())
        reportLabel.config(text="")
    except ValueError:
        reportLabel.config(text="Warning: the Constant RPM field might not contain an integer")

    return initValue


# Returns initial value
def getInitialRampUpValue():
    initValue = 0
    try:
        initValue = int(box_rampup_initial_value.get())
        reportLabel.config(text="")
    except ValueError:
        reportLabel.config(text="Warning: the Initial Ramp RPM field might not contain an integer")

    return initValue


def getFinalRampUpValue():
    finalValue = 0
    try:
        finalValue = int(box_rampup_final_value.get())
        reportLabel.config(text="")
    except ValueError:
        reportLabel.config(text="Warning: the Final Ramp RPM field might not contain an integer")

    return finalValue


def getDurationValue():
    durValue = 0
    try:
        durValue = int(box_duration.get())
        reportLabel.config(text="")
    except ValueError:
        reportLabel.config(text="Warning: the Constant RPM Duration field might not contain an integer")

    return durValue


def getRampUpDurationValue():
    durValue = 0
    try:
        durValue = int(box_ramp_duration.get())
        reportLabel.config(text="")
    except ValueError:
        reportLabel.config(text="Warning: the Ramping Duration  field might not contain an integer")

    return durValue


# Remove later. For testing CW
def test_cw():
    if cw_var.get() == True:
        print("It's clockwise")
    else:
        print("It's counterclockwise")
    print(cw_var.get())


# GUI code (tkinter): Create the window
root = Tk()
root.title("Motor GUI")

label_title = Label(root, text="Motor Control UI", font=('Helvetica', 14, 'bold'))
label_title.grid(row=0, column=2)

# Create widgets, and place it within window using grid.
btn_On = tk.Button(root, text="Start motor at UnitStep", command=unitStep)
btn_On.grid(row=10, column=1, padx=10, pady=10)

btn_Off = tk.Button(root, text="Turn Off Motor", command=turnOffMotor)
btn_Off.grid(row=11, column=2, padx=15, pady=30)

# Rampup
btn_rampUp = tk.Button(root, text="Ramp up motor", command=rampUpMotorPrep)
btn_rampUp.grid(row=10, column=2)

# Sine function (Hidden for future use)
# btn_sine = tk.Button(root, text="Sine", command=lambda: sine_setup(2*np.pi, 500, 1000))
# btn_sine.grid(row=6, column=1)

# Labels unit step and Ramp
label_unit_step = Label(root, text="Unit Step", font=('Helvetica', 11, 'bold'))
label_unit_step.grid(row=1, column=1, padx=10, pady=10)

# CW/CCW Radio buttons
cw_var = IntVar()
cw_radio = Radiobutton(root, text="Clockwise", variable=cw_var, value=True, activebackground='grey', command=test_cw)
cw_radio.grid(row=9, column=1, padx=10, pady=10)

ccw_radio = Radiobutton(root, text="Counter-clockwise", variable=cw_var, value=False, activebackground='grey',
                        command=test_cw)
ccw_radio.grid(row=9, column=2, padx=10, pady=10)

label_ramp = Label(root, text="Ramp", font=('Helvetica', 11, 'bold'))
label_ramp.grid(row=1, column=2, padx=10, pady=10)

# TODO: Create UI to input variables speed_interval update and initial_value
label_initial_value = Label(root, text="Enter a constant RPM")
label_initial_value.grid(row=2, column=1, padx=10, pady=10)

label_duration = Label(root, text="Constant RPM Duration: (leave empty for none)")
label_duration.grid(row=5, column=1, padx=10, pady=10)

box_duration = Entry(root)
box_duration.grid(row=6, column=1, padx=10, pady=10)

box_initial_value = Entry(root)
box_initial_value.grid(row=3, column=1, padx=10, pady=10)

# Initial value for Rampup speed
label_rampup_initial_value = Label(root, text="Initial Ramp up RPM")
label_rampup_initial_value.grid(row=2, column=2, padx=10, pady=10)

box_rampup_initial_value = Entry(root)
box_rampup_initial_value.grid(row=3, column=2, padx=10, pady=10)

# box for ramp up duration
label_ramp_duration = Label(root, text="Ramping Period: (default ramp rate is 1 RPM/s)")
label_ramp_duration.grid(row=5, column=5, padx=10, pady=10)

box_ramp_duration = Entry(root)
box_ramp_duration.grid(row=6, column=5, padx=10, pady=10)

#COMPort Box
label_COM = Label(root, text="COM Port:")
label_COM.grid(row=49, column=5, padx=10, pady=10)

box_COM = Entry(root)
box_COM.grid(row=50, column=5, padx=20, pady=10)

btn_COM = tk.Button(root, text="Connect", command=connectToCOMPort)
btn_COM.grid(row=51, column=5)

label_COM_connection = Label(root, text="")
label_COM_connection.grid(row=52, column=5, padx=10, pady=10)
# Final value for Rampup speed
label_rampup_final_value = Label(root, text="Final Ramp up RPM")
label_rampup_final_value.grid(row=4, column=2, padx=10, pady=10)

box_rampup_final_value = Entry(root)
box_rampup_final_value.grid(row=5, column=2, padx=10, pady=10)

# Motor Speed box on GUI
label_motor_speed = Label(root, text="Motor RPM")
label_motor_speed.grid(row=50, column=2, padx=10, pady=10)

reportLabel = Label(root, text="")
reportLabel.grid(row=15, column=2)

root.geometry("1000x1000")
root.protocol("WM_DELETE_WINDOW", ask_quit)
# Checks motor speed here and updates
routineCheck()

root.mainloop()

# Called only after window dies.
if (ser):
    ser.close()
