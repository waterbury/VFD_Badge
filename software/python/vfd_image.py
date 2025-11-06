import spidev
import time
import random
import getopt, sys
from PIL import Image, ImageEnhance, ImageOps
import numpy as np


GP1294AI_CMD_RESET = 0xAA
GP1294AI_CMD_FRAME_SYNC = 0x08
GP1294AI_CMD_BRIGHTNESS = 0xA0
GP1294AI_CMD_DISPLAY_MODE = 0x80
GP1294AI_CMD_WRITE_GRAM = 0xF0
GP1294AI_CMD_DISPLAY_OFFSET = 0xC0
GP1294AI_CMD_VFD_MODE = 0xCC
GP1294AI_CMD_OSC_SETTING = 0x78
GP1294AI_CMD_EXIT_STANDBY = 0x6D
GP1294AI_CMD_ENTER_STANDBY = 0x61

GP1294AI_MAX_FREQ = 4167000
GP1294AI_DEFAULT_BRIGHTNESS = 1000

cmd_reset = [GP1294AI_CMD_RESET]
cmd_init = [GP1294AI_CMD_VFD_MODE, 0x01, 0x01F, 0x00, 0xFF, 0x2F, 0x00, 0x20]
cmd_brightness = [GP1294AI_CMD_BRIGHTNESS, GP1294AI_DEFAULT_BRIGHTNESS & 0xFF, (GP1294AI_DEFAULT_BRIGHTNESS >> 8) & 0xFF]
cmd_offset = [GP1294AI_CMD_DISPLAY_OFFSET, 0x00, 0x00]
cmd_mode = [GP1294AI_CMD_DISPLAY_MODE, 0x00]
cmd_init_osc = [GP1294AI_CMD_OSC_SETTING, 0x08]

# We only have SPI bus 0 available to us on the Pi
bus = 0

#Device is the chip select pin. Set to 0 or 1, depending on the connections
device = 1

# Enable SPI
spi = spidev.SpiDev()

# Open a connection to a specific bus and device (chip select pin)
spi.open(bus, device)

# Set SPI speed and mode
spi.max_speed_hz = 1000000
spi.mode = 3
#spi.lsbfirst

# Sets up LSB FIRST
def reverse(array):
    for index, value in enumerate(array):
        #print(array[index])
        array[index] = int('{:08b}'.format(value)[::-1], 2) 
    return array

def spi_transfer(array):
    spi.xfer2(reverse(array))

def clear():
    empty_frame = [0x00] * 1535 #*(256*8)
    payload = [0xF0, 0, 0, 47] + empty_frame
    print(len(payload))
    spi_transfer(payload)

def fill():
    empty_frame = [0xFF] * 1536 # (256*8)
    payload = [0xF0, 0, 0, 47] + empty_frame
    print(len(payload))
    spi_transfer(payload)

def draw(image):

    i = 0
    x_bit = 0
    binary = [0x00] * 1536

    # VFD draws from right to left. Flipping image as array will be stored left to right.
    # Makes sure image is in 1 bit color.
    img_1bit = image.convert('1', dither=Image.FLOYDSTEINBERG ).transpose(Image.FLIP_TOP_BOTTOM)

    orig_horiz_res, orig_vert_res = img_1bit.size
    print(f"Image resolution: {orig_horiz_res}x{orig_vert_res} pixels")

    screen_vert_res=256
    screen_horiz_res=48

        # Calculate aspect ratios
    screen_aspect = screen_horiz_res / screen_vert_res
    orig_image_aspect = orig_horiz_res / orig_vert_res

    print("image_aspect: " + str(orig_image_aspect))

    # If image is not vertical, rotate.
    if orig_image_aspect > 1:
        img_1bit = img_1bit.rotate(270, expand=True)
        orig_horiz_res, orig_vert_res = img_1bit.size
        print("Image not vertical, rotating.")
        print(f"New Image resolution: {orig_horiz_res}x{orig_vert_res} pixels")
        orig_image_aspect = orig_horiz_res / orig_vert_res
        print("image_aspect: " + str(orig_image_aspect))


    crop_horiz_origin = 0
    crop_vert_origin = 0

    if orig_vert_res > screen_vert_res or orig_horiz_res > screen_horiz_res:
        img_1bit = img_1bit.crop((crop_horiz_origin, crop_vert_origin, crop_horiz_origin + screen_horiz_res, crop_vert_origin + screen_vert_res))
        # Image is larger, so crop
        #if orig_horiz_res > screen_horiz_res:
        #    # Original is wider, crop width
        #    left = 0
        #    top = 0
        #    right = left + new_width
        #    bottom = original_height
        #else:
        #    # Original is taller, crop height
        #    new_height = int(original_width / target_aspect)
        #    left = 0
        #    top = (original_height - new_height) // 2
        #    right = original_width
        #    bottom = top + new_height
        #img_1bit = img_1bit.crop((0, 0, screen_horiz_res, screen_vert_res))
        #img = img.resize((target_width, target_height), Image.LANCZOS) # Resize after cropping
    #elif original_width < target_width or original_height < target_height:
    #    # Image is smaller, so pad
    #    img = ImageOps.pad(img, (target_width, target_height), color=fill_color)


    image_array = list(img_1bit.getdata())

    frame = [0x00] * 1536
    pixel = 0

    #Transposes image into format VFD will display

    image_array_len = len(image_array)
    bitmapByteNum = 0
    bitmapPixNum = 0
    for bitmapByteNum in range(image_array_len):
        for i in range(0, 8):
            if (bitmapPixNum < len(image_array)): # Safety check
                if ((image_array[bitmapPixNum] == 0)):
                    frame[bitmapByteNum] += 0 << i
                else:
                    frame[bitmapByteNum] += 1 << i
                # Increment bitmapPixNum at the end of the inner loop
                bitmapPixNum += 1

    # 47 actually means 48, counting 0 as 1 :-/
    payload = [0xF0, 0, 0, 47] + frame
    print(len(payload))
    spi_transfer(payload)

def randomGen(startPos):
    random.seed(a=None, version=2)
    frame =[0] * (256*9)
    randVal = random.randint(0,255)
    for i in range(len(frame)):
        #print(i)
        #randVal = random.randint(0,255)
        if i % 100 <= 25:
            frame[i] =  randVal
        else:
            randVal = random.randint(0,255)
            frame[i] = randVal

    payload = [0xF0, randVal, 0, 48] + frame
    print(len(payload))
    spi_transfer(payload)



def init():
    spi_transfer(cmd_reset)
    #spi_transfer([0x6D])
    time.sleep(0.1)
    spi_transfer(cmd_init)
    spi_transfer(cmd_brightness)
    time.sleep(0.02)
    spi_transfer(cmd_offset)
    spi_transfer(cmd_mode)
    spi_transfer(cmd_init_osc)

def init_test():
    #spi_transfer([0x6D])
    #spi_transfer([0xAA])

    spi_transfer([0xCC,0x01,0x1F,0x00,0xFF,0x2F,0x00,0x20])
    spi_transfer([0xA0,0x28,0x04])
    clear()
    time.sleep(0.02)
    spi_transfer([0xF0,0x00,0x00])
    spi_transfer([0x80,0x00])
    spi_transfer([0x78,0x08])



args = sys.argv[1:]
options = "hf:"
long_options = ["Help", "file"]

try:
    arguments, values = getopt.getopt(args, options, long_options)
    for currentArg, currentVal in arguments:
        if currentArg in ("-h", "--Help"):
            print("Showing Help")
        elif currentArg in ("-f", "--file"):
            filename=currentVal
            print("File name:", currentVal)
except getopt.error as err:
    print(str(err))

init()

image_1 = Image.open(filename)
draw(image_1)
