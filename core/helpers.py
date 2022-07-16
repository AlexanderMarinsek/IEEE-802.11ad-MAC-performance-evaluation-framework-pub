"""

General helper function dump.

"""

import math
import warnings

import numpy as np

from .constants import *


# def get_optimal_mcs(Eb_N0, max_BER):
def get_optimal_mcs(Eb_N0, max_BER, ber_results_abs_path):
    """Get MCS that complies with max BER given noise amount that yields the most timely transmission.

    :param Eb_N0: Energy per bit vs noise power spectral density
    :param max_BER: Threshold bearing maximal allowed bit error rate (BER)
    :param ber_results_abs_path: Absolute path (string) to BER results CSV.
    :return: MCS
    """

    # ber = pd.read_csv( os.path.join(os.path.dirname(__file__), 'BER.csv'), index_col='Eb_N0')
    ber = pd.read_csv(ber_results_abs_path, index_col='Eb_N0')
    ber_row = ber.loc[Eb_N0]
    try:
        # Try extracting the highest MCS index that convorms to the BER requirement. Otherwise raise exception.
        # Round source BERs to the power of the threshold BER, avoiding exclusions due to digits at x-th decimal spot (like floating point error)
        power = np.abs((np.log10(max_BER))).astype(int)
        ber_row = ber_row.round(power)
        mcs = ber_row[ber_row <= max_BER].index.values.astype(float).max()
    except:
        raise RuntimeError(f'BER {max_BER} unattainable at {Eb_N0} dB.')
    return float(mcs)


def calc_control_frame_ppdu_size(payload_bytes):
    """Calculate PPDU size in symbols when using control MCS.

    Uses 3/4 code rate and shortening (don't transmit 0-bits). Use spreading with Ga32 sequence. Equation in 20.11.3 TXTIME calculation.

    :param payload_bytes: PSDU size in bytes (usually control frame octets)
    :type payload_bytes: int
    :return: PPDU size in symbols
    :rtype: int
    """

    # N_cw = 1 + math.ceil( (payload_bytes-6)*8 / L_CWD )
    N_cw = 1 + np.ceil( (payload_bytes-6)*8 / L_CWD )

    num_of_parity_symbols = 168 * N_cw
    num_of_data_symbols = (payload_bytes + 5) * 8 # Add header bytes

    num_of_useful_symbols = (num_of_parity_symbols + num_of_data_symbols) * 32 # Add spreading

    ppdu_size_symbols = \
        CONTROL_PPDU_PREAMBLE_LEN + \
        CONTROL_PPDU_HEADER_LEN + \
        num_of_useful_symbols

    return ppdu_size_symbols


def calc_data_frame_ppdu_size(PSDU_length_bytes, modulation_rate, code_rate):
    """Calculate PPDU size in symbols when using the defined modulation and code rate.

    :param PSDU_length_bytes: Payload length in octets.
    :type PSDU_length_bytes: int
    :param modulation_rate: Modulation rate (1,2,4,6 = BPSK, QPSK, 16QAM, 64QAM)
    :type modulation_rate: int
    :param code_rate: Code rate (1/2, 5/8, 3/4, 13/16)
    :type code_rate: float
    :return: PPDU size in symbols
    :rtype: int
    """

    N_cw = PSDU_length_bytes * 8 / (672 * code_rate)
    # N_data_pad = N_cw * 672 * code_rate - PSDU_length_bytes * 8

    N_cbpb = N_CBPB[int(modulation_rate / 2)]
    N_blks = math.ceil(N_cw * 672 / N_cbpb)
    # N_blk_pad = N_blks * N_cbpb - N_cw * 672

    payload_size_symbols = N_blks * 512

    return PPDU_PREAMBLE_LEN + PPDU_HEADER_LEN + payload_size_symbols + PPDU_GI_LENGTH


def calc_a_msdu_length( num_of_subframes, subframe_length ):
    """Calculate A-MSDU length in octets.

    Assume all subframes are of equal size. A-MSDU is "short A-MSDU" type.

    :param num_of_subframes: Number of MSDUs contained withing the A-MSDU frame.
    :type num_of_subframes: int
    :param subframe_length: Length of individual frames in octets.
    :type subframe_length: int
    :return: A-MSDU lenght in bytes.
    :rtype: int
    """

    if num_of_subframes <= 1: return subframe_length # Nothing to aggregate

    end_padding = subframe_length % 4
    a_msdu_length = num_of_subframes * (2 + subframe_length) + (num_of_subframes-1) * end_padding

    if a_msdu_length > MAX_A_MSDU_LENGTH: raise RuntimeError(f"A-MSDU exceeded max size {a_msdu_length} (max {MAX_A_MSDU_LENGTH})")

    return a_msdu_length


def calc_a_mpdu_length( num_of_subframes, subframe_length ):
    """Calculate A-MPDU length in octets.

    Assume all subframes are of equal size.

    :param num_of_subframes: Number of MPDUs contained withing the A-MPDU frame.
    :type num_of_subframes: int
    :param subframe_length: Length of individual frames in octets.
    :type subframe_length: int
    :return: A-MPDU lenght in bytes.
    :rtype: int
    """

    if num_of_subframes <= 1: return subframe_length # Nothing to aggregate

    end_padding = subframe_length % 4
    a_mpdu_length = num_of_subframes * (4 + subframe_length) + (num_of_subframes - 1) * end_padding

    return a_mpdu_length


def calc_data_mpdu_length( msdu_length, ack_policy=None ):
    """Calculate MPDU length in octets.

    Add only mandatory field and QoS control. If ACK is used, add "address 2" and "sequence control" fields.

    :param msdu_length: MSDU or A-MSDU length in octets.
    :type msdu_length: int
    :param ack_policy: Acknowledgement policy.
    :type ack_policy: int
    :return: MPDU lenght in bytes.
    :rtype: int
    """

    mpdu_length = 16 + msdu_length

    if ack_policy != None: mpdu_length += 8 # Add "address 2" and "sequence control" fields

    return mpdu_length


def get_number_of_bft_allocations( num_of_observed_bi, bi_duration, bft_period, num_of_users ):
    """Get the number of BFT allocations in every BI.

    All users equally contribute to the amount of BFT allocations.
    The BFTs per user are assumed out of sync - shift the BFT distribution by one BI for each succeeding user.
    Default to 1 BFT allocation per observed period if the BFT period is longer than the observed period (BIs*BI_duration).

    :param num_of_observed_bi: Number of BIs, determining the total time.
    :type num_of_observed_bi: int
    :param bi_duration: Single BI duration (ns).
    :type bi_duration: int
    :param bft_period: Target beamforming period (ns).
    :type bft_period: int
    :param num_of_users: Number of equally prioritised users.
    :type num_of_users: int
    :return: Number of BFT allocations in every BI
    :rtype: List
    """

    bft_per_bi_array = np.zeros(num_of_observed_bi, dtype=int)

    if bft_period > num_of_observed_bi * bi_duration:
        msg = f"No BFT allocations with period {bft_period} in observed period {num_of_observed_bi*bi_duration}, switching to 0 BFT allocations."
        print (msg)
        # warnings.warn(msg)
        bft_per_bi_array[np.random.randint(0,num_of_observed_bi)] = 1
        # raise RuntimeError (f"No BFT allocations with period {bft_period}, in observed period {num_of_observed_bi*bi_duration}")
    else:
        bft_per_bi = bi_duration / bft_period # First calc number of allocations per user
        # Distribute BFT among BIs. Uneven when BFT period is not an integer.
        carry = 0
        for idx in range(num_of_observed_bi):
            carry += bft_per_bi
            bft_per_bi_array[idx] = int(carry)
            carry %= 1

    # Then multiply by the number of users
    # bft_per_bi_array_multi_user = bft_per_bi_array * num_of_users

    # Apply BFT to each user. Assume the BFTs are out-of sync.
    bft_per_bi_array_multi_user = np.zeros_like(bft_per_bi_array)
    for i in range(num_of_users):
        bft_per_bi_array_multi_user += np.roll(bft_per_bi_array, i)

    # return bft_per_bi_array
    return bft_per_bi_array_multi_user


def calc_max_a_mpdu_subframes(mcs, subframe_length):
    """Calculate maximal number of A-MPDU subframes for transmission, with regards to:
     - 262 143 octet PSDU length limit
     - 2 ms PPDU time limit

    :param mcs: MCS chosen fro transmission.
    :type mcs: float
    :param subframe_length: A-MPDU subframe length (octets).
    :type subframe_length: int
    :return: Maximal number of subframes
    :rtype: int
    """
    # mcs_table = pd.read_csv('MCS_table.csv', index_col='MCS')
    mcs_table = MCS_TABLE
    Rm, Rc = mcs_table.loc[mcs][['Modulation_rate', 'Code_rate']]

    available_time = MAX_PPDU_TIME - 2_509 # 2509,09 ns = PREAMBLE + HEADER + first GUARD INTERVAL (no optimal - const)
    num_of_symbols = int(available_time * SYMBOL_RATE_GHZ) # (no optimal - repetitive calculation of a constant value)
    mpdu_octets = int(num_of_symbols *  448/512 * Rm * Rc / 8) # Calc bytes, given MCS (could be look-up for every MCS)
    if mpdu_octets > MAX_PSDU_LENGTH: mpdu_octets = MAX_PSDU_LENGTH # Impose upper size limit

    padding = subframe_length % 4
    num_of_subframes = mpdu_octets / (4 + subframe_length + padding) # Assumes last subframe is also padded (if padding is needed at all)

    return int(num_of_subframes)



### Functions updated to here ##########################################################################################


# def calc_access_duration():
#     """2020 std. 9.3.1.13 DMG CTS frame format"""
#     len_bytes = 20
#     Rm, Rc = MCS_TABLE.loc[1.0][['Modulation_rate', 'Code_rate']] # Is mcs correct
#     duration = get_ppdu_payload_size( len_bytes, Rm, Rc ) / SYMBOL_RATE_GHZ
#     return duration
#
#
# def calc_acknowledgement_duration(num_of_msdu):
#     if num_of_msdu == 1:
#         len_bytes = 14 # General - 9.3.1.4 Ack frame format
#     duration = 0
#     return duration
#
#
# class Ppdu:
#
#     def __init__(self, d_acc, d_ppdu, d_ack, d_idle):
#         self.d_acc = d_acc
#         self.d_ppdu = d_ppdu
#         self.d_ack = d_ack
#         self.d_idle = d_idle
#
#     def get_total_time(self):
#         return self.d_acc + self.d_ppdu + self.d_ack + self.d_idle
#
# class PpduGenerator():
#
#     def __init__(self):
#         self.mcs_table = pd.read_csv('MCS_table.csv', index_col='MCS')  # Const
#
#     def generate_PPDU(self, Eb_N0, max_BER, PSDU_length_bytes):
#
#         # Look up optimal MCS and extract the modulation- and code rate.
#         mcs = get_optimal_mcs(Eb_N0, max_BER)
#         Rm, Rc = self.mcs_table.loc[mcs][['Modulation_rate', 'Code_rate']]
#
#         # Get size
#         size_symbols = PPDU_PREAMBLE_LEN + PPDU_HEADER_LEN + get_ppdu_payload_size(PSDU_length_bytes, Rm, Rc)
#         d_ppdu = size_symbols / SYMBOL_RATE_GHZ
#
#         ppdu = Ppdu(0, d_ppdu, 0 ,0)
#
#         return ppdu
#
# CTS_MPDU_OCTETS = 20
# CTS_PPDU_SIZE = get_control_frame_ppdu_size(CTS_MPDU_OCTETS)
# CTS_PPDU_TX_TIME = CTS_PPDU_SIZE / SYMBOL_RATE_GHZ
# ACK_MPDU_OCTETS = 14
# ACK_PPDU_SIZE = get_control_frame_ppdu_size(ACK_MPDU_OCTETS)
# ACK_PPDU_TX_TIME = ACK_PPDU_SIZE / SYMBOL_RATE_GHZ
# BA_MPDU_OCTETS = 32
# BA_PPDU_SIZE = get_control_frame_ppdu_size(BA_MPDU_OCTETS)
# BA_PPDU_TX_TIME = BA_PPDU_SIZE / SYMBOL_RATE_GHZ
#
# def calc_tx_busy_time( psdu_len, mcs, use_cts_to_self=False, ack_policy=None ):
#
#     tx_busy_time = 0
#
#     if use_cts_to_self:
#         tx_busy_time += CTS_PPDU_TX_TIME
#         tx_busy_time += SIFS_NS
#
#     Rm, Rc = MCS_TABLE.loc[mcs][['Modulation_rate', 'Code_rate']]
#     ppdu_time = get_ppdu_payload_size( psdu_len, Rm, Rc ) / SYMBOL_RATE_GHZ
#     tx_busy_time += ppdu_time
#
#     if ack_policy == 'ack':
#         tx_busy_time += SIFS_NS
#         tx_busy_time += ACK_PPDU_TX_TIME
#     elif ack_policy == 'block ack':
#         tx_busy_time += SIFS_NS
#         tx_busy_time += BA_PPDU_TX_TIME
#     elif not ack_policy is None:
#         raise ValueError (f'Unknown ack policy {ack_policy}')
#
#     tx_busy_time += DIFS_NS
#
#     return tx_busy_time
#
# ppdu_generator = PpduGenerator()
#
# Eb_N0 = 3.5
# max_BER = 10**(-5)
# PSDU_length_bytes = 1_500
#
# ppdu = ppdu_generator.generate_PPDU( Eb_N0, max_BER, PSDU_length_bytes )
#
# get_control_frame_ppdu_size( 128 )
#
# print (calc_tx_busy_time( 1000, 10.0 ))
# print (calc_tx_busy_time( 1000, 10.0, True ))
# print (calc_tx_busy_time( 1000, 10.0, True, 'ack' ))
# print (calc_tx_busy_time( 1000, 10.0, True, 'block ack' ))
