import threading
import tkinter as tk
from tkinter import ttk, Tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import serial.threaded
import queue


class ReaderThread(threading.Thread):
    def __init__(self, port: str,
                 dataType: chr,
                 dataQueue: queue.Queue[float],
                 baudrate: int = 115200,
                 numOfMeasurements: int = 2):
        super().__init__()
        self.dataType = dataType
        self.port: str = port
        self.baudrate: int = baudrate
        self.serialPort: serial.Serial = None
        self.isRunning: bool = False
        self.numOfMeasurements: int = numOfMeasurements
        self.measurementsDone: int = 0
        self.tempDataQueue: queue.Queue[float] = dataQueue
        self.humDataQueue: queue.Queue[float] = dataQueue

    def run(self):
        self.serialPort = serial.Serial(self.port, self.baudrate)
        self.isRunning = True

        while self.isRunning and self.measurementsDone < self.numOfMeasurements:
            if self.serialPort.in_waiting > 0:
                receivedData: str = self.serialPort.readline().decode('utf-8')
                datatypeIndex: int = receivedData.find('#') + 1
                startIndex: int = receivedData.find('[')
                endIndex: int = receivedData.find(']')
                if datatypeIndex != 0 and startIndex != -1 and endIndex != -1:
                    dataType: chr = receivedData[datatypeIndex]
                    value = float(receivedData[startIndex + 1:endIndex])
                    if dataType == 'T' and self.dataType == 'T':
                        print("Received Temperature:", value)
                        self.tempDataQueue.put(float(value))
                        self.measurementsDone += 1
                    elif dataType == 'H' and self.dataType == 'H':
                        print("Received Humidity:", value)
                        self.humDataQueue.put(float(value))
                        self.measurementsDone += 1
        self.stop()

    def stop(self):
        self.isRunning = False
        if self.serialPort:
            self.serialPort.close()


class STM32_DATA_ANALYSER:
    def __init__(self):
        self.DHT_DELAY: int = 2000
        self.pBar = None
        self.numOfMeasurements: tk.Entry
        self.selectedAttribute: tk.Misc
        self.baudrate: tk.OptionMenu
        self.selectedBaudrate: tk.StringVar
        self.port: tk.Entry
        self.dataType: chr
        self.tempData: list[float]
        self.humData = list[float]
        self.rootPanel: tk.Frame = None
        self.isProgressBarSet: bool = False
        self.title: tk.Entry
        self.selectedTitle: str = "N/A"
        self.dataQueue: queue.Queue[float] = queue.Queue()
        self.results: list[float] = []
        self.OPTIONS: list[int] = [
            4800,
            9600,
            115200,
            230400
        ]

    def processData(self):
        if len(self.results) == int(self.numOfMeasurements.get()):
            print("Finished processing data")
            self.drawPlot()
            return

        while not self.dataQueue.empty():
            received_data = self.dataQueue.get()
            self.results.append(received_data)
            print("Received data:", received_data)
            self.pBar.step()
        self.rootPanel.after(self.DHT_DELAY, self.processData)

    def onSubmit(self):
        self.selectedTitle = self.title.get()
        if not self.isProgressBarSet:
            self.pBar = ttk.Progressbar(self.rootPanel)
            self.pBar.config(maximum=float(self.numOfMeasurements.get()), orient='horizontal', mode='determinate')
            self.pBar.pack(fill="both")
            self.isProgressBarSet = True
        reader_thread = ReaderThread(
            "COM" + self.port.get(),
            self.selectedAttribute.get(),
            self.dataQueue,
            int(self.selectedBaudrate),
            int(self.numOfMeasurements.get()),
        )
        reader_thread.start()
        self.rootPanel.after(self.DHT_DELAY, self.processData)

    def launch(self):
        root = Tk()
        root.wm_title("STM32 DATA ANALYSER")

        root_panel = tk.Frame(root, width=480, height=480)
        root_panel.place = root.winfo_screenwidth() - 100, root.winfo_screenheight() - 100
        self.rootPanel = root_panel

        titleRow = tk.Frame(root_panel)
        label = tk.Label(titleRow, text="Title:")
        label.pack(side="left")
        self.title = tk.Entry(titleRow, width=30)
        self.title.pack(side="right", padx=5)
        titleRow.pack(fill="both", expand=1)

        measurementsRow = tk.Frame(root_panel)
        label = tk.Label(measurementsRow, text="Measurements:")
        label.pack(side="left")
        self.numOfMeasurements = tk.Entry(measurementsRow, width=30)
        self.numOfMeasurements.pack(side="right", padx=5)
        measurementsRow.pack(fill="both", expand=1)

        comRow = tk.Frame(root_panel)
        label = tk.Label(comRow, text="COM port number:")
        label.pack(side="left")
        self.port = tk.Entry(comRow, width=30)
        self.port.pack(side="right", padx=5)
        comRow.pack(fill="both", expand=1)

        baudrateRow = tk.Frame(root_panel)
        label = tk.Label(baudrateRow, text="Baudrate:")
        label.pack(side="left")
        variable: tk.StringVar = tk.StringVar(baudrateRow)
        variable.set(str(self.OPTIONS[2]))
        self.baudrate = tk.OptionMenu(baudrateRow, variable, *self.OPTIONS)
        self.baudrate.pack(side="right", padx=5)
        self.baudrate.config(width=15, justify="center", border="1", direction="right", indicatoron=False)
        self.selectedBaudrate = variable.get()
        baudrateRow.pack(fill="both", expand=2)

        typeRow = tk.Frame(root_panel)
        label = tk.Label(typeRow, text="Select one of the following options:")
        label.pack(side="left")
        self.selectedAttribute = tk.StringVar()
        radio_male = tk.Radiobutton(typeRow, text="Temperature", variable=self.selectedAttribute, value="T")
        radio_male.pack(side="right", padx=5)
        radio_female = tk.Radiobutton(typeRow, text="Humidity", variable=self.selectedAttribute, value="H")
        radio_female.pack(side="right", padx=5)
        typeRow.pack(fill="both", expand=1)
        self.selectedAttribute.set(None)

        btnsRow = tk.Frame(root_panel)
        submitBtn = tk.Button(btnsRow, text="Submit", command=self.onSubmit)
        submitBtn.pack(side="left")
        quitBtn = tk.Button(btnsRow, text="Quit", command=root.quit)
        quitBtn.pack(side="right")
        btnsRow.pack(fill="both", expand=1)

        root_panel.pack()
        root.mainloop()

    def drawPlot(self):
        x_data = [i for i in range(1, int(self.numOfMeasurements.get()) + 1)]
        y_data = self.results
        fig, ax = plt.subplots()
        ax.plot(x_data, y_data, marker='o', label='Temperature')
        fig.suptitle(f'{self.selectedTitle}')
        canvas = FigureCanvasTkAgg(fig, master=self.rootPanel)
        canvas.get_tk_widget().pack(side="bottom", )
        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        ax.legend()
        canvas._tkcanvas.pack()
        canvas.draw()


if __name__ == '__main__':
    program = STM32_DATA_ANALYSER()
    program.launch()
