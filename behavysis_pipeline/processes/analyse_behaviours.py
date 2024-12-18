"""
Functions have the following format:

Parameters
----------
dlc_fp : str
    The DLC dataframe filepath of the experiment to analyse.
ANALYSE_DIR : str
    The analysis directory path.
configs_fp : str
    the experiment's JSON configs file.

Returns
-------
str
    The outcome of the process.
"""

from __future__ import annotations

import os

import numpy as np
from behavysis_core.df_classes.analyse_binned_df import AnalyseBinnedDf
from behavysis_core.df_classes.analyse_df import AnalyseDf
from behavysis_core.df_classes.behav_df import BehavColumns, BehavDf
from behavysis_core.mixins.io_mixin import IOMixin
from behavysis_core.mixins.misc_mixin import MiscMixin
from behavysis_core.pydantic_models.experiment_configs import ExperimentConfigs

###################################################################################################
#               ANALYSIS API FUNCS
###################################################################################################


class AnalyseBehaviours:
    """__summary__"""

    @staticmethod
    def analyse_behaviours(
        behavs_fp: str,
        out_dir: str,
        configs_fp: str,
        # bins: list,
        # summary_func: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> str:
        """
        Takes a behavs dataframe and generates a summary and binned version of the data.
        """
        outcome = ""
        name = IOMixin.get_name(behavs_fp)
        out_dir = os.path.join(out_dir, AnalyseBehaviours.analyse_behaviours.__name__)
        # Calculating the deltas (changes in body position) between each frame for the subject
        configs = ExperimentConfigs.read_json(configs_fp)
        fps, _, _, _, bins_ls, cbins_ls = AnalyseDf.get_configs(configs)
        # Loading in dataframe
        behavs_df = BehavDf.read(behavs_fp)
        # Setting all na and -1 values to 0 (to make any undecided behav to non-behav)
        behavs_df = behavs_df.fillna(0).map(lambda x: np.maximum(0, x))
        # Getting the behaviour names and each user_behav for the behaviour
        # Not incl. the `pred` or `prob` (`prob` shouldn't be here anyway) columns
        columns = np.isin(
            behavs_df.columns.get_level_values(BehavDf.CN.OUTCOMES.value),
            [BehavColumns.PROB.value, BehavColumns.PRED.value],
            invert=True,
        )
        behavs_df = behavs_df.loc[:, columns]
        # Updating the column level names of behavs_df to match AnalyseDf structure
        behavs_df.columns.names = list(MiscMixin.enum2tuple(AnalyseDf.CN))
        # Writing the behavs_df to the fbf file
        fbf_fp = os.path.join(out_dir, "fbf", f"{name}.feather")
        AnalyseDf.write_feather(behavs_df, fbf_fp)
        # Making the summary and binned dataframes
        AnalyseBinnedDf.summary_binned_behavs(
            behavs_df,
            out_dir,
            name,
            fps,
            bins_ls,
            cbins_ls,
        )
        # Returning outcome
        return outcome
