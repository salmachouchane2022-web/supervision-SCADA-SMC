#  SCADA Industrial Supervision System

### Python / PyQt5 / Siemens S7 / Snap7

> **Industrial SCADA dashboard for real-time supervision of an automated assembly line**


##  Overview

This project is an **industrial SCADA supervision application** developed in Python for monitoring an automated assembly line.

The application provides a real-time graphical representation of the production system, including:

*  Production stations
*  Industrial robots
*  Turning table
*  Loading and unloading operations
*  Station cycle status
*  Equipment states
   Operating and fault conditions
*  Real-time PLC data

The system communicates with a **Siemens S7 PLC** using the **S7 communication protocol** through the `python-snap7` library.

The graphical supervision interface is developed with **PyQt5**.


#  Project Objectives

The main objectives of this project are:

1. Establish communication between a Python application and a Siemens PLC.
2. Read process variables from the PLC in real time.
3. Decode PLC data such as `BOOL` and `INT` values.
4. Display industrial equipment states through a graphical SCADA interface.
5. Provide a clear and intuitive dashboard for operators and engineers.
6. Support testing with a real PLC or a simulated PLC environment.
7. Separate PLC communication from the graphical user interface.


#  System Architecture

The application follows a modular architecture where the PLC communication layer is separated from the graphical interface.

                    ┌─────────────────────────┐
                    │       Siemens PLC       │
                    │        S7-1200          │
                    │                         │
                    │   Process Variables     │
                    │        DB / I/O         │
                    └────────────┬────────────┘
                                 │
                                 │ S7 Protocol
                                 │ Ethernet TCP/IP
                                 ▼
                    ┌─────────────────────────┐
                    │  mod_communication.py   │
                    │                         │
                    │ • PLC connection        │
                    │ • DB reading            │
                    │ • BOOL decoding         │
                    │ • INT decoding          │
                    │ • Error handling        │
                    └────────────┬────────────┘
                                 │
                                 │ Python data
                                 ▼
                    ┌─────────────────────────┐
                    │        dashboard.py     │
                    │                         │
                    │      PyQt5 GUI          │
                    │                         │
                    │ • Stations              │
                    │ • Robots                │
                    │ • Turning Table         │
                    │ • Loading / Unloading   │
                    │ • Cycle information     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     SCADA DASHBOARD      │
                    │                         │
                    │ Real-time visualization │
                    └─────────────────────────┘


#  Project Structure

supervision-SCADA-SMC/
│
├── dashboard.py
├── mod_communication.py
├── requirements.txt
├── README.md
├── image.png             # HMI/SCADA mockup or screenshot


#  Main Files

## `dashboard.py`

Main application file responsible for the SCADA graphical interface.

It manages:

* PyQt5 application window
* SCADA dashboard
* Station widgets
* Robot visualization
* Turning table visualization
* Loading / unloading indicators
* Cycle indicators
* Equipment status
* Real-time GUI updates


## `mod_communication.py`

Communication layer between the Python application and the Siemens PLC.

Main responsibilities:

* Establish PLC connection
* Disconnect from PLC
* Read PLC Data Blocks
* Decode `BOOL` variables
* Decode `INT` variables
* Provide structured data to the GUI
* Handle communication errors
* Manage reconnection attempts
* Prevent communication errors from crashing the GUI

This separation makes the application easier to maintain and debug.


#  Technologies

| Technology      | Purpose                       |
| --------------- | ----------------------------- |
| Python 3        | Main programming language     |
| PyQt5           | Graphical SCADA interface     |
| python-snap7    | Siemens S7 communication      |
| Siemens S7      | Industrial PLC                |
| TIA Portal      | PLC programming/configuration |
| PLCSIM Advanced | PLC simulation                |
| Ethernet TCP/IP | Network communication         |
| VS Code         | Development environment       |


#  Requirements

The project requires:

* Python 3.x
* PyQt5
* python-snap7

Dependencies are listed in:

```text
requirements.txt
```

Install them with:

```bash
pip install -r requirements.txt
```

---

#  Installation

## 1. Clone the repository

```bash
git clone https://github.com/salmachouchane2022-web/supervision-SCADA-SMC.git
```

Then:

```bash
cd YOUR_REPOSITORY
```

---

## 2. Create a virtual environment

On Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

On Linux/macOS:

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

Verify the installation:

```bash
pip show PyQt5
```

and:

```bash
pip show python-snap7
```


#  PLC Communication

The SCADA application communicates with the Siemens PLC through the S7 protocol.

The general communication path is:

```text
Python
   │
   ▼
python-snap7
   │
   ▼
S7 Protocol
   │
   ▼
Ethernet TCP/IP
   │
   ▼
Siemens PLC
```

The PLC connection parameters must be configured according to the actual PLC installation.

Typical parameters include:

```text
PLC IP Address
Rack
Slot
DB Number
DB Size
```

Example:

```python
PLC_IP = "192.168.0.10"

RACK = 0
SLOT = 1
```

>  The IP address, rack, slot and DB configuration must match the actual PLC configuration in TIA Portal.


#  PLC Data Block

The SCADA application reads process information from the PLC Data Block.

The project currently uses a dedicated DB for the supervision variables.

Example:

```text
DB620
```

The Data Block contains information related to:

* Station states
* Loading status
* Unloading status
* Robot states
* Turning table conditions
* Cycle information
* Other process signals

The exact addresses must correspond to the PLC program.


#  Data Processing

The communication module reads raw PLC data and converts it into usable Python values.

Example concept:

```text
PLC DB
   │
   ├── BOOL
   ├── BOOL
   ├── INT
   ├── BOOL
   └── INT
        │
        ▼
mod_communication.py
        │
        ▼
Python dictionary
        │
        ▼
dashboard.py
        │
        ▼
SCADA widgets
```

This architecture avoids putting PLC communication logic directly inside the graphical interface.


#  Robot Supervision

The dashboard provides visual information about robot states.

Depending on the PLC signals, the interface can represent states such as:

```text
RUNNING
STOPPED
DONE
WAITING
ERROR
```

The exact interpretation of `TRUE` and `FALSE` depends on the PLC signal mapping.

Therefore, the PLC variable definition must always be checked before modifying the visualization logic.


#  Turning Table Logic

The Turning Table follows the production sequence defined by the PLC.

The table is allowed to rotate only when the required process conditions are satisfied.

Typical conditions include:

```text
Station 1 finished
        +
Station 2 finished
        +
Loading Passed
        +
Unloading Passed
        │
        ▼
Turning Table allowed to rotate
```

Otherwise:

```text
Condition not satisfied
        │
        ▼
Turning Table PAUSED / WAITING
```

This prevents the table from rotating while one of the required production operations is still active.


#  Loading / Unloading

The SCADA interface displays the status of loading and unloading operations.

Typical signals include:

```text
LOADING
LOADING PASSED

UNLOADING
UNLOADING PASSED
```

These signals are obtained directly from the PLC.

The dashboard uses them to provide the operator with a visual representation of the production sequence.


#  Cycle Monitoring

The SCADA dashboard can display cycle-related information for the production stations.

The objective is to provide operators and engineers with a quick overview of:

* Current station status
* Cycle progress
* Completed operations
* Waiting conditions
* Production sequence



#  Simulation with PLCSIM Advanced

The application can be tested without a physical PLC using **Siemens PLCSIM Advanced**, provided that the simulation is configured to expose the PLC communication interface required by the application.

The test architecture is:

```text
TIA Portal
     │
     ▼
PLC Program
     │
     ▼
PLCSIM Advanced
     │
     ▼
Virtual PLC
     │
     │ Ethernet / S7
     ▼
python-snap7
     │
     ▼
mod_communication.py
     │
     ▼
dashboard.py
     │
     ▼
SCADA Dashboard
```

Before launching the SCADA application, verify:

* PLCSIM Advanced is running
* The virtual CPU is correctly configured
* The PLC program has been downloaded
* The simulated CPU is in `RUN`
* The virtual network is correctly configured
* The PLC IP address is reachable
* The required DB exists
* The DB variables are accessible


#  Network Test

Before testing the Python application, verify basic network connectivity.

Windows:

```bash
ping 192.168.0.10
```

Replace the address with the actual PLC IP address.

A successful ping confirms basic IP connectivity.

However:

>  A successful ping does not guarantee that S7 communication is correctly configured.

The following parameters must also be verified:

```text
PLC IP
Rack
Slot
S7 communication
DB number
DB size
PLC access configuration
```


#  Running the Application

After configuring the PLC connection, run:

```bash
python dashboard.py
```

The SCADA dashboard should start and begin displaying the PLC process information.


#  Troubleshooting

##  Python cannot connect to the PLC

Check:

```text
1. PLC IP address
2. Ethernet connection
3. PLC state
4. Rack
5. Slot
6. Firewall
7. S7 communication
8. PLCSIM Advanced configuration
```


##  Ping works but Snap7 does not connect

A successful ping only verifies network-level connectivity.

Check:

```text
Rack
Slot
PLC configuration
S7 communication
PLC access settings
PLCSIM Advanced configuration
```


##  Dashboard starts but values do not update

Check:

```text
DB number
DB size
Variable addresses
BOOL offsets
INT offsets
PLC program
Communication update cycle
```


##  Application freezes during PLC communication

The communication module should handle connection/read errors without blocking the graphical interface.

Check:

```text
Connection timeout
Read timeout
PLC availability
Network configuration
Reconnection logic
```


#  Safety and Industrial Considerations

This project is intended primarily for **supervision and monitoring**.

Before connecting the application to a production PLC:

* Verify all PLC addresses.
* Verify the meaning of every signal.
* Test the application in simulation first.
* Do not write to PLC variables unless explicitly required.
* Validate all commands with the automation engineer.
* Avoid using experimental code directly on a production system.

The SCADA application should not replace the PLC's safety system or emergency-stop architecture.


#  Development Recommendations

For future development, the project can be extended with:

*  Production statistics
*  OEE / TRS monitoring
*  Alarm history
*  Historical data storage
*  Production reports
*  User authentication
*  Alarm notifications
*  OPC UA communication
*  SQL database
*  Grafana integration
*  Multi-line supervision
*  Automatic PLC reconnection
*  Event logging


#  Possible Future Architecture

A more advanced version could use:

```text
                  ┌──────────────────┐
                  │   Siemens PLC    │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Communication    │
                  │ Layer            │
                  │ Snap7 / OPC UA   │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌──────────────┐         ┌──────────────┐
       │ SCADA        │         │ Database     │
       │ PyQt5        │         │ SQL/InfluxDB │
       └──────┬───────┘         └──────┬───────┘
              │                        │
              ▼                        ▼
       ┌──────────────┐         ┌──────────────┐
       │ Operator     │         │ Historical   │
       │ Dashboard    │         │ Analytics    │
       └──────────────┘         └──────────────┘


#  Configuration Checklist

Before starting the application:

```text
[ ] Python installed
[ ] Virtual environment created
[ ] requirements.txt installed
[ ] PLC IP configured
[ ] Rack configured
[ ] Slot configured
[ ] DB number verified
[ ] DB size verified
[ ] PLC program downloaded
[ ] PLC in RUN
[ ] Network connection verified
[ ] Required PLC variables verified
[ ] SCADA application started
```

#  Example `requirements.txt`

```text
PyQt5
python-snap7
```

Install with:

```bash
pip install -r requirements.txt
```



#  Author

**Salma Chouchane**

Industrial Automation / Computer Science

Project developed as part of an industrial internship/project involving:

* Industrial automation
* PLC programming
* SCADA supervision
* Python development
* Industrial communication
* Siemens systems


#  License

This project is intended for educational, development and industrial supervision purposes.

Before deploying the software in a production environment, the PLC communication, process logic and safety requirements must be fully validated.


#  Project

If this project is useful to you, consider giving the repository a ⭐ on GitHub.

**SCADA Industrial Supervision System**
Python • PyQt5 • Snap7 • Siemens PLC • Industrial Automation
