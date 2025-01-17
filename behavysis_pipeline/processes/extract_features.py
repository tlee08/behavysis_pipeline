"""
_summary_
"""

import os

import pandas as pd

from behavysis_pipeline.constants import CACHE_DIR
from behavysis_pipeline.df_classes.features_df import FeaturesDf
from behavysis_pipeline.df_classes.keypoints_df import KeypointsDf
from behavysis_pipeline.pydantic_models.experiment_configs import ExperimentConfigs
from behavysis_pipeline.utils.diagnostics_utils import file_exists_msg
from behavysis_pipeline.utils.io_utils import get_name, silent_remove
from behavysis_pipeline.utils.logging_utils import init_logger, logger_func_decorator
from behavysis_pipeline.utils.misc_utils import enum2tuple
from behavysis_pipeline.utils.multiproc_utils import get_cpid
from behavysis_pipeline.utils.subproc_utils import run_subproc_console
from behavysis_pipeline.utils.template_utils import save_template

# Order of bodyparts is from
# - https://github.com/sgoldenlab/simba/blob/master/docs/Multi_animal_pose.md
# - https://github.com/sgoldenlab/simba/blob/master/docs/Tutorial_DLC.md
# - https://github.com/sgoldenlab/simba/blob/master/simba/pose_configurations/bp_names/bp_names.csv
# - https://github.com/sgoldenlab/simba/blob/master/simba/pose_configurations/configuration_names/pose_config_names.csv
# 2 animals; 16 body-parts

#####################################################################
#               FEATURE EXTRACTION FOR SIMBA
#####################################################################


class ExtractFeatures:
    """__summary__"""

    logger = init_logger(__name__)

    @staticmethod
    @logger_func_decorator(logger)
    def extract_features(
        dlc_fp: str,
        out_fp: str,
        configs_fp: str,
        overwrite: bool,
    ) -> str:
        """
        Extracting features from preprocessed DLC dataframe using SimBA
        processes.

        Parameters
        ----------
        dlc_fp : str
            Preprocessed DLC filepath.
        out_fp : str
            Filepath to save extracted_features dataframe.
        configs_fp : str
            Configs JSON filepath.
        overwrite : bool
            Whether to overwrite the out_fp file (if it exists).

        Returns
        -------
        str
            The outcome of the process.
        """
        if not overwrite and os.path.exists(out_fp):
            return file_exists_msg(out_fp)
        outcome = ""
        # Getting directory and file paths
        name = get_name(dlc_fp)
        cpid = get_cpid()
        configs_dir = os.path.split(configs_fp)[0]
        simba_in_dir = os.path.join(CACHE_DIR, f"input_{cpid}")
        simba_dir = os.path.join(CACHE_DIR, f"simba_proj_{cpid}")
        features_from_dir = os.path.join(simba_dir, "project_folder", "csv", "features_extracted")
        # Preparing dlc dfs for input to SimBA project
        os.makedirs(simba_in_dir, exist_ok=True)
        simba_in_fp = os.path.join(simba_in_dir, f"{name}.csv")
        # Selecting bodyparts for SimBA (8 bpts, 2 indivs)
        df = KeypointsDf.read_feather(dlc_fp)
        df = select_cols(df, configs_fp)
        # Saving dlc frame to place in the SimBA features extraction df
        index = df.index
        # Need to remove index name for SimBA to import correctly
        df.index.name = None
        # Saving as csv
        df.to_csv(simba_in_fp)
        # Removing simba folder (if it exists)
        silent_remove(simba_dir)
        # Running SimBA env and script to run SimBA feature extraction
        outcome += run_simba_subproc(simba_dir, simba_in_dir, configs_dir, CACHE_DIR, cpid)
        # Exporting SimBA feature extraction csv to feather
        simba_out_fp = os.path.join(features_from_dir, f"{name}.csv")
        export2feather(simba_out_fp, out_fp, index)
        # Removing temp folders (simba_in_dir, simba_dir)
        silent_remove(simba_in_dir)
        silent_remove(simba_dir)
        # Returning outcome
        return outcome


#####################################################################
#               PREPARE FOR SIMBA
#####################################################################


def select_cols(
    df: pd.DataFrame,
    configs_fp: str,
) -> pd.DataFrame:
    """
    Selecting given DLC columns to input to SimBA.

    Parameters
    ----------
    df : pd.DataFrame
        DLC dataframe.
    configs_fp : str
        Configs dict.

    Returns
    -------
    pd.DataFrame
        DLC dataframe with selected columns.
    """
    # Getting necessary config parameters
    configs = ExperimentConfigs.read_json(configs_fp)
    configs_filt = configs.user.extract_features
    indivs = configs.get_ref(configs_filt.individuals)
    bpts = configs.get_ref(configs_filt.bodyparts)
    # Checking that the bodyparts are all valid
    KeypointsDf.check_bpts_exist(df, bpts)
    # Selecting given columns
    idx = pd.IndexSlice
    df = df.loc[:, idx[:, indivs, bpts]]
    # returning df
    return df


def run_simba_subproc(
    simba_dir: str,
    dlc_dir: str,
    configs_dir: str,
    temp_dir: str,
    cpid: int,
) -> str:
    """
    Running the custom SimBA script to take the prepared DLC dataframe as input and
    create the features extracted dataframe.

    A custom SimBA script must be run in a separate custom conda environment because SimBA
    cannot be installed in the same environment as DEEPLABCUT (and also uses Python 3.6 -
    which is old).

    Parameters
    ----------
    simba_dir : str
        SimBA project directory.
    dlc_dir : str
        Prepared DLC dataframes directory. SimBA imports the entire directory.
        If only one file is being processed, put that file in a separate folder.
    configs_dir : str
        Directory path of config files corresponding to DLC dataframes in dlc_dir.
        For each DLC dataframe file, there should be a config file with the same name.
    """
    # Saving the script to a file
    script_fp = os.path.join(temp_dir, f"simba_subproc_{cpid}.py")
    save_template(
        "simba_subproc.py",
        "behavysis_pipeline",
        "templates",
        script_fp,
        simba_dir=simba_dir,
        dlc_dir=dlc_dir,
        configs_dir=configs_dir,
    )
    # Running the Simba subprocess in a separate conda env
    cmd = [
        os.environ["CONDA_EXE"],
        "run",
        "--no-capture-output",
        "-n",
        "simba",
        "python",
        script_fp,
    ]
    # run_subproc_fstream(cmd)
    run_subproc_console(cmd)
    # Removing the script file
    silent_remove(script_fp)
    return "Ran SimBA feature extraction script.\n"


def remove_bpts_cols(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Drops the bodyparts columns from the SimBA features extractions dataframes.
    Because bodypart coordinates should not be a factor in behaviour classification.

    Parameters
    ----------
    df : pd.DataFrame
        Features extracted dataframe

    Returns
    -------
    pd.DataFrame
        Features extracted dataframe with the bodyparts columns dropped.
    """
    indivs_n = 2
    bpts_n = 8
    coords_n = 3
    n = indivs_n * bpts_n * coords_n
    return df.iloc[:, n:]


def export2feather(in_fp: str, out_fp: str, index: pd.Index) -> str:
    """
    __summary__
    """
    df = pd.read_csv(in_fp, header=0, index_col=0)
    # Setting index to same as dlc preprocessed df
    df.index = index
    # Setting index and column level names
    df.index.names = list(enum2tuple(FeaturesDf.IN))
    df.columns.names = list(enum2tuple(FeaturesDf.CN))
    # Saving SimBA extracted features df as feather
    FeaturesDf.write_feather(df, out_fp)
    # Returning outcome
    return "Exported SimBA features to feather.\n"
