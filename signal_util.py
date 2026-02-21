import csv

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

if __name__ == "__main__":
    csv_OCIT_file_path = 'OCIT_def.csv'
    OCIT_def_inst = OCIT_def(file_path=csv_OCIT_file_path)
    for OCIT_dict in OCIT_def_inst.dict_list:
        print(OCIT_dict)