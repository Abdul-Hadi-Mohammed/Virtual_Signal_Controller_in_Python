import tkinter as tk
import threading
import queue
import time
import re
from signal_util import OCIT_def
from datetime import datetime

class TrafficLightApp:
    def __init__(self, window, name, switch_interval_queue, signal_wish_queue):
        scal = 0.75
        self.window = window
        self.window.title(name)

        # Erstelle eine Leinwand, um die Ampel zu zeichnen
        self.width = scal * (65 + 200 + 65)
        self.height = scal * (65 + (200 + 35) * 2 + 200 + 65)
        self.canvas = tk.Canvas(window, width=self.width, height=self.height, bg='black')
        self.canvas.pack()

        # Farbvariablen
        self.colors = {
            "rot": '#B81B0E',  # Rot als HEX
            "gelb": '#F5A900',  # Gelb als HEX
            "gruen": '#339966',  # Grün als HEX
            "weiß": '#FFFFFF',  # initialer Zustand: weiß
            "aus": '#4D4D4D',  # Dunkle Farbe für ausgeschaltete Lichter
        }

        #Signalbilder
        self.signal_wish_queue = signal_wish_queue
        self.signal_patterns = {
            "rot": [1, 0, 0, 0, 0], # [rot, gelb, grün, freq[Hz; 0 -> dauer],wbl[1 -> True/ 0 -> False]
            "rotgelb": [1, 1, 0, 0, 0],
            "gelb": [0, 1, 0, 0, 0],
            "gruen": [0, 0, 1, 0, 0],
            "dunkel": [0, 0, 0, 0, 0],
            "rotgruen": [1, 0, 1, 0, 0],
            "gelbgruen": [0, 1, 1, 0, 0],
            "rotblk": [1, 0, 0, 1, 0],
            "gelbblk": [0, 1, 0, 1, 0],
            "gruenblk": [0, 0, 1, 1, 0],
            "wbl_rotgruen": [1, 0, 1, 1, 1],
            "wbl_rotgelb": [1, 1, 0, 1, 1],
            "wbl_gelbgruen": [0, 1, 1, 1, 1],
            "rotblk2hz": [1, 0, 0, 2, 0],
            "gelbblk2hz": [0, 1, 0, 2, 0],
            "gruenblk2hz": [0, 0, 1, 2, 0],
            "wbl2hz_rotgruen": [1, 0, 1, 2, 1],
            "wbl2hz_rotgelb": [1, 1, 0, 2, 1],
            "wbl2hz_gelbgruen": [0, 1, 1, 2, 1],
        }

        # Queue für das Farbwechselintervall
        self.switch_interval_queue = switch_interval_queue
        self.current_interval = 10  # [ms] Standardintervall

        # Initialisiere Ampellichter
        self.lights = {
            "rot": self.canvas.create_oval(scal * 65, scal * 65, scal * 265, scal * 265, fill=self.colors["aus"]),
            "gelb": self.canvas.create_oval(scal * 65, scal * 300, scal * 265, scal * 500, fill=self.colors["aus"]),
            "gruen": self.canvas.create_oval(scal * 65, scal * 535, scal * 265, scal * 735, fill=self.colors["aus"])
        }
        self.lights_no = {
            1: "rot",
            2: "gelb",
            3: "gruen",
        }
        self.signal_wish = 'gelbblk'
        self.signal_wish_controll = 'dunkel'

        #initialsiere freq, wbl
        self.freq_val = False
        self.wbl_val = "dunkel"

        # Starte den Farbwechsel
        self.update_light()
        print(f"Initializing signal vis for {name}- Done")

    def update_light(self):
        # Überprüfe, ob ein neues Intervall in der Queue ist
        try:
            self.current_interval = self.switch_interval_queue.get()
        except:
            pass

        # Nur versorgte Farben nutzen
        try:
            self.signal_wish = self.signal_wish_queue.get()
        except queue.Empty:
            self.signal_wish = 'dunkel'
        if not self.signal_wish_controll == self.signal_wish:
            print(f'Signalbild: {self.signal_wish}')
            self.signal_wish_controll = self.signal_wish

        # Setze alle Lichter auf AUS
        for light in self.lights.values():
            self.canvas.itemconfig(light, fill=self.colors["aus"])

        # Definiere das gewünschte Signalbild
        var = self.signal_patterns[self.signal_wish]
        rot = bool(var[0])
        gelb = bool(var[1])
        gruen = bool(var[2])
        freq = int(var[3])
        wbl = bool(var [4])

        #setze das gewünschte Signalbild
        if freq > 0:
            self.current_interval = int(1000/(freq*2)) #1000ms durch Frezquenz des gesamten Zyklus
            for light_no in self.lights_no.keys():
                if bool(var[light_no - 1]):
                    if not self.wbl_val == self.lights[self.lights_no[light_no]]:
                        self.canvas.itemconfig(self.lights[self.lights_no[light_no]],
                                               fill=self.colors[self.lights_no[light_no]])
                        self.wbl_val = self.lights[self.lights_no[light_no]]
                        break
                    elif not wbl:
                        self.wbl_val = "dunkel"
                        break

        else:
            if rot:
                self.canvas.itemconfig(self.lights['rot'], fill=self.colors['rot'])
            if gelb:
                self.canvas.itemconfig(self.lights['gelb'], fill=self.colors['gelb'])
            if gruen:
                self.canvas.itemconfig(self.lights['gruen'], fill=self.colors['gruen'])

        # Rufe diese Methode nach dem aktuellen Intervall erneut auf
        self.window.after(self.current_interval, self.update_light)

def run_traffic_light_app(name, switch_interval_queue, signal_wish_queue):
    window = tk.Tk()
    app = TrafficLightApp(window, name=name, switch_interval_queue=switch_interval_queue, signal_wish_queue=signal_wish_queue)
    window.mainloop()

def init_signal_vis(name):
    color_switch_interval_queue = queue.Queue(maxsize=1)
    signal_wish_queue = queue.Queue(maxsize=1)
    color_switch_interval_queue.put(10)
    signal_wish_queue.put("dunkel")

    # Starte die TrafficLightApp in einem separaten Thread
    thread = threading.Thread(target=run_traffic_light_app, args=(name, color_switch_interval_queue,signal_wish_queue))
    thread.daemon = True
    thread.start()
    print(f"Initializing signal vis for {name}")

    return color_switch_interval_queue, signal_wish_queue

def test_routine_1(Startzeit, Signaldauer: int, OCIT_Signale: dict) -> int:
    index = int(((time.time() - Startzeit) % ((len(OCIT_Signale) - 1) * Signaldauer)) / Signaldauer)
    # print(time.time(), index + 1)
    return index + 1

def SZP_builder(Startzeit, Signalbilder: [(str,int)]):
    Signalwunsch = "dunkel"
    tu = sum(Signal[1] for Signal in Signalbilder)
    tz = int(((time.time() - Startzeit) % (tu)))
    for Signal in Signalbilder:
        if tz < Signal[1]:
            Signalwunsch = Signal[0]
            break
        else: tz -= Signal[1]
    return Signalwunsch

def listen_for_input(input_queue):
    while True:
        user_input = input("Eingabe akitv\n")
        input_queue.append(user_input)

if __name__ == "__main__":
    color_switch_interval_queue, signal_wish_queue = init_signal_vis("K_Test")

    # Hier läuft weiterer Code, der die Intervalle steuert
    start_time = time.time()
    zeitkonstante = 10 #Berechnungsschritte je Sekunde
    Signaldauer = 3 #Dauer je Signal
    signalindex = 1
    OCIT_signals_util = OCIT_def('OCIT_def.csv')
    OCIT_signals = OCIT_signals_util.indexToName
    OCIT_codes = OCIT_signals_util.codeToName
    Signalwunsch = "dunkel"


    # Liste, die als einfache Queue dient
    input_queue = []
    userInputAktiv = True
    cmd = ""

    #Signalplan 1
    Signaldef_SZP1 = [
        ("rot", 5),
        ("rotgelb", 1),
        ("gruen", 5),
        ("gelb", 3)
    ]

    if userInputAktiv:
        # Erstelle und starte einen Thread, der die Funktion `listen_for_input` ausführt
        input_thread = threading.Thread(target=listen_for_input, args=(input_queue,))
        input_thread.daemon = True
        input_thread.start()

    while True:
        while round(time.time(),2) * zeitkonstante % 1 == 0:
            signal_update_interval = 10
            color_switch_interval_queue.put(signal_update_interval)
            if input_queue:
                cmd = input_queue.pop(0)
                cmd = re.sub(r'[^a-z0-9]', '', cmd.lower()) #Entfernt alle Zeichen außer Buchstaben (welche alle klein werden) oder Zahlen
                if cmd in OCIT_signals.values():
                    Signalwunsch = cmd
                elif cmd in OCIT_codes.keys():
                    Signalwunsch = OCIT_codes[cmd]
                elif cmd == "test":
                    start_time = time.time()
                    Signalwunsch = OCIT_signals[str(test_routine_1(start_time, Signaldauer, OCIT_signals))]
                elif cmd == "szp1":
                    start_time = time.time()
                    Signalwunsch = SZP_builder(start_time,Signaldef_SZP1)
                elif cmd == "h":
                    for signal in OCIT_codes.keys():
                        print(signal, OCIT_codes[signal])
                    print("test")
                    print("SZP_1")
                    Signalwunsch = "dunkel"
                else:
                    print("Kein gültiges Signal\nTippe h für Hilfe")
                    Signalwunsch = "dunkel"
            elif cmd == "test":
                    Signalwunsch = OCIT_signals[str(test_routine_1(start_time, Signaldauer, OCIT_signals))]
            elif cmd == "szp1":
                Signalwunsch = SZP_builder(start_time, Signaldef_SZP1)
            signal_wish_queue.put(Signalwunsch)

            time.sleep(0.15)  # Warte, bevor das Intervall erneut geändert wird -> Die Zeitkonstante funktioniert aktuell nicht