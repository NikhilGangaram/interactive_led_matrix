import cv2
import torch
import numpy as np
import sys
import socket
import time
import traceback

from depth_anything_v2.dpt import DepthAnythingV2

# Specify the device to use ("cpu" or "mps" or "cuda")
DEVICE = "mps"

# Define the threshold to use for depths (percentage of closest depths to be considered "close")
# Used to determine which depth values become 255 in the intermediate binary map.
depth_threshold_percentage = 0.35

LED_IP = "192.168.86.122"
PORT = 8888

TARGET_HEIGHT = 32
TARGET_WIDTH = 32

# --- Model Setup ---
if not torch.backends.mps.is_available():
    print("Error: MPS is not available on this device.")
    if not torch.backends.mps.is_built():
        print("Error: The current PyTorch installation was not built with MPS enabled.")
    sys.exit(1)

model_configs = {
    'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
    'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
    'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
    'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
}

encoder = 'vits'
checkpoint_path = f'checkpoints/depth_anything_v2_{encoder}.pth'

try:
    model = DepthAnythingV2(**model_configs[encoder])
    model.load_state_dict(torch.load(checkpoint_path, map_location=DEVICE))
    model = model.to(DEVICE).eval()
except FileNotFoundError:
    print(f"Error: Checkpoint file not found at {checkpoint_path}")
    sys.exit(1)
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)
# --- End Model Setup ---


def create_depth_map(frame):
    """Generates a depth map from a given frame."""
    with torch.no_grad():
        depth = model.infer_image(frame)
    return depth

def convert_to_binary(depth_map, threshold_percentage):
    """
    Converts a depth map to an inverted binary map based on a threshold percentage.
    Pixels with depth > percentile threshold become 255, others become 0.
    """
    flattened_depth = depth_map.flatten()
    if len(flattened_depth) == 0:
        print("Warning: Empty depth map received in convert_to_binary.")
        return np.zeros_like(depth_map, dtype=np.uint8)

    threshold_index = int(threshold_percentage * len(flattened_depth))
    threshold_index = min(max(0, threshold_index), len(flattened_depth) - 1)
    threshold_depth = np.partition(flattened_depth, threshold_index)[threshold_index]

    binary_depth_map = np.zeros_like(depth_map, dtype=np.uint8)
    binary_depth_map[depth_map > threshold_depth] = 255
    binary_depth_map[depth_map <= threshold_depth] = 0

    return binary_depth_map

def scale_binary_matrix_threshold_kernel(matrix, target_height, target_width, on_threshold_255_percentage):
    """
    Scales a binary matrix to a target size using a threshold kernel approach.
    Outputs 255 if the percentage of 255s in the corresponding block >= threshold.
    """
    original_height, original_width = matrix.shape
    scaled_matrix = np.zeros((target_height, target_width), dtype=np.uint8)

    height_ratio = original_height / target_height
    width_ratio = original_width / target_width

    for y in range(target_height):
        for x in range(target_width):
            start_y = int(y * height_ratio)
            end_y = int((y + 1) * height_ratio)
            start_x = int(x * width_ratio)
            end_x = int((x + 1) * width_ratio)

            block = matrix[start_y:end_y, start_x:end_x]

            if block.size > 0:
                count_of_255s = np.sum(block == 255)
                block_size = block.size
                percentage_of_255s = count_of_255s / block_size

                if percentage_of_255s >= on_threshold_255_percentage:
                     scaled_matrix[y, x] = 255
                else:
                     scaled_matrix[y, x] = 0
            else:
                scaled_matrix[y, x] = 0

    return scaled_matrix

def send_over_wifi(binary_matrix, LED_IP, port):
    """Sends a binary matrix over Wi-Fi."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect((LED_IP, port))
            rows, cols = binary_matrix.shape
            s.sendall(rows.to_bytes(4, 'little'))
            s.sendall(cols.to_bytes(4, 'little'))
            for row in binary_matrix:
                for element in row:
                    s.sendall(int(element).to_bytes(4, 'little'))
            return True

    except (ConnectionRefusedError, socket.timeout, socket.gaierror):
        return False
    except Exception as e:
        print(f"An unexpected error occurred during sending: {e}")
        return False

def main():
    """Captures webcam feed, processes, and sends binary matrix over Wi-Fi."""
    cap = None

    # Threshold for turning ON LEDs (percentage of 255s required in the source block)
    # A higher value biases towards fewer ON LEDs.
    ON_THRESHOLD = 0.75

    try:
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Could not open webcam.")
            sys.exit(1) # Exit immediately if no webcam

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Error: Could not read frame. Exiting.")
                break

            depth_map = create_depth_map(frame)

            # Convert to binary: 255 for farthest 35%, 0 for closest 65%
            binary_depth_map = convert_to_binary(depth_map, (1-depth_threshold_percentage))

            # Scale to 32x32 using ON_THRESHOLD to determine ON/OFF pixels
            scaled_binary_map = scale_binary_matrix_threshold_kernel(
                binary_depth_map,
                TARGET_HEIGHT,
                TARGET_WIDTH,
                on_threshold_255_percentage=ON_THRESHOLD
            )

            # Rotate 90 degrees clockwise (since I messed up assembling the LEDs :) )
            rotated_binary_map = np.rot90(scaled_binary_map, k=-1)

            send_over_wifi(rotated_binary_map, LED_IP, PORT)

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Webcam released and windows closed.")

if __name__ == "__main__":
    main()