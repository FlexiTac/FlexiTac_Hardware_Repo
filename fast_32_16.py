import numpy as np
import serial
import threading
import cv2
import time
from scipy.ndimage import gaussian_filter  # (still unused unless you enable)

# =========================
# SAME visualization settings as old code
# =========================
contact_data_norm = np.zeros((16, 32), dtype=np.float32)
WINDOW_WIDTH = contact_data_norm.shape[1] * 30
WINDOW_HEIGHT = contact_data_norm.shape[0] * 30
cv2.namedWindow("Contact Data_left", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Contact Data_left", WINDOW_WIDTH, WINDOW_HEIGHT)

THRESHOLD = 15
NOISE_SCALE = 60
flag = False

# =========================
# NEW serial format settings
# =========================
MAGIC = b"\xAA\x55"
ROWS, COLS = 16, 32
FRAME_BYTES = ROWS * COLS  # 512
INIT_FRAMES = 30

PORT = "/dev/ttyUSB0"
BAUD = 2_000_000


def temporal_filter(new_frame, prev_frame, alpha=0.2):
    return alpha * new_frame + (1 - alpha) * prev_frame


def readThread(serDev):
    """
    Replacement for old readline()/text parsing thread.
    Reads frames: 0xAA 0x55 + 512 bytes.
    Produces contact_data_norm like old code.
    """
    global contact_data_norm, flag

    ring = bytearray()
    frame_buf = bytearray(FRAME_BYTES)

    data_tac = []
    t1 = time.time()
    flag = False

    serDev.timeout = 0.01 # helps responsiveness

    def read_exact(n):
        """Read exactly n bytes from serial (blocking up to timeout loops)."""
        buf = bytearray(n)
        mv = memoryview(buf)
        got = 0
        while got < n:
            r = serDev.readinto(mv[got:])
            if r is None:
                r = 0
            if r == 0:
                return None
            got += r
        return buf

    # -------------------------
    # 1) Initialization: collect INIT_FRAMES and compute median baseline
    # -------------------------
    while True:
        chunk = serDev.read(4096)
        if not chunk:
            continue
        ring.extend(chunk)

        # keep buffer bounded
        if len(ring) > 50000:
            ring = ring[-50000:]

        idx = ring.find(MAGIC)
        if idx < 0:
            # keep last byte in case marker splits
            if len(ring) > 1:
                ring = ring[-1:]
            continue

        # drop before marker, consume marker
        if idx > 0:
            del ring[:idx]
        if len(ring) < 2:
            continue
        del ring[:2]

        # read one frame (512)
        if len(ring) >= FRAME_BYTES:
            frame_buf[:] = ring[:FRAME_BYTES]
            del ring[:FRAME_BYTES]
        else:
            have = len(ring)
            frame_buf[:have] = ring[:have]
            del ring[:have]
            rem = FRAME_BYTES - have
            rest = read_exact(rem)
            if rest is None:
                ring.clear()
                continue
            frame_buf[have:] = rest

        frame = np.frombuffer(frame_buf, dtype=np.uint8).reshape((ROWS, COLS)).astype(np.float32)
        data_tac.append(frame)

        now = time.time()
        print("init fps", 1 / (now - t1 + 1e-9))
        t1 = time.time()

        if len(data_tac) >= INIT_FRAMES:
            break

    data_tac = np.stack(data_tac, axis=0)  # (N,16,32)
    median = np.median(data_tac, axis=0)
    flag = True
    print("Finish Initialization!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    # -------------------------
    # 2) Streaming loop: update contact_data_norm per frame
    # -------------------------
    while True:
        chunk = serDev.read(8192)
        if not chunk:
            continue
        ring.extend(chunk)

        if len(ring) > 50000:
            ring = ring[-50000:]

        # parse as many complete frames as available
        while True:
            idx = ring.find(MAGIC)
            if idx < 0:
                # keep last byte for split marker
                if len(ring) > 1:
                    ring = ring[-1:]
                break

            # drop before marker
            if idx > 0:
                del ring[:idx]

            # need marker + frame
            if len(ring) < 2 + FRAME_BYTES:
                # not enough yet
                break

            # consume marker
            del ring[:2]

            # take frame bytes
            frame_bytes = ring[:FRAME_BYTES]
            del ring[:FRAME_BYTES]

            backup = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((ROWS, COLS)).astype(np.float32)

            # old-style processing
            contact_data = backup - median - THRESHOLD
            contact_data = np.clip(contact_data, 0, 100)

            if np.max(contact_data) < THRESHOLD:
                contact_data_norm = contact_data / NOISE_SCALE
            else:
                contact_data_norm = contact_data / (np.max(contact_data) + 1e-6)


# =========================
# Start serial + thread (same as old code)
# =========================
serDev = serial.Serial(PORT, BAUD)
serDev.flush()
serDev.reset_input_buffer()

serialThread = threading.Thread(target=readThread, args=(serDev,))
serialThread.daemon = True
serialThread.start()

# =========================
# Main visualization loop (same style as old)
# =========================
prev_frame = np.zeros_like(contact_data_norm, dtype=np.float32)

if __name__ == "__main__":
    print("receive data test")

    while True:
        for i in range(300):
            if flag:
                temp_filtered_data = temporal_filter(contact_data_norm, prev_frame, alpha=0.2)
                prev_frame = temp_filtered_data

                temp_filtered_data_scaled = np.clip(temp_filtered_data * 255.0, 0, 255).astype(np.uint8)
                colormap = cv2.applyColorMap(temp_filtered_data_scaled, cv2.COLORMAP_VIRIDIS)

                cv2.imshow("Contact Data_left", colormap)
                cv2.waitKey(1)

            time.sleep(0.005)
