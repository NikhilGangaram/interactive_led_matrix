# Real-time Depth-Based LED Control

Welcome! This project lets you use your computer's webcam to figure out what's far away in front of your camera. It then sends this information as a pattern over your home network to control a network-connected LED matrix, making LEDs light up based on the distance of objects!

The project consists of two main Python scripts:
1.  A script that runs on your main computer (laptop/desktop) with a webcam. It captures video, calculates depth, processes the data, and sends it over your network.
2.  A script that runs on a Raspberry Pi connected to an LED matrix. It listens for data from the main computer and displays the pattern on the LEDs.

## What You'll Need

Before you get started, please make sure you have these things ready:

1.  **A Computer:** A desktop or laptop. This is where the depth calculation happens. For the best performance (so things happen smoothly and in real-time), your computer should ideally have a graphics card or special chip that supports either **Apple's MPS** (for newer Macs with Apple Silicon) or **NVIDIA CUDA** (for PCs with compatible NVIDIA graphics cards). Running on just the main processor (CPU) is possible but will be much slower.
2.  **A Webcam:** Any working webcam connected to your computer will do.
    * **Cool Tip for Mac users:** If you have an iPhone and a Mac, you can often use your iPhone as a high-quality wireless webcam thanks to a feature called Continuity Camera! If you're using the 3D printed enclosure designed for this project, there's even a spot perfectly sized for an iPhone – a happy little accident!
3.  **A Raspberry Pi with an LED Matrix:** A Raspberry Pi computer connected to an LED matrix that is compatible with the `rpi-rgb-led-matrix` library (often referred to as `rgbmatrix`).
4.  **Network Connection:** Both your main computer (running the depth script) and the Raspberry Pi (controlling the LEDs) need to be connected to the same home network (Wi-Fi or Ethernet). The panel used in the original project and that the 3D printed enclosure was designed for is the Adafruit RGB Matrix (32x32). 
5.  **Conda:** A tool called Conda (either Anaconda or Miniconda) installed on your main computer. It helps manage different software setups for different projects without them interfering with each other.

## Getting Started: Setup on Your Main Computer (Depth Sender)

Let's get the depth-sensing part set up on your main computer first.

### 1. Get the Project Code

First, you need to get a copy of all the project files onto your computer. If this project is hosted on GitHub, you can "clone" the repository using a Git program, or you can usually find a way to download all the files as a Zip archive. Place the downloaded or cloned files in a folder on your computer.

When you get the code, you should find the main script (`main.py`) and a folder named `depth_anything_v2` which contains the necessary parts of the AI model code.

### 2. Create a Dedicated Space (Conda Environment)

It's best practice to set up a dedicated environment for this project. This keeps all the specific software needed here separate from other projects on your computer.

Using your Conda installation, create a new virtual environment. You should give it a specific name, like `interactive_led`, so you can easily find it later. Choose a relatively recent version of Python (e.g., Python 3.9 or 3.10) for this environment.

After the environment is created, you need to "activate" it using your Conda tools. This tells your computer to use the Python and libraries from this specific environment whenever you're working on this project. You'll need to activate it every time you open a new terminal or command prompt to work on the project.

### 3. Install the Necessary Software

Now that your `interactive_led` environment is active, you need to install the specific Python software libraries this project uses.

Inside your activated environment, use the `pip` tool (which comes with your Conda environment) to install the required packages. The main ones are:

* `torch`, `torchvision`, `torchaudio`: These are for the deep learning model (PyTorch).
* `numpy`: For handling numbers and data efficiently.
* `opencv-python`: For working with your webcam and images.

**Installing PyTorch (`torch`, `torchvision`, `torchaudio`) is special!** The exact process depends on whether your computer has MPS, CUDA, or only CPU. Please visit the official PyTorch website's installation guide ([https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/)) and follow their instructions to get the correct installation for your system and desired hardware acceleration.

Once you have PyTorch installed correctly for your hardware, install the other packages (`numpy`, `opencv-python`) using your pip tool within the same activated `interactive_led` environment.

## Getting Started: Setup on Your Raspberry Pi (LED Receiver)

This script runs on your Raspberry Pi, listens for data from your main computer, and displays it on the LED matrix.

### 1. Install the LED Matrix Library

This is often the trickiest part. You need to install the `rpi-rgb-led-matrix` library and its Python bindings on your Raspberry Pi. **Please follow the detailed installation instructions provided by the library's creators:** [https://github.com/hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix). Ensure you complete the steps for building and installing the library, and specifically the Python bindings so your script can import necessary components like `SampleBase`.

### 2. Install Python Dependencies

The receiver script itself has fewer Python dependencies than the sender. In the Python environment on your Raspberry Pi that you'll use to run the script, you need the `numpy` library. You can install this using the `pip` tool available in your Pi's terminal.

### 3. Get the Receiver Script

Copy the concise Python script for the LED receiver (the one designed to run on the Pi) onto your Raspberry Pi. Place it in a convenient folder.

## Connecting and Running the System

Now that both sides are set up, let's connect them and run the show!

### 1. Find Your Raspberry Pi's IP Address

The script on your main computer needs to know *where* to send the data on your network. It needs the IP address of your Raspberry Pi.

A common way to find this is from your main computer. If your Raspberry Pi has the default hostname, open a terminal or command prompt on your *main computer* and try sending a network test request (often called 'pinging') using its local network name. On many systems, this name is `raspberrypi.local`. You'll perform this action using your operating system's command line tools. Look at the output you receive; it should show the IP address that the name `raspberrypi.local` corresponds to (it will look something like `192.168.1.100`).

If `raspberrypi.local` doesn't work (sometimes network setups prevent this), you might need to log into your home router's settings page and look for a list of connected devices to find the Raspberry Pi's IP address, or use a network scanning application on your computer or phone.

### 2. Configure the Sender Script (on your Main Computer)

Go back to your *main computer* and open the `main.py` script in your text editor again.

Find the line that says `LED_IP = "..."`. Change the IP address written inside the quotes (`"..."`) to the exact IP address you just found for your Raspberry Pi in the previous step.

Save the `main.py` file.

### 3. Run the Receiver Script (on your Raspberry Pi)

Now, go to your *Raspberry Pi*. Open a terminal and navigate to the folder where you saved the receiver script (you might have named it `pi_receiver.py`).

The LED matrix library often requires the script to be run with root privileges to directly control the hardware. This usually involves using a command like `sudo` before the python command. You also need to tell the script the dimensions of your specific LED matrix panel (how many rows and columns it has) by providing arguments when you run the script, following the format required by the library's `SampleBase` class.

Run the script in the terminal on your Pi using the appropriate command for your setup, ensuring you use `sudo` and provide the correct matrix dimensions as arguments. The script should start and print a message indicating it's listening for connections. The LED matrix will likely remain blank or black until it receives data from your main computer.

### 4. Run the Sender Script (on your Main Computer)

Finally, go back to your *main computer*. Open a terminal or command prompt, activate your `interactive_led` conda environment, and navigate to the folder where you saved `main.py`.

Run the sender script using your Python interpreter within the activated environment.

The script should start, try to open your webcam feed, begin processing the depth information in real-time, and attempt to send the resulting data pattern over your network to the Raspberry Pi's IP address you configured. If everything is set up correctly and both scripts are running, you should see the LED matrix on the Raspberry Pi start displaying patterns based on the depth detected by your webcam!

To stop either script, go to the terminal window where it's running and typically press the `Ctrl` key and the `C` key at the same time (`Ctrl+C`). It's usually best to stop the sender script on the laptop first, then the receiver script on the Pi.

## How it Works (A Simple Explanation)

Think of the system working like this for each picture it gets from the webcam:

1.  **See the Depths (on your main computer):** The AI model looks at the camera picture and guesses how far away everything is, creating a "depth map" where different shades mean different distances.
2.  **Pick the Farthest Stuff (on your main computer):** It looks at this depth map and finds the objects that are farthest away. The `depth_threshold_percentage` helps decide what counts as "farthest" (e.g., the farthest 35% of things). These "farther" spots are marked in a simple black-and-white map (where white means farther).
3.  **Shrink and Decide (for LEDs - on your main computer):** It then shrinks this black-and-white map down to the size of your LED matrix (32x32 pixels). For each LED pixel in the final grid, it looks at the bigger area it came from in the black-and-white map. The `ON_THRESHOLD` is used here: if a large enough percentage (like 75% if `ON_THRESHOLD` is 0.75) of that area in the black-and-white map was marked as "farther" (white), then the LED lights up (is turned ON). Otherwise, it stays OFF. This helps make sure an LED only turns on if a significant part of the picture in that area is far away.
4.  **Adjust Orientation (on your main computer):** The resulting 32x32 pattern is rotated to match how your LED matrix is physically set up (the rotation happens in the sender script before sending).
5.  **Send the Pattern (from your main computer to the Pi):** Finally, this 32x32 ON/OFF pattern is sent over your network using a TCP socket connection to the IP address and port you specified for the Raspberry Pi.
6.  **Receive and Display (on your Raspberry Pi):** The receiver script on the Raspberry Pi is listening on that IP and port. When it gets the data, it reads the pattern and tells the connected LED matrix to illuminate the corresponding LEDs according to the ON/OFF pattern it received.

## If Something Goes Wrong: Troubleshooting

Here are a few common issues and things to check:

* **"Error: Could not import SampleBase." (on Pi)**: This means the `rpi-rgb-led-matrix` Python library is not installed correctly or cannot be found by the Python environment you are using on your Raspberry Pi. Go back to step 1 of the Raspberry Pi setup and carefully follow the library's installation instructions, paying close attention to the Python bindings part.
* **"Error: Could not open webcam." (on main computer)**: Make sure your webcam is plugged in correctly and working. If you have more than one camera, your computer might be trying to use the wrong one (usually index 0). You might need to change the number inside the `cv2.VideoCapture()` part in `main.py` to `1` or another number to find the right camera. Also, make sure no other program is currently using the webcam.
* **"Error: Checkpoint file not found..." (on main computer)**: This means the script couldn't find the AI model brain file (`depth_anything_v2_vits.pth`). Check that you downloaded the correct file and that you put it exactly in the `checkpoints` subfolder, which should be directly inside your main project folder. Make sure the file name is spelled correctly!
* **"Error loading model..." (on main computer)**: This could happen if the model file was downloaded incorrectly or if the PyTorch software you installed doesn't match the `DEVICE` you set in `main.py`. Double-check step 3 and step 5 of the main computer setup and ensure your PyTorch installation is correct for your hardware (MPS, CUDA, or CPU).
* **LEDs don't light up or don't change / Connection errors in terminal**:
    * Is your LED matrix server script on the Raspberry Pi definitely running? Check the terminal on the Pi for error messages.
    * Is the `LED_IP` address you put in the `main.py` script on your main computer exactly right for the Raspberry Pi's current IP address on your network? IP addresses can sometimes change if your router assigns them automatically. Double-check the IP address (step 1 of Connecting and Running) and update `main.py` if needed.
    * Is the `PORT` number in `main.py` the same as the port the receiver script on the Pi is listening on (default 8888)?
    * Are both computers connected to the same network (Wi-Fi or Ethernet)?
    * Could a firewall on either computer or your router be blocking the connection on that port?
    * Did you run the script on the Raspberry Pi with the necessary permissions (like using `sudo`) and provide the correct matrix dimensions as arguments?
* **Everything is very slow and laggy (on main computer)**: If the webcam feed processing is very slow or the script consumes excessive CPU on your main computer, it's likely running in CPU-only mode (`DEVICE = "cpu"`). For satisfactory real-time performance with deep learning models like this, hardware acceleration (MPS on Apple Silicon or CUDA on NVIDIA GPUs) and the correct PyTorch installation are essential. Ensure your hardware supports one of these backends and you have installed PyTorch accordingly, and that the `DEVICE` variable is set correctly in `main.py`.
