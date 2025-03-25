import socket
import matplotlib.pyplot as plt
import numpy as np
import time
from scipy.interpolate import UnivariateSpline

# UDP connection parameters
UDP_IP = "192.168.4.2"  # This should match the ESP32 access point's IP
UDP_PORT = 12345

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# -- Figure 1: Pitch & Roll --
plt.ion()
fig1, (ax1, ax2) = plt.subplots(2, 1)

pitch_lines = []
roll_lines = []

# Initialize pitch and roll lines for each sensor
for i in range(4):
    pitch_line, = ax1.plot([], [], label=f"MPU#{i + 1}")
    roll_line,  = ax2.plot([], [], label=f"MPU#{i + 1}")
    pitch_lines.append(pitch_line)
    roll_lines.append(roll_line)

ax1.set_title("Pitch")
ax1.set_ylim(-90, 90)
ax1.set_ylabel("Angle (degrees)")
ax1.legend()

ax2.set_title("Roll")
ax2.set_ylim(-90, 90)
ax2.set_ylabel("Angle (degrees)")
ax2.legend()
ax2.set_xlabel("Time (seconds)")

# -- Figure 2: Spline Plot (Vertical) --
fig2 = plt.figure()
ax3 = fig2.add_subplot(111)


# Compute spline for the latest roll values across sensors
sensor_indices = np.array([1, 2, 3, 4])
roll_perfect = np.array([14, -10, -7.5, -2.5])
spline = UnivariateSpline(sensor_indices, roll_perfect, k=3)
spline.set_smoothing_factor(0.5)
spline_indices = np.linspace(1, 4, 100)
spline_values_perfect = spline(spline_indices)
ax3.plot(spline_values_perfect, spline_indices, color='gray', alpha = 0.6, label="Perfect Posture")


# We'll plot Roll on the x-axis, and the Sensor Index on the y-axis
spline_line, = ax3.plot([], [], 'g-', label="Roll Spline")

ax3.set_title("Roll Spline by Sensor Index (Vertical)")
ax3.set_xlim(-180, 180)   # Roll range on the horizontal axis
ax3.set_ylim(1, 4)      # Sensor Index on the vertical axis
ax3.set_xlabel("Roll (degrees)")
ax3.set_ylabel("Sensor Index")
ax3.set_yticks([1, 2, 3, 4])
ax3.legend()

time_window = 10  # seconds of data to display
num_points = 100  # number of points to plot within the time window
time_data = np.linspace(-time_window, 0, num_points)

# Initialize angle data arrays
pitch_data = [np.zeros(num_points) for _ in range(4)]
roll_data = [np.zeros(num_points) for _ in range(4)]

start_time = time.time()
last_print_time = time.time()  # For 20ms print timing


def calculate_pitch_roll(ax_val, ay_val, az_val):
    pitch = np.arctan2(ay_val, np.sqrt(ax_val**2 + az_val**2)) * (180 / np.pi)
    roll = np.arctan2(-ax_val, az_val) * (180 / np.pi)
    roll = -(roll+90)
    return pitch, roll


def calculate_pitch_roll_opposite(ax_val, ay_val, az_val):
    pitch = np.arctan2(ay_val, np.sqrt(ax_val**2 + az_val**2)) * (180 / np.pi)
    roll = np.arctan2(-ax_val, az_val) * (180 / np.pi)
    roll = (roll+90)
    return pitch, roll


while True:
    try:
        # Receive data from UDP socket
        data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
        data = data.decode("utf-8")
        accel_values = list(map(float, data.split(",")))

        # Calculate pitch and roll for each sensor
        for i in range(4):
            ax_val = accel_values[i * 3 + 0]
            ay_val = accel_values[i * 3 + 1]
            az_val = accel_values[i * 3 + 2]
            if (i < 2):
                pitch, roll = calculate_pitch_roll_opposite(
                    ax_val, ay_val, az_val)
            else:
                pitch, roll = calculate_pitch_roll(ax_val, ay_val, az_val)

            # Update the data arrays
            pitch_data[i] = np.roll(pitch_data[i], -1)
            roll_data[i] = np.roll(roll_data[i], -1)
            pitch_data[i][-1] = pitch
            roll_data[i][-1] = roll

        # Update the time window
        current_time = time.time() - start_time
        time_data = np.roll(time_data, -1)
        time_data[-1] = current_time

        # Update the plots for pitch and roll (Figure 1)
        for i in range(4):
            pitch_lines[i].set_xdata(time_data)
            pitch_lines[i].set_ydata(pitch_data[i])
            roll_lines[i].set_xdata(time_data)
            roll_lines[i].set_ydata(roll_data[i])

        # Compute spline for the latest roll values across sensors
        sensor_indices = np.array([1, 2, 3, 4])
        roll_current = [roll_data[i][-1] for i in range(4)]

        # Create a spline based on the roll data
        spline = UnivariateSpline(sensor_indices, roll_current, k=3)
        spline.set_smoothing_factor(0.5)
        spline_indices = np.linspace(1, 4, 100)
        spline_values = spline(spline_indices)
        
        mse = np.mean((spline_values-spline_values_perfect) ** 2)

        # For the vertical plot:
        #   x-axis: roll (spline_values)
        #   y-axis: sensor index (spline_indices)
        spline_line.set_xdata(spline_values)
        spline_line.set_ydata(spline_indices)
        
        if mse > 12:
            spline_line.set_color("red")
        else:
            spline_line.set_color("green")

        # Auto-rescale (Figure 1)
        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()

        # Auto-rescale (Figure 2)
        ax3.relim()
        ax3.autoscale_view()

        # Print roll values every 20ms
        now = time.time()
        if (now - last_print_time) >= 0.02:
            print(f"Roll values (every 20ms): {roll_current}")
            print(f"Mean Squared Error: {mse}")
            last_print_time = now

        plt.pause(0.005)

    except KeyboardInterrupt:
        print("Stopping...")
        break

sock.close()
