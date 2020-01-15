import serial # pip3 instal pyserial
import argparse
import time
from rtlsdr import RtlSdr # pip3 install pyrtlsdr
import numpy as np
import matplotlib.pyplot as plt
import camera_emi_mapper

def send_gcode(s, gcode, wait_for_ok=True):
    #print(gcode)
    s.write(gcode + b'\n')
    if wait_for_ok:
        ack_ok = False
        while not ack_ok:
            line = s.readline()
            #print(line)
            if line == b'ok\n':
                ack_ok = True
      
def main():          
    parser = argparse.ArgumentParser(description='EMI mapping with 3D-printer and RTL-SDR.')
    parser.add_argument('-p', '--serial-port', type=str, help='printer serial port.',default='/dev/ttyACM0')
    parser.add_argument('-b', '--baud-rate', type=int, help='printer serial baud rate (default: 250000 for Marlin).',default=250000)
    parser.add_argument('-f', '--frequency', type=float, help='sets the center frequency on the SDR, in MHz (default: 300).',default=300)
    parser.add_argument('-g', '--gain', type=int, help='sets the SDR gain in 0.1dB (default: 496).',default=496)
    parser.add_argument('-z', '--zone-size', type=int, help='size of the zone to map in mm (default: 100).',default=100)
    parser.add_argument('-r', '--resolution', type=int, help='resolution of the grid in mm (default: 10).',default=10)
    parser.add_argument('--px-mm', type=int, help='final picture pixels per mm (default: 10).',default=10)
    parser.add_argument('--feedrate', type=int, help='feedrate percentage, put more than 100 for greater speed (default: 100).',default=100)
    args = parser.parse_args()
    
    # Args
    # General
    gridStep=args.resolution; #mm
    gridSize=args.zone_size; #mm
    pixelPerMM=args.px_mm; #px/mm
    feedrate = args.feedrate; #%
    # SDR stuff
    frequency=args.frequency; #MHz
    gain = args.gain; #0.1dB
    # Serial
    port=args.serial_port;
    baudrate=args.baud_rate;
    
    # Vars
    steps=int(gridSize/gridStep);
    
    # Open serial port
    s = serial.Serial(port, baudrate,timeout=1)
    
    # Open SDR
    sdr = RtlSdr()
    sdr.sample_rate = 2.4e6
    sdr.center_freq = frequency * 1e6
    sdr.gain = gain
    sdr.set_agc_mode(0)
    power = emi.get_RMS_power(sdr) #First read doesn't work
    
    # Prepare canvas
    powermap = np.empty((gridSize*pixelPerMM,gridSize*pixelPerMM))
    powermap.fill(np.nan)
    cell_size=(gridStep*pixelPerMM)
    
    # Init. machine
    s.write(b'\n')
    time.sleep(2)
    line = ''
    while not (line == b'ok\n' or line == b'echo:SD card ok\n'):
        line = s.readline()
        
    send_gcode(s,b'G21') # Set unit to mm
    send_gcode(s,b'G90') # Set to *Absolute* Positioning
    
    send_gcode(s,b'G28 XY') # Home XY
    send_gcode(s,b'M400') # Wait for current moves to finish
    
    send_gcode(s,b'M220 S' + str(feedrate).encode()) # Goto XY zero
    
    send_gcode(s,b'G0 X0Y0Z0') # Goto XY zero
    send_gcode(s,b'M400') # Wait for current moves to finish
    
    # Go through the grid
    direction = True;
    for y in range(steps):
         # Fast Move (Y axis)
        send_gcode(s,b'G0 Y' + str(y*gridStep).encode())
        send_gcode(s,b'M400')
        
        x_iter = range(steps)
        if not direction:
            x_iter = reversed(x_iter)
            
        for x in x_iter:
            send_gcode(s,b'G0 X' + str(x*gridStep).encode()) # Fast Move (X axis)
            send_gcode(s,b'M400') # Wait for current moves to finish
            
            # Measure
            power = emi.get_RMS_power(sdr)
            print("RMS power",power,"dBm at (",x*gridStep,"mm;",y*gridStep, "mm)")
            powermap[int(y*cell_size):int(y*cell_size+cell_size),int(x*cell_size):int(x*cell_size+cell_size)] = power
    
        direction = not direction
    send_gcode(s,b'M18') # SRelease steppers
    
    # Close ressources
    s.close()
    sdr.close()
    
    # Display picture
    blurred = emi.gaussian_with_nan(powermap, sigma=3*pixelPerMM)
    plt.imshow(blurred, cmap='hot', interpolation='nearest',alpha=1, extent=[0,gridSize,0,gridSize])
    plt.title("EMI map (min. "+"%.2f" % np.nanmin(powermap)+" dBm, max. "+"%.2f" % np.nanmax(powermap)+" dBm)")
    plt.xlabel("mm")
    plt.ylabel("mm")
    plt.show()

if __name__== "__main__":
  main()
