"""

Main module for running IEEE 802.11ad MAC layer simulations, based on service period allocation.

"""


import os

from core.studyExecutor import StudyExecutor, StudyExecutorDynamicDb
from core.inOutStudy import FastInOutStudy


### GLOBAL SETUP

os.nice(10)


### STUDY SETUP

mp_pool_size = 8

parent_log_dir_path = os.path.join(os.path.dirname(__file__), 'log')

# ber_results_abs_path = os.path.join(os.path.dirname(__file__), 'ber_data', 'BER-3-iter.csv')
ber_results_abs_path = os.path.join(os.path.dirname(__file__), 'ber_data', 'BER-3-to-20-iter.csv')

config = {
    'msdu_length_bytes': [500, 1_500, 7_920],
    'msdu_max_agg': [True, False],
    'mpdu_max_agg': [True, False],
    'self_cts': [True, False],
    'ack': [True, False],
    'allowed_err': [10**(-5), 10**(-6), 10**(-7)],
    'enable_r_txss': [True, False], # Responder (AP) TXSS
    'enalbe_sls': [True, False],
    'Eb_N0': [i/100 for i in range(0,1500,25)],
    'mobility': [0, 's1', 's5', 'a90', 'a180', 'a360'],
    'num_of_ue_antennas': [1, 3],
    'num_of_antenna_sectors': [28, 34, 40],
    'num_of_users': [1, 2, 4, 8]
}

store_raw_msdu_times=True


### EXECUTION

# se = StudyExecutor(mp_pool_size, FastInOutStudy, config, parent_log_dir_path)
# se.begin_execution()

se = StudyExecutorDynamicDb(mp_pool_size, FastInOutStudy, config, parent_log_dir_path, ber_results_abs_path)
se.begin_execution(store_raw_msdu_times)
