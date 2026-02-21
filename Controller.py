class Controller:
    def __init__(self, data):
        self.all_stages = data['stages']  # All 5 stages from XML
        self.programs = data['programs']
        self.intergreens = data['intergreen_times']  # Safety matrix from XML
        
        self.program_names = list(self.programs.keys())
        self.current_program = self.program_names[0] if self.program_names else None
        
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