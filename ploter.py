"""
Plot and save values of 16 input values from COM (serial) port.

#### github.com/dvorel ####
"""

from threading import Thread
import serial
import time
import collections
import pandas as pd
import os

import datetime

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages


class serialPlot:
    def __init__(self, serialPort='/dev/ttyUSB0', serialBaud=38400, plotLength=100, numberOfChannels=3, delimiter=",", saveDir="runs"):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.numPlots = numberOfChannels
        self.saveDir = saveDir
        self.rawData = bytearray()

        
        self.data = []
        for i in range(numberOfChannels):   # give an array for each type of data and store them in a list
            self.data.append(collections.deque([0] * plotLength, maxlen=plotLength))
        
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        self.delimiter = delimiter

        self.csvData = []
        for i in range(numberOfChannels):
            self.csvData.append(list())


        print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=4)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')

            
    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)

    
    def getSerialData(self, frame, lines, pltNumber):
        #print("GSD: ", frame, index)
        # currentTimer = time.perf_counter()
        # index = 0
        # self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
        # self.previousTimer = currentTimer
        # timeText[index].set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')

        if pltNumber == 0:  # in order to make all the clocks show the same reading
            currentTimer = time.perf_counter()
            self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
            self.previousTimer = currentTimer

        for i in range(len(lines)):
            lines[i].set_data(range(self.plotMaxLength), self.data[i])


    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.rawData = self.serialConnection.readline()
            self.parseData()
            self.isReceiving = True
    
            
    def parseData(self):
        self.rawData = str(self.rawData.decode()).split(self.delimiter)
        
        if self.numPlots != len(self.rawData):
            print("Received less or more data!!!")
            return False
        
        values = []

        for i in range(len(self.rawData)):
            try:
                values.append(int(self.rawData[i]))
            except:
                print("ERROR: parsing failed!")
                return False
            
        for i in range(len(values)):
            self.data[i].append(values[i])

        return True
    
    def getSaveDir(self):
        os.makedirs(self.saveDir, exist_ok=True)
        dirs = os.listdir(self.saveDir)
        dirs.sort(reverse=True)
        
        last = 0

        for i in range(len(dirs)):
            try:
                last = int(dirs[i])+1
                break
            except:
                continue
        
        finalDir = os.path.join(self.saveDir, str(last))
        os.makedirs(finalDir, exist_ok=True)
        return finalDir

    
    def close(self, fig, data):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')

        dir = str(self.getSaveDir())

        #save pdf
        pdf = PdfPages(dir + '/pdfPlot.pdf')
        pdf.savefig(fig)
        pdf.close()
        
        #save csv
        df = pd.DataFrame(self.data)
        df.to_csv(dir + '/csvData.csv', header=False)     

        #save some info
        with open(dir + '/info.txt', 'w') as f:
            for k, v in data.items():
                f.write(str(k) + " : " + str(v) + "\n")



def main():
    SAMPLES = "500 samples/s"
    MAXY = 1024
    MAXX = 1500
    PORT = 'COM6'
    BAUD = 115200

    #plot style
    N = 16
    NCOLS = 2

    LABELS = [str(i) for i in range(N)]
    style = 'w-'
    

    #collect some data for txt file
    runData = {}
    runData["SAMPLES:"] = str(SAMPLES)
    runData["BAUD:"] = str(BAUD)
    runData["Electrodes:"] = str(N)
    runData["Labels:"] = str(LABELS)
    runData["Start time:"] = str(datetime.datetime.now())

    t_start= time.time_ns()

    s = serialPlot(PORT, BAUD, MAXX, numberOfChannels=N)   # initializes all required variables
    s.readSerialStart()                                               # starts background thread

    # plotting starts below
    pltInterval = 50    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = MAXX
    ymin = -(MAXY)
    ymax = MAXY

    lines = []
    anims = []

    plt.style.use('dark_background')
    fig, plots =  plt.subplots(nrows=N//NCOLS, ncols=NCOLS, figsize=(1000,800))

    plt.subplots_adjust(left=0.001,
                    bottom=0.1,
                    right=0.999,
                    top=0.98,
                    wspace=0.1,
                    hspace=0.01)

    for i, ax in enumerate(plots.flat):
        ax.set_xlabel(SAMPLES)
        ax.set_title(LABELS[i], y=1.0, pad=-14)

        ax.set(xlim=(xmin, xmax), ylim=(int(ymin - (ymax - ymin) / 10), int(ymax + (ymax - ymin) / 10)))

        lines.append(ax.plot([], [], style, linewidth=0.5, label='_nolegend_')[0])

        anims.append(animation.FuncAnimation(fig, s.getSerialData, fargs=(lines, i), interval=pltInterval)) # fargs has to be a tuple

    
    plt.show()


    runData["Run time (ns):"] = str(time.time_ns() - t_start)
    runData["Run time (s):"] = str((time.time_ns() - t_start) / 1000000000)
    runData["Samples:"] = str(len(s.data))
    s.close(fig, runData)


if __name__ == '__main__':
    main()
