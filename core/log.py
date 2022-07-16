"""

Module containing Log definitions.

These are either helper functions, such as for creating log (sub)directories, or the process log `PLog` class.
The latter is used by individual `InOutStudy` instances to output results and status reports.

"""

import os
import pickle
import re # Regular expression

import numpy as np


class PLog():
    """Single process log."""

    def __init__(self):
        pass

    def init_for_parallel_dir_structure(self, sid_log_dir_path, pid):
        """Initialize single process directory within the study log parent directory (single dir with millions of entries).

        :param sid_log_dir_path: Study log absolute path.
        :type sid_log_dir_path: str
        :param pid: Process ID.
        :type pid: int
        """
        self.log_path = os.path.join(sid_log_dir_path, f'{pid:012d}')
        self.make_log_dir()

    def init_for_subdir_structure(self, sid_log_dir_path, log_depth, pid):
        """Initialize subdirectory structure where process log will reside (avoid having a single dir with millions of entries).

        :param sid_log_dir_path: Study log absolute path.
        :type sid_log_dir_path: str
        :param log_depth: Amount of nested subdirectories.
        :type log_depth: int
        :param pid: Process ID.
        :type pid: int
        """
        self.log_path = os.path.join(
            sid_log_dir_path, # Study log dir
            *list(f'{pid//1000:0{log_depth}d}'), # Subdir for 1000 processes
            f'{pid%1000:04d}' # Single process dir
        )
        self.make_log_dir()

    def make_log_dir(self):
        """Make PDI log directory."""
        # os.makedirs( self.log_path )
        os.mkdir( self.log_path )

    def get_log_path(self):
        """Return process log path."""
        return self.log_path

    def save_metadata(self, t_begin, t_end):
        """Save process metadata.

        :param t_begin: Begin time (normally in iso format).
        :type t_begin: str
        :param t_end: Begin time (normally in iso format).
        :type t_end: str
        """
        metadata = {
            't_begin': t_begin,
            't_end': t_end
        }
        with open( os.path.join(self.log_path, 'metadata.pkl'), 'wb' ) as f:
            pickle.dump(metadata, f)

    def save_single_config(self, config):
        """Save configuration used by process.

        :param config: Study configuration used in parent process.
        :type config: dict
        """
        with open( os.path.join(self.log_path, 'config.pkl'), 'wb' ) as f:
            pickle.dump(config, f)

    def save_results(self, throughput, msdu_latency, t_msdu_generation=None, t_msdu_arrival=None, intermediate=None, channel_timeslot=None):
        """Save process results.

        :param throughput: The throughput in Gbps.
        :type throughput: float
        :param msdu_latency: MSDU latency description (normally mean, var, min, p25, median, p75, max).
        :type msdu_latency: dict
        :param t_msdu_generation: MSDU generation time.
        :type t_msdu_generation: ndarray
        :param t_msdu_arrival: MSDU arrival time.
        :type t_msdu_arrival: ndarray
        :param intermediate: Various intermediate results.
        :type intermediate: dict
        :param channel_timeslot: Channel timeslot object containing nested timeslots.
        :type channel_timeslot: object
        """
        with open(os.path.join(self.log_path, 'throughput.pkl'), 'wb') as f: pickle.dump(throughput, f)
        with open(os.path.join(self.log_path, 'msdu_latency.pkl'), 'wb') as f: pickle.dump(msdu_latency, f)
        if not t_msdu_generation is None:
            with open(os.path.join(self.log_path, 't_msdu_generation.pkl'), 'wb') as f: pickle.dump(t_msdu_generation, f)
        if not t_msdu_arrival is None:
            with open(os.path.join(self.log_path, 't_msdu_arrival.pkl'), 'wb') as f: pickle.dump(t_msdu_arrival, f)
        if not intermediate is None:
            with open(os.path.join(self.log_path, 'intermediate.pkl'), 'wb') as f: pickle.dump(intermediate, f)
        if not channel_timeslot is None:
            with open(os.path.join(self.log_path, 'channel_timeslot.pkl'), 'wb') as f: pickle.dump(channel_timeslot, f)

    def save_raw_msdu_times(self, t_msdu_generation, t_msdu_arrival):
        """Save only MSDU generation and arrival times.

        :param t_msdu_generation: MSDU generation time.
        :type t_msdu_generation: ndarray
        :param t_msdu_arrival: MSDU arrival time.
        :type t_msdu_arrival: ndarray
        """
        with open(os.path.join(self.log_path, 't_msdu_generation.pkl'), 'wb') as f: pickle.dump(t_msdu_generation, f)
        with open(os.path.join(self.log_path, 't_msdu_arrival.pkl'), 'wb') as f: pickle.dump(t_msdu_arrival, f)


def get_log_sid(parent_log_dir_path, sid_zero_pad=None):
    """Get lowest possible SID in parent log directory.

    :param parent_log_dir_path: Absolute path to parent log directory.
    :type parent_log_dir_path: str
    :param sid_zero_pad: Zero padding attached to SID when making SID string.
    :type sid_zero_pad: int
    :return: Lowest possible SID in parent log directory.
    :rtype: int or str
    """

    dirs = os.listdir(parent_log_dir_path)
    p = re.compile('^[0-9]*$')

    # Extract only directories corresponding to SIDs. Assume only these have fully-numerical names.
    existing_sid = []
    for d in dirs:
        if p.match(d) is None: continue
        existing_sid.append(int(d))
    existing_sid = np.sort(np.array(existing_sid))

    # Find the smallest possible available SID.
    if existing_sid.size == 0:
        sid = 0
    elif existing_sid[-1] == existing_sid.size - 1:
        sid = existing_sid[-1] + 1
    elif existing_sid[0] != 0:
        sid = 0
    else:
        last_idx = np.argmin(existing_sid[:-1] - existing_sid[1:])
        sid = existing_sid[last_idx] + 1

    # Convert to string (legacy)
    if not sid_zero_pad is None:
        sid = f'{sid:0{sid_zero_pad}d}'

    return sid


def save_study_config(sid_log_dir_path, config):
    """Save study configuration.

    :param sid_log_dir_path: Absolute path to study log dir.
    :type sid_log_dir_path: str
    :param config: Study configuration.
    :type config: dict
    """
    config_path = os.path.join(sid_log_dir_path, 'config.pkl')
    with open(config_path, 'wb') as f:
        pickle.dump(config, f)


def make_sid_log_dir(parent_log_dir_path, sid):
    """Make SID log directory if it doesn't exist and return the absolute path to it.

    :param parent_log_dir_path: Absolute path to parent log directory.
    :type parent_log_dir_path: str
    :param sid: Study/simulation ID.
    :type sid: int
    :return: Study/simulation ID log absolute path.
    :rtype: str
    """

    path = os.path.join(parent_log_dir_path, f'{sid:04d}')
    try:
        os.mkdir(path)
    except FileExistsError: # Skip if exists
        pass
    return path


if __name__ == '__main__':

    config = {
        'msdu_length_bytes': [2500],
        'msdu_max_agg': [True],
        'mpdu_max_agg': [True],
        'self_cts': [True],
        'ack': [True],
        'allowed_err': [10 ** (-5)],
        'enable_rxss': [True],
        'enalbe_sls': [True],
        'Eb_N0': [5.00],
        'movement': [0],
        'rotation': [0],
        'num_of_ue_antennas': [1],
        'num_of_users': [1]
    }

    parent_log_dir_path = '/Log'
    sid_zero_pad = 4

    sid = get_log_sid(parent_log_dir_path)
    sid_log_dir_path = make_sid_log_dir(parent_log_dir_path, sid)
    pid = 11

    process_log = PLog(sid_log_dir_path, pid)

    a=1
