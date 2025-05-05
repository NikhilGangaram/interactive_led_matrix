#!/usr/bin/env python
import time
import sys
import socket
import struct
import numpy as np
import traceback

# Import the SampleBase class required for interacting with the LED matrix library
try:
    from samplebase import SampleBase
except ImportError:
    # Provide clear instructions if the library isn't found
    print("Error: Could not import SampleBase.")
    print("Please ensure the rgbmatrix library is installed correctly and in your PYTHONPATH.")
    sys.exit(1)

# --- Network Configuration ---
# Listen on all available network interfaces (makes it accessible from sender via Pi's IP)
LISTEN_HOST = "0.0.0.0"
# The port number to listen on, must match the sender script
LISTEN_PORT = 8888
# The expected dimensions of the binary matrix data sent from the sender
EXPECTED_ROWS = 32
EXPECTED_COLS = 32

# --- LED Color Mapping ---
# Define RGB colors for the ON (255) and OFF (0) states received from the sender
ON_COLOR = (255, 255, 255) # White light for 'ON' pixels
OFF_COLOR = (0, 0, 0)      # Black/off for 'OFF' pixels


class SocketLEDReceiver(SampleBase):
    def __init__(self, *args, **kwargs):
        super(SocketLEDReceiver, self).__init__(*args, **kwargs)
        # Matrix to store the current frame's pixel data to be displayed
        self.display_matrix = np.full((EXPECTED_ROWS, EXPECTED_COLS), 0, dtype=np.uint8)
        self.server_socket = None
        self.socket_listening = False

    def setup_socket(self):
        """Sets up the server socket to listen for incoming connections."""
        try:
            # Create a TCP/IP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reusing the address quickly after the script exits (useful for quick restarts)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set a timeout for accepting connections. This prevents accept() from blocking forever,
            # allowing the main loop to continue and refresh the display even without new data.
            self.server_socket.settimeout(1.0)
            # Bind the socket to the configured host and port
            self.server_socket.bind((LISTEN_HOST, LISTEN_PORT))
            # Enable the server to accept connections (1 pending connection queue size)
            self.server_socket.listen(1)
            self.socket_listening = True
            print(f"Listening for connections on {LISTEN_HOST}:{LISTEN_PORT}...")
        except socket.error as e:
            print(f"Failed to set up socket: {e}")
            self.socket_listening = False
        except Exception as e:
            print(f"An unexpected error occurred during socket setup: {e}")
            self.socket_listening = False

    def receive_matrix_data(self, conn):
        """Receives matrix dimensions and pixel data from the connected sender."""
        try:
            # Set a timeout for receiving data on the established connection
            conn.settimeout(5.0)

            # --- Receive Dimensions ---
            # Expected 8 bytes (4 for rows, 4 for cols, little-endian integers)
            dim_bytes = b''
            while len(dim_bytes) < 8:
                packet = conn.recv(8 - len(dim_bytes))
                if not packet: # Connection closed by sender
                    print("Connection closed by sender while receiving dimensions.")
                    return None
                dim_bytes += packet

            # Unpack the 8 bytes into two little-endian integers (rows, cols)
            rows, cols = struct.unpack('<ii', dim_bytes)

            # Validate received dimensions against expected dimensions
            if rows != EXPECTED_ROWS or cols != EXPECTED_COLS:
                print(f"Received unexpected dimensions: {rows}x{cols}. Expected {EXPECTED_COLS}x{EXPECTED_ROWS}. Attempting to drain buffer.")
                # Try to quickly read and discard remaining data for this incorrect frame
                try: conn.settimeout(0.1); while True: drained_data = conn.recv(1024); if not drained_data: break
                except: pass
                return None

            # --- Receive Pixel Data ---
            # Expected total bytes: rows * cols * 4 (since each pixel is sent as a 4-byte integer)
            total_bytes_to_receive = rows * cols * 4
            received_bytes = 0
            pixel_data_bytes = b''

            # Loop to ensure all expected pixel bytes are received
            while received_bytes < total_bytes_to_receive:
                chunk = conn.recv(total_bytes_to_receive - received_bytes)
                if not chunk: # Connection closed by sender prematurely
                    print(f"Connection closed by sender before receiving all pixel data ({received_bytes}/{total_bytes_to_receive} bytes received).")
                    return None
                pixel_data_bytes += chunk
                received_bytes += len(chunk)

            # Final check on received byte count (redundant but safe)
            if received_bytes != total_bytes_to_receive:
                print(f"Warning: Received incorrect total bytes ({received_bytes} vs {total_bytes_to_receive}). Data may be corrupted.")
                return None

            # --- Process Received Data ---
            try:
                # Convert received bytes buffer into a numpy array of 32-bit integers, then to 8-bit unsigned integers (0 or 255)
                flattened_data = np.frombuffer(pixel_data_bytes, dtype=np.int32).astype(np.uint8)
                # Reshape the 1D array into the expected 2D matrix format
                received_matrix = flattened_data.reshape((rows, cols))
                return received_matrix
            except Exception as e:
                print(f"Error processing received pixel data: {e}")
                traceback.print_exc()
                return None

        except socket.timeout:
            # This specific timeout happens if data stops arriving on an *established* connection
            return None
        except socket.error as e:
            print(f"Socket error during receive: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during receive: {e}")
            traceback.print_exc()
            return None

    def update_display(self, canvas, matrix_data):
        """Updates the LED matrix canvas based on the received matrix data (0 or 255 values)."""
        # Basic shape validation before drawing
        if matrix_data.shape[0] != EXPECTED_ROWS or matrix_data.shape[1] != EXPECTED_COLS:
            print(f"Cannot update display: Matrix data has incorrect shape {matrix_data.shape}.")
            return

        canvas.Clear() # Clear the entire canvas (sets all pixels to black/OFF)

        # Iterate through the received matrix and set pixel colors on the canvas
        for y in range(EXPECTED_ROWS):
            for x in range(EXPECTED_COLS):
                # If the value at this position is 255, set the pixel to the ON_COLOR
                if matrix_data[y, x] == 255:
                    canvas.SetPixel(x, y, *ON_COLOR)
                # Pixels with value 0 are already OFF due to canvas.Clear()

    def run(self):
        """Main loop for the LED receiver."""
        # Get the canvas object provided by the SampleBase class for drawing
        offset_canvas = self.matrix.CreateFrameCanvas()

        # Set up the network socket server
        self.setup_socket()

        # Exit if socket setup failed
        if not self.socket_listening:
            print("Socket not listening, exiting.")
            return

        print("Waiting for first connection and data...")
        # Flag to track if we have received at least one valid frame
        has_received_data = False

        try:
            # --- Main Application Loop ---
            while True:
                conn = None # Connection object
                addr = None # Client address

                try:
                    # Attempt to accept a new connection. This will block for up to the set timeout (1s).
                    # If a connection is accepted, process it. If it times out, the loop continues,
                    # allowing the display to be refreshed with the last received data.
                    conn, addr = self.server_socket.accept()

                    if conn: # Check if a connection was successfully accepted
                        # print(f"Connection accepted from {addr}") # Optional debug print
                        # Receive the matrix data from the connected client
                        received_matrix = self.receive_matrix_data(conn)

                        if received_matrix is not None: # If data was received and validated
                            self.display_matrix = received_matrix # Store it for display
                            has_received_data = True # Mark that we have valid data
                            # print("Successfully received and processed a frame.") # Optional debug print

                        # Close the connection immediately after processing the frame's data
                        try: conn.close()
                        except Exception as e: print(f"Error closing connection from {addr}: {e}")

                except socket.timeout:
                    # Expected exception if no connection is made within the accept timeout
                    pass # Just continue the loop to refresh display
                except Exception as e:
                    # Catch unexpected errors during connection handling
                    print(f"Error during connection acceptance: {e}")
                    traceback.print_exc()
                    time.sleep(0.1) # Small delay to prevent rapid error looping

                # --- Display Update Logic ---
                # This section updates the physical LED matrix display
                if self.matrix is not None and offset_canvas is not None:
                    if has_received_data: # Only update if we've ever received valid data
                        # Draw the latest received matrix data onto the canvas
                        self.update_display(offset_canvas, self.display_matrix)
                        # Swap the updated canvas to the live display, waits for vsync for smoothness
                        offset_canvas = self.matrix.SwapOnVSync(offset_canvas)
                    else:
                        # If no data yet, keep the display blank/black
                        offset_canvas.Clear()
                        offset_canvas = self.matrix.SwapOnVSync(offset_canvas)

        except KeyboardInterrupt:
            # Allows user to stop the script cleanly with Ctrl+C
            print("\nLED Receiver stopped by user.")
        except Exception as e:
            # Catch any other unexpected errors in the main loop
            print(f"An unexpected error occurred in the run loop: {e}")
            traceback.print_exc()
        finally:
            # --- Clean Up ---
            # Ensure resources are released when the script exits
            if self.server_socket:
                try: self.server_socket.settimeout(0.1); self.server_socket.close(); print("Server socket closed.")
                except Exception as e: print(f"Error closing server socket: {e}")
            if self.matrix:
                # Clear the physical LED matrix display
                try: self.matrix.Clear(); print("LED matrix cleared.")
                except Exception as e: print(f"Error clearing LED matrix: {e}")


# --- Script Entry Point ---
if __name__ == "__main__":
    # Create an instance of the LED receiver application.
    # Command-line arguments needed by SampleBase (e.g., --led-rows, --led-cols)
    # are automatically handled by the .process() method.
    receiver_app = SocketLEDReceiver()

    # Start the application. .process() handles initialization and calls .run()
    if not receiver_app.process():
         # If process() fails, print help, likely due to missing matrix arguments
         receiver_app.print_help()