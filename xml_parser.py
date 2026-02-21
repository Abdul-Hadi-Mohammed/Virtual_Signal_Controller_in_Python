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
    if matrix:
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