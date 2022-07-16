"""

Constants corresponding mostly to the definitions in the IEEE 802.11ad standard.

"""

import os

import pandas as pd


MCS_TABLE = pd.read_csv(os.path.join(os.path.dirname(__file__), 'MCS_table.csv'), index_col='MCS')

PPDU_PREAMBLE_LEN = 3328
PPDU_HEADER_LEN = 1024
PPDU_GI_LENGTH = 64
SYMBOL_RATE_GHZ = 1.76
N_CBPB = [448, 896, 1792, 2688]

CONTROL_PPDU_PREAMBLE_LEN = 7552
CONTROL_PPDU_HEADER_LEN = 40
L_CWD = 168 # Max data bits in MCS 0 codeword

SIFS_NS = 3_000
DIFS_NS = 13_000
GI_NS = 3_000

TXTIME_SSW = 14641 # Time for transmitting SSW (24 bytes, control mode)
SBIFS_NS = 1_000
MBIFS_NS = 3*SIFS_NS
LBIFS_NS = TXTIME_SSW + 2*SBIFS_NS

MAX_MSDU_LENGTH = 7920
MAX_A_MSDU_LENGTH = 7935
MAX_PSDU_LENGTH = 262_143

MAX_PPDU_TIME = 2_000_000

AGC_AND_TRN_LENGTH = 5_312 # Number of symbols for single sector (multiply by number of sectors)

# ANTENNA_AZIMUTH_COVERAGE_DEG = 120
UE_TO_AP_DISTANCE_M = 5 # Users move in a fixed-distance circle around the AP
