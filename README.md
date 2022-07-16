# IEEE 802.11ad MAC performance evaluation framework

A custom simulation framework for mimicking the behaviour of an IEEE 802.11ad network, where channel access is based on service period (SP) allocation. 
It works by scheduling data and control frame transmission airtime, enabling the extraction of MSDU latency and MAC layer throughput in various network configurations. 
The two can be used to derive M2P latency and achievable video frame size during post-processing.



## Running 

Configure `main.py`:

- Set process niceness (e.g. 10), enabling preemption by other processes on the host machine.
- Select process pool size, also limiting the number of cores used for processing.
- Redirect output to custom path if needed.
- Select the input BER data - view [BER data][ber-data] for more info.
- Set the simulation input parameters - refer to [(coming soon)][vtc-spring-paper] for their descriptions.
- Switch MSDU departure (TX) and arrival (RX) time logging on or off (`store_raw_msdu_times`).

Then run.



## Output interpretation

Output is redirected to the `log` directory by default. Within it, a subdirectory with the smallest available ID between 0 and 9999 will be automatically created every time a new simulation is run. It contains outputs from individual processess, corresponding to a single input parameter combination, and global simulation config/result files:
- `config.pkl`: Input parameters.
- `config_table.csv`: Mapping between processess and input parameter combinations.
- `mcs_table.csv`: The MCS applied to every inpur parameter combination, determined by EbNo and allowed BER.
- `msdu_latency.csv`: Latency results per process (units are nanoseconds).
- `statu_table.csv`: Status of each terminated process (successful=0, early exit=1, error=-1)
- `throughput_table.csv`: Throughput results per process (units are Gbps).



## BER data

Bit error rate (BER) data was determined using the [802.11ad PHY simulation framework][ber-simulator], descibed in [this MDPI Electronics paper][mdpi-paper]. The contained results correspond to:

- `BER-3-iter.csv`: Limiting LDPC decoding to 3 iterations.
- `BER-3-to-20-iter.csv`: Allowing between 3 and 20 LDPC decoding iterations (depending on MCS), as long as bottlenecking doesn't occur.



## Structure

A rough outline of the framework's structure is illustrated in the below figure. The employed classes and their roles are:
- `StudyExecutorDynamicDb`: Builds log directory structure and schedules simulation processes for individual input parameter combinations.
- `FastInOutStudy`: Generates MSDU timeslots. Also calculates both MSDU latency and throughput.
- `DurationGenerator`: Determines individual time slot durations, based on the input params.
- `PLog`: Saves the config, metadata, and stdout for each process in its corresponding subdirectory. Optionally, also stores raw MSDU generation (TX) and arrival (RX) times.
- `Librarian`: Listens to queue, containing individual process results, and forwards then to the `Db`.
- `Db`: In charge of mapping individual process IDs to input parameters and results (the `.csv` files).

![structure](structure.png)



### Notes

- `Db` saves data to the `log` directory. With regards to the *process log* `PLog` class, the `Db` class can be regarded as a *simulation log*.
- There are two definitions for the `InOutStudy`:
    - `DescriptiveInOutStudy` which generates and saves all timeslots, not just data. These feature a duration, start time, unique ID, and optionally a parent or one or more children. Its further development was abandoned after noticing slow execution times and large amounts of output data.
    - `FastInOutStudy` which generates only the data transmission time slots, and supports both storage of the raw data (needed for the M2P performance analysis) or only storage of the main statistical descriptors.
- The name `InOutStudy` was used to reflect the methodology for allocating airtime - first, individual MSDU times are determined, followed by the network performance derivation (MSDU latency and throughput).



[ber-simulator]: https://github.com/PhyPy-802dot11ad/BER-simulator
[mdpi-paper]: https://www.mdpi.com/2079-9292/10/13/1599
[vtc-spring-paper]: https://www.google.com
[ber-data]: #BER-data
