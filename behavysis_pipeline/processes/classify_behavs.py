"""
Classify Behaviours
"""

import os

import pandas as pd

from behavysis_pipeline.behav_classifier.behav_classifier import BehavClassifier
from behavysis_pipeline.df_classes.behav_df import BehavPredictedDf, BehavScoredDf, BoutCols, OutcomesPredictedCols

# from behavysis_pipeline.df_classes.bouts_df import BoutColumns, BoutsDf
from behavysis_pipeline.df_classes.features_df import FeaturesDf
from behavysis_pipeline.pydantic_models.configs import ExperimentConfigs
from behavysis_pipeline.utils.diagnostics_utils import file_exists_msg
from behavysis_pipeline.utils.logging_utils import get_io_obj_content, init_logger_with_io_obj
from behavysis_pipeline.utils.misc_utils import get_current_func_name

# TODO: handle reading the model file whilst in multiprocessing


class ClassifyBehavs:
    """__summary__"""

    @classmethod
    def classify_behavs(
        cls,
        features_fp: str,
        behavs_fp: str,
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
        dst_fp : str
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
        logger, io_obj = init_logger_with_io_obj(get_current_func_name())
        if not overwrite and os.path.exists(behavs_fp):
            logger.warning(file_exists_msg(behavs_fp))
            return get_io_obj_content(io_obj)
        # Getting necessary config parameters
        configs = ExperimentConfigs.read_json(configs_fp)
        model_configs_ls = configs.user.classify_behavs
        # Getting features data
        features_df = FeaturesDf.read(features_fp)
        # Initialising y_preds df
        # Getting predictions for each classifier model and saving
        # in a list of pd.DataFrames
        behavs_df_ls = []
        for model_config in model_configs_ls:
            proj_dir = configs.get_ref(model_config.proj_dir)
            behav_name = configs.get_ref(model_config.behav_name)
            behav_model = BehavClassifier.load(proj_dir, behav_name)
            pcutoff = cls._get_pcutoff(configs.get_ref(model_config.pcutoff), behav_model.configs.pcutoff)
            min_window_frames = configs.get_ref(model_config.min_window_frames)
            # Running the clf pipeline
            behav_df_i = behav_model.pipeline_run(features_df)
            # Getting prob and pred column names
            prob_col = (behav_name, OutcomesPredictedCols.PROB.value)
            pred_col = (behav_name, OutcomesPredictedCols.PRED.value)
            # Using pcutoff to get binary predictions
            behav_df_i[pred_col] = (behav_df_i[prob_col] > pcutoff).astype(int)
            # Filling in small non-behav bouts
            behav_df_i[pred_col] = cls._merge_bouts(behav_df_i[pred_col], min_window_frames)
            # Adding model predictions df to list
            behavs_df_ls.append(behav_df_i)
            # Logging outcome
            logger.info(f"Completed {behav_name} classification.")
        # If no models were run, then return outcome
        if len(behavs_df_ls) == 0:
            return get_io_obj_content(io_obj)
        # Concatenating predictions to a single dataframe
        behavs_df = pd.concat(behavs_df_ls, axis=1)
        # Saving behav_preds df
        BehavPredictedDf.write(behavs_df, behavs_fp)
        return get_io_obj_content(io_obj)

    @staticmethod
    def _get_pcutoff(pcutoff: float, model_pcutoff: float) -> float:
        """
        Check if the pcutoff is valid.

        Also check if the pcutoff is the special value `-1`, in which case
        `model_pcutoff` is used.
        """
        # Checking if pcutoff is -1, then using model_pcutoff
        if pcutoff == -1:
            # Checking if model_pcutoff is valid
            assert 0 <= model_pcutoff <= 1, (
                "pcutoff is relying on the model's pcutoff.\n"
                f"But the model's pcutoff is invalid: {model_pcutoff}.\n"
                "Must be between 0 and 1."
            )
            return model_pcutoff
        assert 0 <= pcutoff <= 1, (
            "pcutoff in configs must be between 0 and 1, or the special value -1.\n" f"Instead it has value: {pcutoff}"
        )
        return pcutoff

    @staticmethod
    def _merge_bouts(
        vect: pd.Series,
        min_window_frames: int,
    ) -> pd.Series:
        """
        For a given pd.Series, `vect`,
        if the time between two bouts is less than `min_window_frames`, then merging
        the two bouts together by filling in the short `non-behav` period with `is-behav`.

        Parameters
        ----------
        vect : pd.Series
            A scored_behavs pd.Series.
        min_window_frames : int
            _description_

        Returns
        -------
        pd.DataFrame
            A scored_behavs dataframe, with the merged bouts.
        """
        vect = vect.copy()
        # Getting start, stop, and duration of each non-behav bout
        nonbouts_df = BehavScoredDf.vect2bouts(vect == 0)
        # For each non-behav bout, if less than min_window_frames, then call it a behav
        for _, row in nonbouts_df.iterrows():
            if row[BoutCols.DUR.value] < min_window_frames:
                vect.loc[row[BoutCols.START.value] : row[BoutCols.STOP.value]] = 1
        return vect
