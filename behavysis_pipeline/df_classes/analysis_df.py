import os
from enum import Enum

import pandas as pd
import seaborn as sns

from behavysis_pipeline.df_classes.df_mixin import DFMixin, FramesIN
from behavysis_pipeline.df_classes.keypoints_df import CoordsCols

FBF = "fbf"


class AnalysisCN(Enum):
    INDIVIDUALS = "individuals"
    MEASURES = "measures"


class AnalysisDf(DFMixin):
    """__summary__"""

    NULLABLE = False
    IN = FramesIN
    CN = AnalysisCN

    @classmethod
    def make_location_scatterplot(
        cls,
        scatter_df: pd.DataFrame,
        corners_df: pd.DataFrame,
        dst_fp,
        measure: str,
    ):
        """
        Expects analysis_df index levels to be (frame,),
        and column levels to be (individual, measure).
        """
        scatter_stacked_df = scatter_df.stack(level="individuals").reset_index("individuals")
        g = sns.relplot(
            data=scatter_stacked_df,
            x=CoordsCols.X.value,
            y=CoordsCols.Y.value,
            hue=measure,
            col="individuals",
            kind="scatter",
            col_wrap=2,
            height=8,
            aspect=0.5 * scatter_stacked_df["individuals"].nunique(),
            alpha=0.8,
            linewidth=0,
            marker=".",
            s=10,
            legend=True,
        )
        # Invert the y axis
        g.axes[0].invert_yaxis()
        # Adding region definition (from roi_df) to the plot
        corners_df = pd.concat(
            [corners_df, corners_df.groupby("roi").first().reset_index()],
            ignore_index=True,
        )
        for ax in g.axes:
            sns.lineplot(
                data=corners_df,
                x=CoordsCols.X.value,
                y=CoordsCols.Y.value,
                hue="roi",
                # color=(1, 0, 0),
                linewidth=1,
                marker="+",
                markeredgecolor=(1, 0, 0),
                markeredgewidth=2,
                markersize=5,
                estimator=None,
                sort=False,
                legend=False,
                ax=ax,
            )
            ax.set_aspect("equal")
        # Setting fig titles and labels
        g.set_titles(col_template="{col_name}")
        g.figure.subplots_adjust(top=0.85)
        g.figure.suptitle("Spatial position", fontsize=12)
        # Saving fig
        os.makedirs(os.path.dirname(dst_fp), exist_ok=True)
        g.savefig(dst_fp)
        g.figure.clf()
