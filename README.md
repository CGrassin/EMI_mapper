# EMI mapping with RTL-SDR and OpenCV

Mapping near-field electromagnetic parasitic emissions is useful for the design, debug and pre-compliance testing of electronic devices. Unfortunately, there is no simple way to make EM scans with sufficient level of details/accuracy, speed and reasonable cost. Hence, I developed this solution to make **high-resolution** and **fast** 2D maps of RF EMI for PCBs and more.

## Improved version
* improved probe tracking
* live preview of heatmap
* spectrogram view by double clicking on preview

![Arduino Mega RF power map.](https://raw.githubusercontent.com/cfretter/EMI_mapper/master/output/specview.PNG)


You can find more information and details on charles project page (including more examples): http://charleslabs.fr/en/project-Electromagnetic+interference+mapping

## Prerequisites

Hardware requirements:
* A USB camera,
* An RTL-SDR with a (DIY?) near-field probe.

Software dependencies for the python script:
* OpenCV (`sudo apt install python3-opencv && pip3 install opencv-contrib-python imutils setuptools`)
* pyrtlsdr (`sudo apt install rtl-sdr && pip3 install pyrtlsdr`)
* numpy, scipy, matplotlib (`pip3 install scipy numpy matplotlib`)

*These install commands were tested in Linux Mint 19*

## Usage

To make an EM map:
1. Launch the script (optionnal arguments, refer to the help),
2. Properly position the device under test (DUT) in the camera image,
3. Press "R" to set the position (**the camera and DUT must not move after pressing "R"**),
4. Put the probe in the frame, press "S", select the probe with the mouse and press "ENTER" to start the scanning,
5. Scan the DUT by moving the probe,
6. Press "Q" to exit. If a scan was made, the result is displayed.

Call with `python3 emi.py -h` to view the help (arguments description).

Typical use: `python3 emi.py -c 1 -f 100` (start the script using a 100MHz center frequency and camera id 1).

## Sample result

This is a scan of an Arduino Uno board performed with this script and a DIY near-field loop probe:

![Arduino Uno RF power map.](https://raw.githubusercontent.com/CGrassin/EMI_mapper/master/output/Arduino_Uno.png)