from typing import Optional

import numpy as np

DIAGNOSTICS_SUCCESS_MESSAGES = (
    "Success! Success! Success!!",
    "Done and DONE!!",
    "Yay! Completed!",
    "This process was completed. Good on you :)",
    "Thumbs up!",
    "Woohoo!!!",
    "Phenomenal!",
    ":) :) :) :) :)",
    "Go you!",
    "You are doing awesome!",
    "You got this!",
    "You're doing great!",
    "Sending good vibes.",
    "I believe in you!",
    "You're a champion!",
    "No task too tall :) :)",
    "A job done well, and a well done job!",
    "Top job!",
)


def success_msg() -> str:
    """
    Return a random positive message :)
    """
    return f"SUCCESS: {np.random.choice(DIAGNOSTICS_SUCCESS_MESSAGES)}\n"


def file_exists_msg(fp: Optional[str] = None) -> str:
    """
    Return a warning message.
    """
    fp_str = f", {fp}, " if fp else " "
    return f"Output file{fp_str}already exists - not overwriting file.\n" "To overwrite, specify `overwrite=True`.\n"
