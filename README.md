# AAS Agent

The AAS Agent is an event-driven runtime component that extends a static Asset Administration Shell (AAS), such as an Eclipse BaSyx server, with dynamic behavior.

**Already available:**
- AAS Type 1 functionality (static data representation) with [Eclipse BaSyx™](https://basyx.org/) ([BaSyx Java Version 2](https://wiki.basyx.org/en/latest/content/user_documentation/basyx_components/v2/index.html) or [BaSyx Go](https://github.com/eclipse-basyx/basyx-go-components))

**It enables:**
- AAS Type 2 functionality (live data integration) by reacting to incoming data streams (e.g. via AAS, fieldbuses or directly connected sensors)
- AAS Type 3 functionality (active operations) by executing domain-specific actions based on AAS state changes

The agent continuously monitors AAS-related events and maps them to executable operations.

---

## Why use an AAS Agent?

While platforms like [Eclipse BaSyx™](https://basyx.org/) provide a solid foundation for managing AAS data (Type 1), they do not natively support reactive or autonomous behavior.

The AAS Agent is an exemplary implementation to close this gap through the introduction of:

- Reactive processing of AAS changes
- Automated execution of operational routines

This turns a passive digital model (Type 1) not only into a digital shadow (Type 2) but into an active digital twin (Type 3).

---

## Software Architecture

<p align="center">
  <img src="docs/images/SoftwareArchitektur.png" alt="Software Architecture" />
</p>

---

## Class Diagram

<p align="center">
  <img src="docs/images/UML_aas_agent.png" alt="UML AAS Agent" />
</p>

---

## Installation and Usage

### Prerequisites

- A running AAS server (e.g. [Eclipse BaSyx](https://basyx.org/))

---

### 1. Install `uv`

Follow the official installation guide: [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/)

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify your installation:
```bash
uv --version
# Expected output: uv 0.10.8 or similar
```

> **Note:** Make sure the `uv` binary is available in your `PATH`.

---

### 2. Clone the Repository

**Using Git:**
```bash
git clone https://github.com/Crauder00/Aas_Agent.git
cd AAS_AGENT
```

**Linux (without Git, via release archive):**
```bash
mkdir AAS_AGENT && cd AAS_AGENT
curl -L -O https://github.com/Crauder00/Aas_Agent/releases/download/<version>/<release-file>.zip
unzip <release-file>.zip
```
> **Note:** Replace `<version>` and `<release-file>` with the actual values from the [Releases page](https://github.com/Crauder00/Aas_Agent/releases).

---

### 3. Install Dependencies

Inside the `AAS_AGENT` folder, run:

```bash
uv sync --no-dev
```

---

### 4. Configure the Agent

Open `main.py` and adjust the configuration to your environment, or integrate the configuration block into your own application.

All available configuration options are located in:
AAS_AGENT/aas_agent/config/
> **Note:** You do not need to modify the config files directly — all options can be set via `main.py`.

---

### Configuring MQTT or polling

Create the service instances first, then bind their registered operation paths to
an explicit repository and submodel using `watches`:

```python
from aas_agent import (
    AasAgent, AgentConfig, EmissionService, ListenerConfig, SubmodelWatch,
)

# Define emission_config_station_0 and emission_config_station_1 as in main.py.
services = [
    EmissionService(emission_config_station_0),
    EmissionService(emission_config_station_1),
]

agent_config = AgentConfig(
    listener=ListenerConfig(
        mode="mqtt",
        host=MQTT_HOST,
        watches=[
            SubmodelWatch(
                base_url=LOCAL_AAS,
                submodel_id=CF_SUBMODEL_ID,
                services=services,
            ),
        ],
    ),
)
agent = AasAgent(agent_config, services)
agent.start()
# Keep the application running, then call agent.stop() on shutdown.
```

- `base_url` is the REST repository URL accessible from the agent.
- `submodel_id` is the plain submodel ID, not Base64 encoded.
- `services` contains the same instances passed to `AasAgent`. Their registered
  paths determine which values are watched; submodels are not inferred from services.
- Add another `SubmodelWatch` for each additional repository/submodel. Group services
  watching the same repository/submodel in a single watch.
- Optional `event_source` matches the CloudEvent `source` exactly when multiple
  repositories publish the same submodel ID. REST requests still use `base_url`.
- Optional `operation_topics` selects exact, case-sensitive registered operation
  paths from the watch's services. Omit it (or use `None`) to watch all their
  registered paths. Empty lists and unknown paths are rejected at startup.

One service can react to different paths in multiple submodels. Reuse the same
service instance and select the paths belonging to each submodel:

```python
# agv_service is an existing service instance registering these three paths.
services = [agv_service]
agent_config = AgentConfig(
    listener=ListenerConfig(
        mode="polling",
        poll_interval_seconds=1.0,
        watches=[
            SubmodelWatch(
                base_url=LOCAL_AAS,
                submodel_id="https://www.example.com/subodel/partstorage/1",
                services=services,
                operation_topics=["Red_parts", "min_number_red_parts"],
            ),
            SubmodelWatch(
                base_url=LOCAL_AAS,
                submodel_id="https://www.example.com/subodel/agv/1",
                services=services,
                operation_topics=["min_battery_allowed"],
            ),
        ],
    ),
)
agent = AasAgent(agent_config, services)
```

Each watch reads only its selected paths. Service methods remain responsible for
using the correct repository and submodel for their own REST reads and writes.

The default MQTT filter is `basyx/submodelrepository/submodel/updated` for BaSyx Go.
On a matching `io.admin-shell.submodel.updated.v1` CloudEvent, the handler reads
registered values via REST and dispatches only detected changes. For BaSyx Java,
set `topic_filter="sm-repository/+/submodels/+/submodelElements/+/updated"`.
A list of filters can subscribe to both formats.

For polling, replace the listener configuration with:

```python
ListenerConfig(
    mode="polling",
    poll_interval_seconds=1.0,
    watches=[SubmodelWatch(LOCAL_AAS, CF_SUBMODEL_ID, services)],
)
```

Polling opens no MQTT connection. In `main.py`, set `EVENT_MODE = "polling"`
and adjust `POLL_INTERVAL_SECONDS`; the interval is used only for polling.
Both modes establish an initial baseline without triggering operations, then
apply the existing `execute_when` conditions and guards to value changes.
The old `AgentConfig(mqtt=MqttConfig(...))` configuration remains supported for
Java MQTT without watches. If `listener` is supplied, it takes precedence.

---

### 5. Prepare Your AAS Server

Make sure your AAS server is running before starting the agent (e.g. Eclipse BaSyx Java V2 or BaSyx Go).

Then upload the initial asset to your server — choose one of the following approaches:

**Upload via `.aasx` file:**
Use your AAS server's UI or API to upload the provided `ES_V3.aasx` package directly.

---

### 6. Start the Agent

#### Manually (Windows)

```bash
.venv\Scripts\activate.bat
python main.py
```

#### Manually (Linux / macOS)

```bash
source .venv/bin/activate
python main.py
```

#### Automatically on Linux via systemd

Create a new service file:

```bash
sudo nano /etc/systemd/system/aas-agent.service
```

Paste the following content and adjust the paths to match your setup:

```ini
[Unit]
Description=AAS Agent
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/AAS_AGENT
ExecStart=/home/<your-user>/.local/bin/uv run --no-dev python main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

> **Note:** Replace all occurrences of `<your-user>` with your actual Linux username (e.g. `pi`).

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aas-agent.service
sudo systemctl start aas-agent.service
```

Check the status or logs:

```bash
sudo systemctl status aas-agent.service
sudo journalctl -u aas-agent.service -f
```
> **Note:** On first startup, `uv` may need to compile native dependencies from source (e.g. on ARM devices). This can take anywhere from a few seconds up to 30 minutes depending on your hardware.

---

## Extending with Custom Use Cases

Additional use cases can be added under `aas_agent/services/` as Python modules.

> **Important:** Every custom service **must** inherit from `aas_agent/core/base_operation_service.py` to ensure compatibility with the agent's execution lifecycle.

```
aas_agent/
└── services/
    ├── emission_service/ 
    ├── your_custom_service/
    │   ├── utils_for_custom_service.py
    │   └── your_custom_service.py   ← inherits from BaseOperationService
    └── ...
```

Once your service is implemented, register it in `main.py` by adding it to the `services` list and passing it to the agent:

```python
def main() -> None:
    ...

    services = [
        EmissionService(emission_config_station_0),
        EmissionService(emission_config_station_1),
        YourCustomService(your_config_0)  # Add more services if needed
    ]

    ...

    agent = AasAgent(agent_config, services)

    ...
```

---

## Periodic services (including timer-only agents)

Services can register synchronous, parameterless methods independently of event
topics. Register methods in the service constructor before passing the service
to `AasAgent`:

```python
import threading

from aas_agent import AasAgent, AgentConfig, BaseOperationService


class BatteryService(BaseOperationService):
    def __init__(self):
        super().__init__()
        self.register_periodic(
            self.read_batteries,
            interval_seconds=300,
            timing="soft",
            max_lateness_seconds=30,
        )

    def read_batteries(self):
        # Read batteries and update application state / the AAS here.
        # Use network timeouts so shutdown can finish.
        print("Reading batteries")


agent = AasAgent(AgentConfig(event_mode="disabled"), [BatteryService()])
try:
    agent.start()
    threading.Event().wait()
except KeyboardInterrupt:
    pass
finally:
    agent.stop()
```

`event_mode="disabled"` creates no MQTT listener, polling source or event handler.
The default `event_mode="enabled"` retains existing behavior. A service can use
both `register(...)` and `register_periodic(...)` when events are enabled; timer
registrations do not require a topic or a submodel watch. Intervals and timing
options can be taken from your service configuration.

### Timing and execution rules

- The first call is due **one full interval after successful event-source
  initialization** (or startup for a timer-only agent). Intervals use a monotonic
  clock and fixed-rate scheduling: a method's runtime does not shift the next
  scheduled time. This is relative scheduling, not alignment to wall-clock minutes.
- `timing="soft"`: run when idle, even if late. An optional
  `max_lateness_seconds` emits a warning when exceeded; omitting it allows any
  start delay.
- `timing="hard"`: `max_lateness_seconds` is required. A start beyond this
  tolerance logs an error and is skipped by default. Use `late_policy="run"`
  to execute anyway after logging the error. Missed ticks and busy-worker skips
  also log errors. The tolerance measures the start of the method, including
  time spent in its optional guard.
- Missed intervals are coalesced into the most recent due tick. There is no
  catch-up burst. `overlap="skip"` is the only supported overlap policy: at most
  one pending or running invocation per registration. A busy method loses that
  tick and is considered again at the next scheduled tick.
- Each registration has a dedicated worker, independent of event workers and
  other periodic operations. This consumes up to one worker thread per job.
  Exceptions in methods or guards are logged; later intervals remain scheduled.
  `guard=` accepts the same parameterless `GuardResult` guards as event operations.
- Register a method only once per service instance. Independent service instances
  have independent schedules. Guards and methods must be synchronous and callable
  without arguments. Scheduling and event calls of the same method are **not**
  mutually exclusive; use service locks if they share state.
- `stop()` prevents further scheduling, cancels queued invocations and waits for
  running methods/guards. Python threads cannot forcibly interrupt a running
  method: use bounded I/O and cooperative cancellation for long-running work.
  When called from a periodic method or guard, shutdown completes asynchronously
  on a separate thread so the callback can return without joining itself.
  A subsequent `stop()` from outside a periodic callback waits for all periodic
  workers to finish, including the callback that requested shutdown.
  Repeated `start()`/`stop()` calls are harmless, but a stopped agent cannot be
  restarted; create a new agent instead. Jobs are not persisted across restarts.

**Hard timing is deadline monitoring, not a hard real-time guarantee.** Python
threads, the OS scheduler, guards and network requests can introduce delays.
Only start deadlines are monitored; no completion deadline or forced timeout is
provided. Use a real-time controller for operations requiring guaranteed deadlines.

Run scheduler and existing watch regression tests with:

```bash
uv run python -m unittest discover -s tests -v
```

## Known Limitations

- **`registration_service`** is currently under development and not yet tested.
- **BaSyx Go adaptation is under development.** CloudEvent MQTT handling and
  configurable polling are implemented, but live integration with BaSyx Go still
  needs validation. REST endpoints and MQTT settings must match your deployment.
- Reconciliation observes current values, not a complete event history. Rapid
  changes between reads and repeated writes of the same value can be missed.
  This limitation is accepted for the current prototype.

