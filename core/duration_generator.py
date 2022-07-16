"""

Module housing the `DUrationGenerator`, used for determining individual time slot durations, based on the input params.

"""

import math

import numpy as np

from .helpers import calc_control_frame_ppdu_size, calc_data_frame_ppdu_size
from .constants import *


class DurationGenerator():
    """Generates and stores time slot durations."""

    bti_duration = None
    bft_duration = None
    data_ppdu_duration = None
    cts_duration = None
    ack_duration = None

    def __init__(self):
        # self.mcs_table = pd.read_csv('MCS_table.csv', index_col='MCS')
        self.mcs_table = MCS_TABLE

    def generate_guard_time_duration(self, bi_duration):
        """Generate and store the duration of the guard time between allocations. Units are nanoseconds.

        Assume all allocations are nonpseudo-static (A1 = A2 = 0, 10.39.6.5 Guard time).
        The above also alleviates the need for separating B1 and B2 by assuming sync at the start of each BI.

        :param bi_duration: Beacon interval duration (ns).
        :type bi_duration: int
        """

        C = 20 * 10**(-6) # 20 ppm
        Tp = 100 # ns

        duration_rounded_to_us = math.ceil((C * bi_duration + SIFS_NS + Tp) * 10**(-3))
        self.guard_time_duration = duration_rounded_to_us * 10**(3)

    def generate_bti_duration(self, num_of_allocations):
        """Generate and store BTI (BF) timeslot duation.
        :param num_of_allocations: Number of SP/CBAP allocations, influences the length of beacon frames (n*15B).
        :type num_of_allocations: int
        """
        bf_payload_length = 66 + (2 + 15*num_of_allocations) + 34 # Mandatory part + extended schedule el. + SSID
        bti_ppdu_size = calc_control_frame_ppdu_size(bf_payload_length)
        # self.bti_duration = round( bti_ppdu_size / SYMBOL_RATE_GHZ )
        self.bti_duration = np.round( bti_ppdu_size / SYMBOL_RATE_GHZ ).astype(int)

    def generate_bft_duration(self, i_antennas, i_antenna_sectors, r_antennas, r_antenna_sectors, enable_SLS, enable_r_TXSS):
        """Generate and store BFT timeslot duration.

        SLS (and RXSS within it) can be toggled, while BRP is always included.

        :param i_antennas: Number of initiator antennas.
        :type i_antennas: int
        :param i_antenna_sectors: Number of initiator antenna sectors.
        :type i_antenna_sectors: int
        :param r_antennas: Number of responder antennas.
        :type r_antennas: int
        :param r_antenna_sectors: Number of responder antenna sectors.
        :type r_antenna_sectors: int
        :param enable_SLS: Enable in-bound SLS (as opposed to out-of-bounds).
        :type enable_SLS: bools
        :param enable_r_TXSS: Enable responder (AP) TXSS during SLS (as opposed to initiator-only during UE rotation).
        :type enable_r_TXSS: bool
        """

        self.bft_duration = 0

        if enable_SLS:
            if enable_r_TXSS:

                i_ssw_slots = i_antennas * i_antenna_sectors * r_antennas
                r_ssw_slots = r_antennas * r_antenna_sectors * i_antennas
                ssw_ppdu_size = calc_control_frame_ppdu_size(24)
                ssw_fbk_ppdu_size = ssw_ack_ppdu_size = calc_control_frame_ppdu_size(28)
                ppdu_size_sum = ssw_ppdu_size * (i_ssw_slots + r_ssw_slots) + ssw_fbk_ppdu_size + ssw_ack_ppdu_size
                ppdu_time_sum = round(ppdu_size_sum / SYMBOL_RATE_GHZ)

                # SBIFS - between SSWs, part of a single initiator antenna
                # LBIFS - either initiator or responder switches antennas
                # MBIFS - switching from TXSS to RXSS, assuming the same antennas are used at the end of TXSS and start of RXSS
                # SBIFS - between SSWs, part of a single responder antenna
                # LBIFS - either responder or initiator switches antennas
                # MBIFS/LBIFS - switching from RXSS to FBK (responder has to set the best antenna during TXSS to quasi-omni)
                # MBIFS/LBIFS - switching from FBK to ACK (responder has to switch to best antenna and pattern, indicated by FBK)
                idle_time_sum = \
                    SBIFS_NS * (i_antenna_sectors - 1) * i_antennas * r_antennas + \
                    LBIFS_NS * i_antennas * r_antennas + \
                    MBIFS_NS * 1 + \
                    SBIFS_NS * (r_antenna_sectors - 1) * r_antennas * i_antennas  + \
                    LBIFS_NS * i_antennas * r_antennas + \
                    MBIFS_NS * int(r_antennas==1) + LBIFS_NS * int(r_antennas>1) + \
                    MBIFS_NS * int(r_antennas==1) + LBIFS_NS * int(r_antennas>1)

                self.bft_duration = ppdu_time_sum + idle_time_sum

            else:

                i_ssw_slots = i_antennas * i_antenna_sectors * r_antennas
                r_ssw_slots = 1 # Used for providing feedback after initiator TXSS
                ssw_ppdu_size = calc_control_frame_ppdu_size(24)
                ssw_fbk_ppdu_size = ssw_ack_ppdu_size = calc_control_frame_ppdu_size(28)
                ppdu_size_sum = ssw_ppdu_size * (i_ssw_slots + r_ssw_slots) + ssw_fbk_ppdu_size + ssw_ack_ppdu_size
                ppdu_time_sum = round(ppdu_size_sum / SYMBOL_RATE_GHZ)

                # SBIFS - between SSWs, part of a single initiator antenna
                # LBIFS - either initiator or responder switches antennas
                # MBIFS - switching from TXSS to RXSS, assuming the same antennas are used at the end of TXSS and start of RXSS
                # 0 - Single response message, no RXSS
                # 0 - Single omni-directional response message on best antenna during TXSS reception, no RXSS
                # MBIFS/LBIFS - switching from RXSS to FBK (responder has to set the best antenna during TXSS to quasi-omni)
                # MBIFS/LBIFS - switching from FBK to ACK (responder has to switch to best antenna and pattern, indicated by FBK)
                idle_time_sum = \
                    SBIFS_NS * (i_antenna_sectors - 1) * i_antennas * r_antennas + \
                    LBIFS_NS * i_antennas * r_antennas + \
                    MBIFS_NS * 1 + \
                    0 + \
                    0 + \
                    MBIFS_NS * int(r_antennas==1) + LBIFS_NS * int(r_antennas>1) + \
                    MBIFS_NS * int(r_antennas==1) + LBIFS_NS * int(r_antennas>1)

                self.bft_duration = ppdu_time_sum + idle_time_sum

            self.bft_duration += SIFS_NS # Between SLS and BRP (Mavromatis, 2017, Beam alignment for mmilimeter...)

        brp_sector_quota = 0.25 # Sector quota used in the BRP (percentage of sectors used for BRP)

        # Calc amount of sectors used in BRP, use min 2
        i_brp_sectors = math.ceil(i_antenna_sectors * brp_sector_quota)
        if i_brp_sectors < 2: i_brp_sectors = 2
        r_brp_sectors = math.ceil(r_antenna_sectors * brp_sector_quota)
        if r_brp_sectors < 2: r_brp_sectors = 2

        # Add RX-TRN beam refinement transaction for each device, plus SIFS between them
        brp_duration = (
            calc_control_frame_ppdu_size(42) + i_brp_sectors * AGC_AND_TRN_LENGTH +
            calc_control_frame_ppdu_size(42) + r_brp_sectors * AGC_AND_TRN_LENGTH
        ) / SYMBOL_RATE_GHZ
        brp_duration += SIFS_NS # Between the two RX-TRN

        self.bft_duration += brp_duration


    def generate_data_ppdu_duration(self, payload_length, mcs):
        """Generate and store data PPDU timeslot duration.
        :param payload_length: PSDU length in octets.
        :type payload_length: int
        :param mcs: Modulation and coding scheme selected for transmission.
        :type mcs: float
        """
        Rm, Rc = self.mcs_table.loc[mcs][['Modulation_rate', 'Code_rate']]
        size = calc_data_frame_ppdu_size(payload_length, Rm, Rc)
        self.data_ppdu_duration = round(size / SYMBOL_RATE_GHZ)

    def generate_cts_duration(self):
        """Generate and store CTS-to-self timeslot duration.
        """
        ppdu_size = calc_control_frame_ppdu_size(20)
        self.cts_duration = round( ppdu_size / SYMBOL_RATE_GHZ )

    def generate_ack_duration(self, num_of_mpdu):
        """Generate and store acknowledgement timeslot duration.

        Single MPDU gets immediate ACK (14 B), A-MPDUs get BLK ACK (32 B)

        :param num_of_mpdu: Number of (A-)MPDUs per PPDU.
        :type num_of_mpdu: int
        """

        ack_payload_length = 14 if num_of_mpdu == 1 else 32
        ppdu_size = calc_control_frame_ppdu_size(ack_payload_length)
        self.ack_duration = round( ppdu_size / SYMBOL_RATE_GHZ )

    def generate_data_with_overhead_duration(self, enable_cts, enable_ack):
        """Generat duration of data PPDU + self-cts + ack, including all SIFS and  final DIFS.

        :param enable_cts: Flag indicating the usage of self-CTS.
        :type enable_cts: bool
        :param enable_ack: Flag indicating the usage of acknowledgements.
        :type enable_ack: bool
        """

        duration = self.get_data_ppdu_duration() + DIFS_NS
        if enable_cts: duration += self.get_cts_duration() + SIFS_NS
        if enable_ack: duration += self.get_ack_duration() + SIFS_NS

        self.data_with_overhead_duration = duration

    def get_guard_time_duration(self):
        return self.check_existence_and_return_duration(self.guard_time_duration)

    def get_bti_duration(self):
        return self.check_existence_and_return_duration(self.bti_duration)

    def get_bft_duration(self):
        return self.check_existence_and_return_duration(self.bft_duration)

    def get_data_ppdu_duration(self):
        return self.check_existence_and_return_duration(self.data_ppdu_duration)

    def get_cts_duration(self):
        return self.check_existence_and_return_duration(self.cts_duration)

    def get_ack_duration(self):
        return self.check_existence_and_return_duration(self.ack_duration)

    def get_data_with_overhead_duration(self):
        return self.check_existence_and_return_duration(self.data_with_overhead_duration)

    def check_existence_and_return_duration(self, duration):
        """Check if duration has been set and return it. Otherwise raise an error.
        :param duration: Value of self-attribute.
        :type duration: int or None
        :return: The duration if it has been set.
        :rtype: int
        """
        if type(duration) == type(None): raise RuntimeError('Tried fetching unset duration.')
        return duration
