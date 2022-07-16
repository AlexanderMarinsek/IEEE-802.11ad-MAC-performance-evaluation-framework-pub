"""

Module housing the study executor an middleman between it and the database.

"""


import os
import sys
import itertools
import multiprocessing as mp
from datetime import datetime as dt

from .stat import describe_normal_distribution
from .log import PLog, get_log_sid, make_sid_log_dir, save_study_config
from .db import Db


class Librarian():
    """Middleman between workers and database.

    Waits for results to appear in a queue (buffer) and puts them in the database.
    """

    write_frequency = 100_000

    def __init__(self, study_config):
        """
        :param study_config: Global study configuration.
        :type study_config: dict
        """

        max_pid = 1
        for v in study_config.values():
            max_pid *= len(v)
        pid_list = [*range(max_pid)]

        study_config_cols = study_config.keys()
        msdu_latency_cols = ['mean', 'var', 'min', 'q1', 'q2', 'q3', 'max']

        self.db = Db( pid_list, study_config_cols, msdu_latency_cols )


    def run(self, q, save_dirpath):
        """Run an infinite loop, periodically saving results. Quit when 'kill' message is received.

        :param q: Multiprocessing manager queue.
        :type q: object
        :param save_dirpath: Absolute path to where the DB is saved.
        :type save_dirpath: str
        """

        num_of_entries = 0 # Keep track of written elements for providing intermediate output

        while 1:
            msg = q.get()
            if msg == 'kill':
                self.db.save(save_dirpath)
                break
            self.db.add_results(msg['pid'], msg['config'], msg['status'], msg['mcs'], msg['throughput'], msg['msdu_latency'])
            # self.db.add_results(msg['pid'], msg['config'], msg['status'], msg['throughput'], msg['msdu_latency'])

            # Save every X-entries
            num_of_entries += 1
            # if num_of_entries % 1000 == 0:
            if num_of_entries % self.write_frequency == 0:
                self.db.save(save_dirpath)



class StudyExecutorDynamicDb():
    """Multi-process study execution wrapper that dynamically builds database.

    Individual process results are put in corresponding subdirectories, while a general overview of processes, their
    inputs, and their results is built in parallel.
    """

    def __init__(self, mp_pool_size, study_class, config, parent_log_dir_path, ber_results_abs_path):
        """
        :param mp_pool_size: Max number of parallel processes.
        :type mp_pool_size: int
        :param study_class: Reference to study class definition.
        :type study_class: object
        :param config: Input parameters.
        :type config: dict
        :param parent_log_dir_path: Absolute path to log directory.
        :type parent_log_dir_path: str
        :param ber_results_abs_path: Absolute path to simulation BER results csv file (including filename).
        :type ber_results_abs_path: str
        """
        self.mp_pool_size = mp_pool_size
        self.study_class = study_class
        self.config = config

        # Make unique subdirectory in `Log` directory
        sid = get_log_sid(parent_log_dir_path)
        self.sid_log_dir_path = make_sid_log_dir(parent_log_dir_path, sid)

        save_study_config(self.sid_log_dir_path, config)

        self.ber_results_abs_path = ber_results_abs_path


    def begin_execution(self, store_raw_msdu_times=False):
        """Commence multi-process execution.

        :param store_raw_msdu_times: Flag indicating whether to store MSDU arrival and generation times.
        :type store_raw_msdu_times: bool
        """

        # Must use Manager queue here, or will not work
        manager = mp.Manager()
        q = manager.Queue()
        print(f'Re-formatting input arguments before execution.')

        # Create unique config combinations
        config_list = []
        for key in self.config:
            config_list.append(self.config[key])
        config_iterable = list(itertools.product(*config_list))

        max_pid = len(config_iterable)

        pool = mp.Pool(self.mp_pool_size)

        print(f'Preparing for execution of {len(config_iterable)} processes, max. {self.mp_pool_size} at a time.')
        pid_list = [*range(max_pid)]

        print(f'Execution started.')

        librarian = Librarian(self.config)

        # Put listener to work first
        watcher = pool.apply_async(librarian.run, (q, self.sid_log_dir_path))

        # Fire off workers
        jobs = []
        for pid, ci in zip(pid_list, config_iterable):
            # job = pool.apply_async(simulate_single, (pid, ci, self.config.keys(), FastInOutStudy, self.sid_log_dir_path, q))
            # job = pool.apply_async(self.simulate_single, (pid, ci, q, store_raw_msdu_times))
            job = pool.apply_async(self.simulate_single, (pid, ci, q, store_raw_msdu_times, self.ber_results_abs_path))
            jobs.append(job)

        # Collect results from the workers through the pool result queue
        for job in jobs:
            job.get()  # Use '.get()' because it raises exceptions. On the other hand, '.wait() doesn't

        # Now we are done, kill the listener
        q.put('kill')
        pool.close()
        pool.join()


    # def simulate_single(self, pid, config_iterable, q, store_raw_msdu_times):
    def simulate_single(self, pid, config_iterable, q, store_raw_msdu_times, ber_results_abs_path):
        """Run simulation for a single config combination. Run in worker process.

        :param pid: Process ID.
        :type pid: int
        :param config_iterable: Study config values.
        :type config_iterable: list
        :param q: Multiprocessing manage queue object.
        :type q: object
        :param store_raw_msdu_times: Flag indicating whether to store MSDU arrival and generation times.
        :type store_raw_msdu_times: bool
        :return: Status (0 for all OK, -1 for something went wrong)
        :rtype: int
        """

        single_config = dict(zip(self.config.keys(), config_iterable))  # Convert list of config values to dictionary

        t_begin = dt.now().isoformat()  # Time execution

        process_log = PLog()  # Start new log
        process_log.init_for_parallel_dir_structure(self.sid_log_dir_path, pid)

        sys.stdout = open(os.path.join(process_log.get_log_path(), 'std.out'), 'w')  # Redirect std out.
        print(f'Begin: {t_begin}')  # Test print in case stdout is otherwise empty

        process_log.save_metadata(t_begin, None)  # Pre-save in case of early termination
        process_log.save_single_config(single_config)  # Pre-save in case of early termination

        ### SETUP

        ios = self.study_class()

        try:
            # ios.set_mcs(
            #     single_config['Eb_N0'],
            #     single_config['allowed_err']
            # )
            ios.set_mcs(
                single_config['Eb_N0'],
                single_config['allowed_err'],
                ber_results_abs_path
            )
        except Exception as e:
            print(str(e))
            sys.stdout.flush()
            sys.stdout.close()
            res = dict(pid=pid, config=single_config, status=1, mcs=0, throughput=0, msdu_latency=0)
            q.put(res)
            return -1

        ios.set_num_of_users(single_config['num_of_users'])

        ios.set_bft_duration(
            single_config['num_of_ue_antennas'],
            single_config['num_of_antenna_sectors'],
            single_config['enalbe_sls'],
            single_config['enable_r_txss']
        )

        ios.set_num_of_data_sp_allocations(
            single_config['num_of_antenna_sectors'],
            single_config['mobility']
        )

        ios.set_mpdu_length(
            single_config['msdu_length_bytes'],
            single_config['msdu_max_agg']
        )

        ios.set_psdu_length(single_config['mpdu_max_agg'])

        ios.set_ack_duration()

        ios.set_data_ppdu_duration()

        ios.set_data_with_overhead_duration(
            single_config['self_cts'],
            single_config['ack']
        )

        ios.set_cts_enabled_flag(single_config['self_cts'])

        ios.set_ack_enabled_flag(single_config['ack'])

        ### RUN and SAVE

        try:
            ios.run()
        except Exception as e:
            print(f'Encountered exception while running study: {str(e)}')
            sys.stdout.flush()
            sys.stdout.close()
            res = dict(pid=pid, config=single_config, status=-1, mcs=0, throughput=0, msdu_latency=0)
            q.put(res)
            return -1

        ios.calc_performance_metrics()

        throughput, msdu_latency = ios.get_performance_metrics()
        t_msdu_generation, t_msdu_arrival = ios.get_msdu_times()

        msdu_latency_compact = describe_normal_distribution(msdu_latency)

        t_end = dt.now().isoformat()

        process_log.save_metadata(
            t_begin,
            t_end
        )

        if store_raw_msdu_times: # May generate TBs of data
            process_log.save_raw_msdu_times(
                t_msdu_generation,
                t_msdu_arrival
            )

        sys.stdout.flush()
        sys.stdout.close()

        res = dict(
            pid=pid,
            config=single_config,
            status=0,
            mcs=ios.get_mcs(),
            throughput=throughput,
            msdu_latency=msdu_latency_compact
        )

        q.put(res)

        return 0



class StudyExecutor():
    """Multi-process study execution wrapper where results are individually dumped and need later processing."""

    def __init__(self, mp_pool_size, study_class, config, parent_log_dir_path):
        """
        :param mp_pool_size: Max number of parallel processes.
        :type mp_pool_size: int
        :param study_class: Reference to study class definition.
        :type study_class: object
        :param config: Input parameters.
        :type config: dict
        :param parent_log_dir_path: Absolute path to log directory.
        :type parent_log_dir_path: str
        """
        self.mp_pool_size = mp_pool_size
        self.study_class = study_class
        self.config = config

        sid = get_log_sid(parent_log_dir_path)
        self.sid_log_dir_path = make_sid_log_dir(parent_log_dir_path, sid)

        save_study_config(self.sid_log_dir_path, config)


    def begin_execution(self):
        """Commence multi-process execution."""

        print(f'Re-formatting input arguments before execution.')

        # Create unique config combinations
        config_list = []
        for key in self.config:
            config_list.append(self.config[key])
        config_iterable = list(itertools.product(*config_list))

        # Reformat combinations back to dictionary and associate each with the log path and the process ID
        # input_args = [] # Make list of input arguments for 'starmap'
        # for pid, single_config in enumerate(config_iterable):
        #     config_combination = {} # Make dictionaries again for easier access
        #     for key, val in zip(self.config.keys(), single_config):
        #         config_combination[key] = val
        #     input_args.append((config_combination, self.sid_log_dir_path, pid)) # Add log path and PID
        #
        print(f'Preparing for execution of {len(config_iterable)} processes, max. {self.mp_pool_size} at a time.')

        max_pid = len(config_iterable)

        self.generate_pid_subdirs(max_pid)

        pid_list = [*range(max_pid)]
        input_args = [*zip(
            config_iterable, # Individual configurations
            [len(str(max_pid//1000))]*len(pid_list), # Subdir depth
            pid_list # PIDs
        )]

        print(f'Execution started.')

        # Execute results in multiple processes
        with mp.Pool(self.mp_pool_size) as p:
            p.starmap(self.run_single_and_save_results, input_args)

        # for ia in input_args:
        #     self.run_single_and_save_results(*ia)

        # for ia in input_args:
        #     self.run_single_and_save_results(*ia)


    def generate_pid_subdirs(self, max_pid):
        """Generate log subdirectories.

        Only generates the major subdirs (per 1000 processes).
        Part of initialization to avoid race conditions.

        :param max_pid: Highest process ID.
        :type max_pid: int
        """

        val = max_pid // 1000
        depth = len(str(val)) # Number of subdirectories / directory tree depth
        while val >= 0:
            path = os.path.join(
                self.sid_log_dir_path,
                *list(f'{val:0{depth}d}')
            )
            os.makedirs(path)
            val -= 1


    # def run_single_and_save_results(self, single_config, sid_log_dir_path, pid):
    def run_single_and_save_results(self, single_config, log_depth, pid):
        """Run study for single input param combination and save the results.

        :param single_config: Single config combination.
        :type single_config: object
        :param sid_log_dir_path: Absolute path to log directory.
        :type sid_log_dir_path: str
        :param sid_log_dir_path: Log directory depth (implemented for faster interfacing during analysis).
        :type sid_log_dir_path: int
        :param pid: Unique process ID.
        :type pid: int
        """

        single_config = dict(zip(self.config.keys(), single_config)) # Convert list of config values to dictionary

        t_begin = dt.now().isoformat()  # Time execution

        process_log = PLog()  # Start new log
        process_log.init_for_subdir_structure(self.sid_log_dir_path, log_depth, pid)  # Start new log

        sys.stdout = open(os.path.join(process_log.get_log_path(), 'std.out'), 'w')  # Redirect std out.
        print(f'Begin: {t_begin}')  # Test print in case stdout is otherwise empty

        process_log.save_metadata( t_begin, None ) # Pre-save in case of early termination
        process_log.save_single_config( single_config ) # Pre-save in case of early termination

        ### SETUP

        ios = self.study_class()

        try:
            ios.set_mcs(
                single_config['Eb_N0'],
                single_config['allowed_err']
            )
        except Exception as e:
            print(str(e))
            return

        ios.set_num_of_users( single_config['num_of_users'] )

        ios.set_bft_duration(
            single_config['num_of_ue_antennas'],
            single_config['num_of_antenna_sectors'],
            single_config['enalbe_sls'],
            single_config['enable_r_txss']
        )

        ios.set_num_of_data_sp_allocations(
            single_config['num_of_antenna_sectors'],
            # single_config['speed'],
            # single_config['angular_velocity']
            single_config['mobility']
        )

        ios.set_mpdu_length(
            single_config['msdu_length_bytes'],
            single_config['msdu_max_agg']
        )

        ios.set_psdu_length(single_config['mpdu_max_agg'])

        ios.set_ack_duration()

        ios.set_data_ppdu_duration()

        ios.set_data_with_overhead_duration(
            single_config['self_cts'],
            single_config['ack']
        )

        ios.set_cts_enabled_flag(single_config['self_cts'])

        ios.set_ack_enabled_flag(single_config['ack'])

        ### RUN and SAVE

        try:
            ios.run()
        except Exception as e:
            print(f'Encountered exception while running study: {str(e)}')
            return

        ios.calc_performance_metrics()

        throughput, msdu_latency = ios.get_performance_metrics()
        t_msdu_generation, t_msdu_arrival = ios.get_msdu_times()
        # intermediate = ios.get_intermediate_data()
        # channel_timeslots = ios.get_raw_channel_timeslots()

        msdu_latency_compact = describe_normal_distribution(msdu_latency)

        t_end = dt.now().isoformat()

        process_log.save_metadata(
            t_begin,
            t_end
        )

        process_log.save_results(
            throughput,
            msdu_latency_compact,
            t_msdu_generation=t_msdu_generation,
            t_msdu_arrival=t_msdu_arrival
            # intermediate=intermediate,
            # channel_timeslots=channel_timeslots
        )

        sys.stdout.flush()
        sys.stdout.close()
