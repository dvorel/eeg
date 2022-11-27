from threading import Thread
import serial
import time
import collections
import pandas as pd
import os

import datetime

from random import randint
import cv2
import numpy as np
from time import sleep

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages


class serialPlot:
    def __init__(self, serialPort='/dev/ttyUSB0', serialBaud=38400, plotLength=100, numberOfChannels=3, delimiter=",", saveDir="runs", delay=5, pause=2, sampleRate = 500):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.numPlots = numberOfChannels
        self.saveDir = saveDir
        #self.rawData = bytearray()
        self.parser = None

        self.sampleTime = 1000000000/sampleRate

        self.actionThread = None
        self.action = -1
        self.actionDelay = delay
        self.actionPause = pause
        self.actions = []
        self.dataCSV = []

        self.buffer = []


        
        self.data = []
        for i in range(numberOfChannels):   # give an array for each type of data and store them in a list
            self.data.append(collections.deque([0] * plotLength, maxlen=plotLength))
            self.dataCSV.append([])
        
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
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')

            
    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            time.sleep(1)

        if self.parser == None:
            self.parser = Thread(target=self.parseBuffer)
            self.parser.start()
            time.sleep(0.1)

    
    def getSerialData(self, frame, lines, pltNumber):
        if pltNumber == 0:  # in order to make all the clocks show the same reading
            currentTimer = time.perf_counter()
            self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
            self.previousTimer = currentTimer

        for i in range(len(lines)):
            lines[i].set_data(range(self.plotMaxLength), self.data[i])


    def backgroundThread(self):    # retrieve data
        # give some buffer time for retrieving data
        self.serialConnection.readline()
        self.serialConnection.readline()

        while (self.isRun):
            #self.rawData = self.serialConnection.readline()
            self.buffer.insert(0, self.serialConnection.readline())
        
        #self.parseData()
    
    def parseBuffer(self):
        app = True
        values = []

        while True:
            try:
                privateData = self.buffer.pop()

            except:
                #print("Buffer empty")
                sleep(0.002)
                continue
            
            try:
                privateData = str(privateData.decode()).strip().split(self.delimiter)
            except:
                continue

            if self.numPlots != len(privateData):
                print("Received less or more data!!!")
                print(len(privateData))
                continue
            
            values = []
            
            for j in range(len(privateData)):
                try:
                    values.append(int(privateData[j]))
                except:
                    print("ERROR: parsing failed!")
                    app = False
                    break
            
            if not app:
                continue

            for j in range(len(values)):
                self.data[j].append(values[j])
                self.dataCSV[j].append(values[j])
            
            self.actions.append(self.action)
            

    def parseData(self):
        privateData = str(self.rawData.decode()).strip().split(self.delimiter)

        
        if self.numPlots != len(privateData):
            print("Received less or more data!!!")
            print(len(privateData))
            return
        
        values = []

        for j in range(len(privateData)):
            try:
                values.append(int(privateData[j]))
            except:
                print("ERROR: parsing failed!")
                continue
            
        for j in range(len(values)):
            self.data[j].append(values[j])
            self.dataCSV[j].append(values[j])
        
        self.actions.append(self.action)

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
        if self.actionThread is not None:
            self.actionThread.join()
        self.serialConnection.close()
        
        print('Disconnected...')

        dir = str(self.getSaveDir())

        #save pdf
        pdf = PdfPages(dir + '/pdfPlot.pdf')
        pdf.savefig(fig)
        pdf.close()
        
        #save csv
        df = pd.DataFrame(self.dataCSV)
        df.loc[len(df.index)] = self.actions
        df.to_csv(dir + '/csvData.csv', header=False)  

        #save txt
        with open(dir + '/info.txt', 'w') as f:
            for k, v in data.items():
                f.write(str(k) + " : " + str(v) + "\n")


    def random_digit(self):
        print("Starting num")
        while self.isRun:
            self.action = str(-1)
            arr = np.zeros((1080, 1920, 1))
            cv2.imshow("num", arr)
            cv2.waitKey(1)
            sleep(self.actionPause)

            next = str(randint(0, 9))
            cv2.putText(arr, next, (600, 900), cv2.FONT_HERSHEY_SIMPLEX, 30, (255, 255, 255), 12)
            cv2.imshow("num", arr)
            cv2.waitKey(1)
            sleep(0.5)
            self.action = next
            sleep(self.actionDelay-0.5)
            
        
    def on_press(self, event):
        if not self.isReceiving or event.key=="meta":
            return
        
        if event.key == "f1":
            if self.actionThread != None:
                print("Thread running!")
                return

            self.actionThread = Thread(target=self.random_digit)
            self.actionThread.start()
            return

        self.action = str(event.key)
        print(self.action)

    def open_window(self):
        arr = np.zeros((1080, 1920, 1))
        cv2.namedWindow("num", cv2.WINDOW_NORMAL)
        cv2.imshow("num", arr)
        cv2.waitKey(0)
        cv2.setWindowProperty("num", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.waitKey(0)


def main():
    SAMPLES = "500 samples/s"
    MAXY = 750
    MAXX = 300
    PORT = 'COM6'
    BAUD = 1000000
    DELAY = 4

    #plot style
    N = 16
    NCOLS = 2

    LABELS = [str(i) for i in range(N)]
    style = 'w-'
    


    s = serialPlot(PORT, BAUD, MAXX, numberOfChannels=N)   # initializes all required variables
    s.actionDelay = DELAY
    #s.open_window()


    s.readSerialStart()                                               # starts background thread
    t_start= time.time_ns()
 
    #collect some data for txt file
    runData = {}
    runData["SAMPLES:"] = str(SAMPLES)
    runData["BAUD:"] = str(BAUD)
    runData["Electrodes:"] = str(N)
    runData["Labels:"] = str(LABELS)
    runData["Start time:"] = str(datetime.datetime.now())

    # plotting starts below
    pltInterval = 250    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = MAXX
    ymin = 0
    ymax = MAXY

    lines = []
    anims = []

    plt.style.use('dark_background')
    
    fig, plots =  plt.subplots(nrows=N//NCOLS, ncols=NCOLS, figsize=(1000,800))

    fig.canvas.mpl_connect('key_press_event', s.on_press)

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
