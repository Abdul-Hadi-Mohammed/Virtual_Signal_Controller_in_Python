 **Virtual Signal Controller in Python**

A Python-based Virtual Signal Controller (VSC) that executes real-world traffic signal logic exported from LISA+ XML files.
The project simulates a German traffic signal controller in real time, including intergreens, conflict handling, and safe signal time plan (STP) switching.

**Project Overview**
- This project was developed as part of a research module.
- The goal is to create a transparent and programmable execution layer for traffic signal logic defined in LISA+.
- Instead of running inside a closed system, the signal logic is executed step-by-step in Python, allowing full visibility, experimentation, and future extensions.
- The controller follows German traffic signal standards based on FGSV guidelines (RiLSA).

**Example Intersection**

Intersection 311 (Planitzer Straße – Breithauptstraße), Zwickau, Germany

The XML file exported from LISA defines:
- Signal groups (vehicles & pedestrians)
- Conflict matrix (safety rules)
- Intergreen times (clearance intervals)
- 3 Signal Time Plans (STP 1, STP 2, STP 3)

**Key Features**

✅ XML-based signal logic execution

✅ Stage-based state machine

✅ Green → Amber → Red transitions

✅ Red → Red-Amber → Green initiation

✅ Intergreen (all-red) safety clearance

✅ Conflict matrix enforcement

✅ Interactive STP switching (keys 1, 2, 3)

✅ Safe Switching Window (90% stage rule)

✅ Real-time GUI visualization (Tkinter)

✅ Modular and extensible architecture

**Project Architecture**

The system is modular and consists of:

1️⃣ The Rulebook

z1_fg311.xml
- Exported from LISA
- Contains signal groups, STPs, conflict matrix

2️⃣ The Translator

xml_parser.py
- Reads and converts XML data into Python structures

3️⃣ The Brain

Controller.py
- Executes stage logic
- Manages timing and transitions
- Handles safe STP switching

4️⃣ The Connector

main.py
- Runs controller & GUI in parallel (multithreading)
- Handles keyboard interaction

5️⃣ The Face

signal_vis.py
- Visualizes traffic lights using Tkinter

6️⃣ The Dictionary

OCIT_def.csv + signal_util.py
- Maps OCIT codes to signal colors

**Simulation Modes**

Fixed-Time Simulation

Interactive Simulation (manual STP switching)

Press:

1 → STP 1

2 → STP 2

3 → STP 3

Switching occurs only within a Safe Switching Window (90% rule) to ensure stable and realistic traffic behavior.

**Safety Implementation**

- Strict conflict matrix enforcement
- Intergreen (all-red) clearance phase
- Stage-based deterministic control
- No conflicting greens allowed
- Minimum one full cycle after STP switch

**Technologies Used**

- Python
- AI Copilot
- Tkinter
- Multithreading
- XML parsing
- OCIT protocol structure
- LISA+ XML export

**References**

- RiLSA – German Signal Control Guidelines
- LISA+ (Signal Planning Software)
- OCIT-O Standard

**Authors**

Abdul Hadi Mohammed

Rahil Asit Malviya
