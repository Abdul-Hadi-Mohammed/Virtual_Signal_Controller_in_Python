import xml.etree.ElementTree as ET
import time
import sys
import csv
import tkinter as tk
import threading
import queue
import re
try:
    import msvcrt
    use_keyboard = True
except ImportError:
    use_keyboard = False

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.schlothauer.de/OMTC/LStg_Versorgung'}
    
    data = {
        'stages': [],
        'programs': {},
        'intergreen_times': {}
    }
    
    phases = root.findall('.//ns:Phase', ns)
    for phase in phases:
        stage_name = phase.findtext('ns:Bezeichnung', namespaces=ns)
        signals = {}
        
        elements = phase.findall('ns:PhasenElementeintrag', ns)
        for element in elements:
            signal = element.findtext('ns:Signalgruppe', namespaces=ns)
            state = element.findtext('ns:Signalbild', namespaces=ns)
            if signal and state:
                signals[signal] = state
        
        if signals:
            data['stages'].append({'name': stage_name, 'signals': signals})
    
    programs = root.findall('.//ns:Signalprogramm', ns)
    for program in programs:
        name = program.findtext('ns:Bezeichnung', namespaces=ns)
        timings = {}
        
        rows = program.findall('ns:SPZeile', ns)
        for row in rows:
            signal = row.findtext('ns:Signalgruppe', namespaces=ns)
            if not signal:
                continue
            
            switches = row.findall('ns:Schaltzeit', ns)
            for switch in switches:
                if switch.findtext('ns:ZielSignalbild', namespaces=ns) == 'gruen':
                    time_point = switch.findtext('ns:Schaltzeitpunkt', namespaces=ns)
                    if time_point:
                        timings[signal] = int(float(time_point))
                    break
        
        data['programs'][name] = timings
    
    matrix = root.find('.//ns:SicherheitsZwischenzeitenmatrix', ns)
    if matrix is not None:
        entries = matrix.findall('ns:ZwiZt', ns)
        for entry in entries:
            from_sig = entry.findtext('ns:Raeumer', namespaces=ns)
            to_sig = entry.findtext('ns:Einfahrer', namespaces=ns)
            time_val = entry.findtext('ns:T', namespaces=ns)
            
            if from_sig and to_sig and time_val:
                if from_sig not in data['intergreen_times']:
                    data['intergreen_times'][from_sig] = {}
                data['intergreen_times'][from_sig][to_sig] = int(float(time_val))
    
    return data


class Controller:
    def __init__(self, data):
        self.all_stages = data['stages']  # All 5 stages from XML
        self.programs = data['programs']
        self.intergreens = data['intergreen_times']  # Safety matrix from XML
        
        self.program_names = list(self.programs.keys())
        self.current_program = self.program_names[0] if self.program_names else None
        
        # Initialize signal visualization
        self.signal_queues = {}  # Will store queues for each signal group
        
        self.stage_sequences = {}
        for prog in self.program_names:
            self.stage_sequences[prog] = self._parse_stage_sequence(prog)
        
        self.active_stages = self.stage_sequences[self.current_program]
        self.current_stage_index = 0  # Index in active_stages list
        
        self.time_in_stage = 0
        self.stage_duration = 60  # Each stage runs for 60 seconds
        self.switch_window_start = int(self.stage_duration * 0.90)  # Last 10% (6 seconds)
        
        self.pending_program_switch = None
        self.switch_requested_at_step = None
        
        self.in_transition = False
        self.transition_phase = None  # 'yellow', 'all_red', 'red_yellow'
        self.transition_time_remaining = 0
        self.next_stage_idx = None
        
        self.yellow_duration = 3  # Termination: GREEN → YELLOW → RED
        self.red_yellow_duration = 1  # Initiation: RED → RED-YELLOW → GREEN
        
        if self.all_stages:
            self.signals = list(self.all_stages[0]['signals'].keys())
            current_stage = self.all_stages[self.active_stages[0]]
            self.current_state = current_stage['signals'].copy()
            
            # Initialize visualization for each signal
            for signal in self.signals:
                color_switch_interval_queue, signal_wish_queue = init_signal_vis(f"Signal {signal}")
                self.signal_queues[signal] = {
                    'interval': color_switch_interval_queue,
                    'wish': signal_wish_queue
                }
                # Set initial state
                signal_wish_queue.put(self.current_state.get(signal, 'dunkel'))
        else:
            self.signals = []
            self.current_state = {}
    
    def _parse_stage_sequence(self, program_name):
        import re
        match = re.search(r'\((\d+(?:-\d+)*)\)', program_name)
        if match:
            return [int(x) - 1 for x in match.group(1).split('-')]
        return list(range(len(self.all_stages)))
    
    def translate(self, color):
        colors = {
            'gruen': 'GREEN',
            'rot': 'RED',
            'gelb': 'YELLOW',
            'dunkel': 'DARK',
            'rotgelb': 'ROTGELB'  # Red-Yellow phase
        }
        return colors.get(color.lower(), color.upper())
    
    def display(self, step):
        current_stage_idx = self.active_stages[self.current_stage_index]
        stage = self.all_stages[current_stage_idx]
        stage_num = current_stage_idx + 1
        stage_pos = f"{self.current_stage_index + 1}/{len(self.active_stages)}"
        
        transition_info = ""
        if self.in_transition:
            transition_info = f" [TRANSITION: {self.transition_phase.upper()} {self.transition_time_remaining}s]"
        
        print(f"\n[Step {step:03d}] STP: {self.current_program} | Stage {stage_num}: {stage['name']} ({stage_pos}) | Time: {self.time_in_stage}/{self.stage_duration}s{transition_info}")
        
        signal_display = []
        for signal in sorted(self.signals):
            color = self.current_state.get(signal, 'UNKNOWN')
            eng = self.translate(color)
            icon = {'GREEN': '\U0001F7E2', 'RED': '\U0001F534', 'YELLOW': '\U0001F7E1', 'DARK': '\U000026AB', 'ROTGELB': '\U0001F7E0'}.get(eng, '\U000026AA')
            signal_display.append(f"{signal}:{icon}")
        
        print("Signals: " + " | ".join(signal_display))
        
        if self.pending_program_switch:
            print(f"\U000026A0  STP SWITCH PENDING: Will change to '{self.pending_program_switch}' at end of stage")
    
    def request_program_switch(self, program_name):
        if program_name not in self.programs:
            print(f"\n\U0000274C Error: Program '{program_name}' not found!")
            return False
        
        if program_name == self.current_program:
            print(f"\n\U000026A0  Already on program: {program_name}")
            return False
        
        if self.time_in_stage < self.switch_window_start:
            time_until_window = self.switch_window_start - self.time_in_stage
            print(f"\n\U000023F3 Switch request queued for: {self.current_program} → {program_name}")
            print(f"   Safe switching window opens in {time_until_window}s")
            self.pending_program_switch = program_name
            self.switch_requested_at_step = self.time_in_stage
        else:
            self.pending_program_switch = program_name
            time_until_switch = self.stage_duration - self.time_in_stage
            print(f"\n\U00002713 STP SWITCH WILL OCCUR: {self.current_program} → {program_name}")
            print(f"   Will switch at end of stage (in {time_until_switch}s)")
        
        return True
    
    def advance(self, step):
        if self.in_transition:
            self.transition_time_remaining -= 1
            if self.transition_time_remaining <= 0:
                self._complete_transition_phase()
            return
        
        self.time_in_stage += 1
        
        if self.time_in_stage == self.switch_window_start and self.pending_program_switch:
            print(f"\n\U0001F7E2 SAFE SWITCHING WINDOW OPEN: {self.stage_duration - self.time_in_stage}s remaining")
        
        if self.time_in_stage >= self.stage_duration:
            if self.pending_program_switch:
                self.switch_program()
            
            self._start_stage_transition()
    
    def switch_program(self):
        old_program = self.current_program
        self.current_program = self.pending_program_switch
        self.pending_program_switch = None
        
        self.active_stages = self.stage_sequences[self.current_program]
        self.current_stage_index = 0  # Start at first stage of new STP
        
        print(f"\n{'='*60}")
        print(f"\U0001F504 STP SWITCHED: {old_program} → {self.current_program}")
        print(f"   New stage sequence: {[i+1 for i in self.active_stages]}")
        print(f"{'='*60}")
    
    def change_stage(self):
        old_idx = self.active_stages[self.current_stage_index]
        self.current_stage_index = (self.current_stage_index + 1) % len(self.active_stages)
        new_idx = self.active_stages[self.current_stage_index]
        
        old = self.all_stages[old_idx]
        new = self.all_stages[new_idx]
        
        print(f"\n{'*'*60}")
        print(f"STAGE CHANGE COMPLETE: {old['name']} → {new['name']}")
        
        for signal in self.signals:
            old_color = old['signals'].get(signal)
            new_color = new['signals'].get(signal)
            
            if old_color != new_color:
                print(f"   {signal}: {self.translate(old_color)} → {self.translate(new_color)}")
        
        print(f"{'*'*60}")
        
        self.current_state = new['signals'].copy()
        
        for signal in self.signals:
            if signal in self.signal_queues:
                try:
                    self.signal_queues[signal]['wish'].put(self.current_state.get(signal, 'dunkel'))
                except:
                    pass
        
        self.time_in_stage = 0
        self.switch_requested_at_step = None
    
    def _start_stage_transition(self):
        old_idx = self.active_stages[self.current_stage_index]
        next_stage_index = (self.current_stage_index + 1) % len(self.active_stages)
        self.next_stage_idx = self.active_stages[next_stage_index]
        
        old_stage = self.all_stages[old_idx]
        new_stage = self.all_stages[self.next_stage_idx]
        
        print(f"\n{'~'*60}")
        print(f"\U000026A1 STARTING TRANSITION: {old_stage['name']} → {new_stage['name']}")
        print(f"{'~'*60}")
        
        self.in_transition = True
        self.transition_phase = 'yellow'
        self._apply_yellow_phase(old_stage, new_stage)
        
    def _apply_yellow_phase(self, old_stage, new_stage):
        self.transition_time_remaining = self.yellow_duration
        
        print(f"\U0001F7E1 Phase 1: YELLOW (Termination) - {self.yellow_duration}s")
        for signal in self.signals:
            old_color = old_stage['signals'].get(signal)
            new_color = new_stage['signals'].get(signal)
            
            if old_color == 'gruen' and new_color == 'rot':
                self.current_state[signal] = 'gelb'
                print(f"   {signal}: GREEN → YELLOW")
                # Update visualization
                if signal in self.signal_queues:
                    try:
                        self.signal_queues[signal]['wish'].put('gelb')
                    except:
                        pass
    
    def _complete_transition_phase(self):
        old_idx = self.active_stages[self.current_stage_index]
        old_stage = self.all_stages[old_idx]
        new_stage = self.all_stages[self.next_stage_idx]
        
        if self.transition_phase == 'yellow':
            self._apply_all_red_phase(old_stage, new_stage)
            
        elif self.transition_phase == 'all_red':
            self._apply_red_yellow_phase(old_stage, new_stage)
            
        elif self.transition_phase == 'red_yellow':
            self.in_transition = False
            self.transition_phase = None
            self.change_stage()
    
    def _apply_all_red_phase(self, old_stage, new_stage):
        print(f"\U0001F534 Phase 2: ALL-RED (Clearance)")
        
        for signal in self.signals:
            old_color = old_stage['signals'].get(signal)
            if old_color == 'gruen':
                self.current_state[signal] = 'rot'
                print(f"   {signal}: YELLOW → RED")
                if signal in self.signal_queues:
                    try:
                        self.signal_queues[signal]['wish'].put('rot')
                    except:
                        pass
        
        max_clearance = 0
        for from_signal in self.signals:
            if old_stage['signals'].get(from_signal) == 'gruen':
                for to_signal in self.signals:
                    if new_stage['signals'].get(to_signal) == 'gruen':
                        if from_signal in self.intergreens:
                            if to_signal in self.intergreens[from_signal]:
                                clearance = self.intergreens[from_signal][to_signal]
                                max_clearance = max(max_clearance, clearance)

        self.transition_time_remaining = max(max_clearance, 2)
        self.transition_phase = 'all_red'
        print(f"   Clearance time: {self.transition_time_remaining}s (from intergreen matrix)")
    
    def _apply_red_yellow_phase(self, old_stage, new_stage):
        self.transition_time_remaining = self.red_yellow_duration
        self.transition_phase = 'red_yellow'
        
        print(f"\U0001F7E0 Phase 3: RED-YELLOW (Initiation) - {self.red_yellow_duration}s")
        for signal in self.signals:
            old_color = old_stage['signals'].get(signal)
            new_color = new_stage['signals'].get(signal)
            
            if old_color == 'rot' and new_color == 'gruen':
                self.current_state[signal] = 'rotgelb'
                print(f"   {signal}: RED → RED-YELLOW")
                if signal in self.signal_queues:
                    try:
                        self.signal_queues[signal]['wish'].put('rotgelb')
                    except:
                        pass
    
    def show_available_programs(self):
        print(f"\n{'='*60}")
        print("AVAILABLE SIGNAL TIME PLANS (STPs):")
        print(f"{'='*60}")
        for idx, name in enumerate(self.program_names, 1):
            marker = "◄ ACTIVE" if name == self.current_program else ""
            print(f"  {idx}. {name} {marker}")
        print(f"{'='*60}")
    
    def run(self, seconds):
        print(f"\n{'#'*60}")
        print(f"TRAFFIC SIGNAL SIMULATION")
        print(f"{'#'*60}")
        print(f"Duration: {seconds} steps = {seconds} seconds")
        print(f"Stage duration: {self.stage_duration} seconds per stage")
        print(f"Starting STP: {self.current_program}")
        print(f"Stage sequence: {[i+1 for i in self.active_stages]}")
        print(f"{'#'*60}")
        
        self.show_available_programs()
        
        for step in range(1, seconds + 1):
            if use_keyboard and msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in ['1', '2', '3']:
                    idx = int(key) - 1
                    if 0 <= idx < len(self.program_names):
                        self.request_program_switch(self.program_names[idx])
            
            self.display(step)
            self.advance(step)
            time.sleep(1)
        
        print(f"\n{'#'*60}")
        print(f"\U00002713 SIMULATION COMPLETE - {seconds} steps finished")
        print(f"{'#'*60}")


class OCIT_def:
    def __init__(self, file_path):
        self.indexToName = {}
        self.nameToCode = {}
        self.codeToName = {}
        self.NameToASCII = {}
        self.ASCIIToName = {}
        self.codeToASCII = {}
        self.ASCIIToCode = {}
        self.dict_list = [
            self.indexToName,
            self.nameToCode,
            self.codeToName,
            self.NameToASCII,
            self.ASCIIToName,
            self.codeToASCII,
            self.ASCIIToCode,
        ]

        with open(file_path, mode='r', newline='', encoding='utf-8') as csv_OCIT_def:
            reader = csv.reader(csv_OCIT_def, delimiter=';')
            for row in reader:
                self.indexToName[row[0]] = row[1]
                self.nameToCode[row[1]] = row[2]
                self.codeToName[row[2]] = row[1]
                self.NameToASCII[row[1]] = row[3]
                self.ASCIIToName[row[3]] = row[1]
                self.codeToASCII[row[2]] = row[3]
                self.ASCIIToCode[row[3]] = row[2]


class TrafficLightApp:
    def __init__(self, window, name, switch_interval_queue, signal_wish_queue):
        scal = 0.75
        self.window = window
        self.window.title(name)

        self.width = scal * (65 + 200 + 65)
        self.height = scal * (65 + (200 + 35) * 2 + 200 + 65)
        self.canvas = tk.Canvas(window, width=self.width, height=self.height, bg='black')
        self.canvas.pack()

        self.colors = {
            "rot": '#B81B0E',
            "gelb": '#F5A900',
            "gruen": '#339966',
            "weiß": '#FFFFFF',
            "aus": '#4D4D4D',
        }

        self.signal_wish_queue = signal_wish_queue
        self.signal_patterns = {
            "rot": [1, 0, 0, 0, 0],
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

        self.switch_interval_queue = switch_interval_queue
        self.current_interval = 10

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

        self.freq_val = False
        self.wbl_val = "dunkel"

        self.update_light()
        print(f"Initializing signal vis for {name}- Done")

    def update_light(self):
        try:
            self.current_interval = self.switch_interval_queue.get()
        except:
            pass

        try:
            self.signal_wish = self.signal_wish_queue.get()
        except queue.Empty:
            self.signal_wish = 'dunkel'
        if not self.signal_wish_controll == self.signal_wish:
            print(f'Signalbild: {self.signal_wish}')
            self.signal_wish_controll = self.signal_wish

        for light in self.lights.values():
            self.canvas.itemconfig(light, fill=self.colors["aus"])

        var = self.signal_patterns[self.signal_wish]
        rot = bool(var[0])
        gelb = bool(var[1])
        gruen = bool(var[2])
        freq = int(var[3])
        wbl = bool(var [4])

        if freq > 0:
            self.current_interval = int(1000/(freq*2))
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

    thread = threading.Thread(target=run_traffic_light_app, args=(name, color_switch_interval_queue,signal_wish_queue))
    thread.daemon = True
    thread.start()
    print(f"Initializing signal vis for {name}")

    return color_switch_interval_queue, signal_wish_queue


if __name__ == '__main__':
    print("Loading XML file...")
    data = parse_xml('z1_fg311.xml')
    print(f"\U00002713 Found {len(data['stages'])} total stages")
    print(f"\U00002713 Found {len(data['programs'])} signal time plans (STPs)")
    
    print("\nStarting traffic controller...")
    controller = Controller(data)
    controller.run(180)
