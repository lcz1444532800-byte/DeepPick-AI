"""Prevent console flashes from third-party subprocess calls in a GUI app."""
import os
import subprocess


def hide_child_consoles():
    if os.name != 'nt' or getattr(subprocess.Popen, '_deeppick_hidden', False):
        return
    original = subprocess.Popen

    class HiddenPopen(original):
        _deeppick_hidden = True

        def __init__(self, *args, **kwargs):
            values = list(args)
            if len(values) > 13:
                values[13] |= subprocess.CREATE_NO_WINDOW
            else:
                kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
            super().__init__(*values, **kwargs)

    subprocess.Popen = HiddenPopen
