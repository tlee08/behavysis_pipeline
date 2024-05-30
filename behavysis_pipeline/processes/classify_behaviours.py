"""
Classify Behaviours
"""

import os

import numpy as np
import pandas as pd
from behavysis_core.constants import BEHAV_COLUMN_NAMES, BEHAV_INDEX_NAME, BehavColumns
from behavysis_core.data_models.experiment_configs import ExperimentConfigs
from behavysis_core.mixins.behav_mixin import BehavMixin
from behavysis_core.mixins.df_io_mixin import DFIOMixin
from behavysis_core.mixins.io_mixin import IOMixin

from behavysis_pipeline.behav_classifier import BehavClassifier

# TODO: handle reading the model file whilst in multiprocessing


class ClassifyBehaviours:
    """__summary__"""

    @staticmethod
    @IOMixin.overwrite_check()
    def classify_behaviours(
        features_fp: str,
        out_fp: str,
        configs_fp: str,
        overwrite: bool,
    ) -> str:
        """
        Given model config files in the BehavClassifier format, generates beahviour predidctions
        on the given extracted features dataframe.

        Parameters
        ----------
        features_fp : str
            _description_
        out_fp : str
            _description_
        configs_fp : str
            _description_
        overwrite : bool
            Whether to overwrite the output file (if it exists).

        Returns
        -------
        str
            Description of the function's outcome.

        Notes
        -----
        The config file must contain the following parameters:
        ```
        - user
            - classify_behaviours
                - models: list[str]
        ```
        Where the `models` list is a list of `model_config.json` filepaths.
        """
        outcome = ""
        # Getting necessary config parameters
        configs = ExperimentConfigs.read_json(configs_fp)
        configs_filt = configs.user.classify_behaviours
        models_ls = configs.get_ref(configs_filt.models)
        pcutoff = configs.get_ref(configs_filt.pcutoff)
        min_window_frames = configs.get_ref(configs_filt.min_window_frames)
        # Getting features data
        features_df = DFIOMixin.read_feather(features_fp)
        # Initialising y_preds df
        # Getting predictions for each classifier model and saving
        # in a list of pd.DataFrames
        behav_preds_ls = np.zeros(len(models_ls), dtype="object")
        for i, model in enumerate(models_ls):
            # Getting classifier probabilities
            clf = BehavClassifier(model)
            df_i = clf.model_predict(features_df)
            # Getting prob and pred column names
            prob_col = (clf.configs.name, BehavColumns.PROB.value)
            pred_col = (clf.configs.name, BehavColumns.PRED.value)
            # Using pcutoff to get binary predictions
            df_i[pred_col] = df_i[prob_col] > pcutoff
            df_i[pred_col] = df_i[pred_col].astype(int)
            # Filling in small non-behav bouts
            df_i[pred_col] = merge_bouts(df_i[pred_col], min_window_frames)
            # Saving df
            behav_preds_ls[i] = df_i
            # Logging outcome
            outcome += f"Completed {model} classification,\n"
        # Concatenating predictions to a single dataframe
        behavs_df = pd.concat(behav_preds_ls, axis=1)
        # Setting the index and column names
        behavs_df.index.name = BEHAV_INDEX_NAME
        behavs_df.columns.names = BEHAV_COLUMN_NAMES
        # Checking df
        BehavMixin.check_df(behavs_df)
        # Saving behav_preds df
        DFIOMixin.write_feather(behavs_df, out_fp)
        # Returning outcome
        return outcome


def merge_bouts(
    vect: pd.Series,
    min_window_frames: int,
) -> pd.DataFrame:
    """
    If the time between two bouts is less than `min_window_frames`, then merging
    the two bouts together by filling in the short `non-behav` period `is-behav`.

    Parameters
    ----------
    df : pd.DataFrame
        A scored_behavs dataframe.
    min_window_frames : int
        _description_

    Returns
    -------
    pd.DataFrame
        A scored_behavs dataframe, with the merged bouts.
    """
    vect = vect.copy()
    # Getting start, stop, and duration of each non-behav bout
    nonbouts_df = BehavMixin.vect_2_bouts(vect == 0)
    # For each non-behav bout, if less than min_window_frames, then call it a behav
    for _, row in nonbouts_df.iterrows():
        if row["dur"] < min_window_frames:
            vect.loc[row["start"] : row["stop"]] = 1
    # Returning df
    return vect
