"""
_summary_
"""

import os
import pathlib
from enum import Enum

####################################################################################################
# PIPELINE FOLDERS
####################################################################################################

DF_IO_FORMAT = "parquet"


class Folders(Enum):
    """Enum for the pipeline folders."""

    CONFIGS = "0_configs"
    RAW_VID = "1_raw_vid"
    FORMATTED_VID = "2_formatted_vid"
    DLC = "3_dlc"
    PREPROCESSED = "4_preprocessed"
    FEATURES_EXTRACTED = "5_features_extracted"
    PREDICTED_BEHAVS = "6_predicted_behavs"
    SCORED_BEHAVS = "7_scored_behavs"
    # ANALYSIS = "8_analysis"
    ANALYSE_COMBINED = "9_analysis_combined"
    EVALUATE_VID = "10_evaluate_vid"


class FileExts(Enum):
    CONFIGS = "json"
    RAW_VID = "mp4"
    FORMATTED_VID = "mp4"
    DLC = DF_IO_FORMAT
    PREPROCESSED = DF_IO_FORMAT
    FEATURES_EXTRACTED = DF_IO_FORMAT
    PREDICTED_BEHAVS = DF_IO_FORMAT
    SCORED_BEHAVS = DF_IO_FORMAT
    ANALYSE_COMBINED = DF_IO_FORMAT
    EVALUATE_VID = "mp4"


# TODO: is there a better way to do the subsubdirs?
DIAGNOSTICS_DIR = "0_diagnostics"
ANALYSIS_DIR = "8_analysis"

CACHE_DIR = os.path.join(pathlib.Path.home(), ".behavysis_temp")


####################################################################################################
# DIAGNOSTICS CONSTANTS
####################################################################################################


STR_DIV = "".ljust(50, "-")


####################################################################################################
# PLOT CONSTANTS
####################################################################################################

PLOT_STYLE = "whitegrid"
PLOT_DPI = 75