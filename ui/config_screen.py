"""
Tkinter config screen — launches before the camera.

Lets you pick key, mode, MIDI channel, octave, and camera index.
Returns config dict when Start is clicked.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional


# Keys with enharmonic display
KEY_OPTIONS = [
    'C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F',
    'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B'
]

# Map display names back to sharp-only names for the engine
KEY_MAP = {
    'C': 'C', 'C#/Db': 'C#', 'D': 'D', 'D#/Eb': 'D#', 'E': 'E',
    'F': 'F', 'F#/Gb': 'F#', 'G': 'G', 'G#/Ab': 'G#', 'A': 'A',
    'A#/Bb': 'A#', 'B': 'B'
}


def show_config_screen() -> Optional[dict]:
    """
    Show the config screen. Blocks until Start is clicked or window is closed.
    Returns config dict or None if cancelled.
    """
    result = {'started': False}

    root = tk.Tk()
    root.title("MIDI Camera")
    root.geometry("340x380")
    root.resizable(False, False)

    # Try to set dark-ish appearance
    root.configure(bg='#1a1a1a')
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('.', background='#1a1a1a', foreground='#e0e0e0')
    style.configure('TLabel', background='#1a1a1a', foreground='#e0e0e0', font=('Helvetica', 12))
    style.configure('TCombobox', fieldbackground='#2a2a2a', background='#2a2a2a',
                     foreground='#e0e0e0')
    style.configure('TButton', background='#333333', foreground='#e0e0e0',
                     font=('Helvetica', 13, 'bold'))
    style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), foreground='#8aff8a')

    # Header
    header = ttk.Label(root, text="MIDI Camera", style='Header.TLabel')
    header.pack(pady=(20, 5))

    sub = ttk.Label(root, text="Hand Gesture MIDI Controller",
                    font=('Helvetica', 10), foreground='#888888')
    sub.pack(pady=(0, 15))

    # Config frame
    frame = tk.Frame(root, bg='#1a1a1a')
    frame.pack(padx=30, fill='x')

    # Key
    ttk.Label(frame, text="Key").grid(row=0, column=0, sticky='w', pady=5)
    key_var = tk.StringVar(value='C')
    key_combo = ttk.Combobox(frame, textvariable=key_var, values=KEY_OPTIONS,
                              state='readonly', width=12)
    key_combo.grid(row=0, column=1, sticky='e', pady=5, padx=(10, 0))

    # Mode
    ttk.Label(frame, text="Mode").grid(row=1, column=0, sticky='w', pady=5)
    mode_var = tk.StringVar(value='Major')
    mode_combo = ttk.Combobox(frame, textvariable=mode_var, values=['Major', 'Minor'],
                               state='readonly', width=12)
    mode_combo.grid(row=1, column=1, sticky='e', pady=5, padx=(10, 0))

    # MIDI Channel
    ttk.Label(frame, text="MIDI Channel").grid(row=2, column=0, sticky='w', pady=5)
    ch_var = tk.StringVar(value='1')
    ch_combo = ttk.Combobox(frame, textvariable=ch_var,
                             values=[str(i) for i in range(1, 17)],
                             state='readonly', width=12)
    ch_combo.grid(row=2, column=1, sticky='e', pady=5, padx=(10, 0))

    # Octave
    ttk.Label(frame, text="Octave").grid(row=3, column=0, sticky='w', pady=5)
    oct_var = tk.StringVar(value='3')
    oct_combo = ttk.Combobox(frame, textvariable=oct_var,
                              values=[str(i) for i in range(1, 7)],
                              state='readonly', width=12)
    oct_combo.grid(row=3, column=1, sticky='e', pady=5, padx=(10, 0))

    # Camera Index
    ttk.Label(frame, text="Camera").grid(row=4, column=0, sticky='w', pady=5)
    cam_var = tk.StringVar(value='0')
    cam_combo = ttk.Combobox(frame, textvariable=cam_var,
                              values=['0', '1', '2', '3'],
                              state='readonly', width=12)
    cam_combo.grid(row=4, column=1, sticky='e', pady=5, padx=(10, 0))

    frame.columnconfigure(1, weight=1)

    def on_start():
        result['started'] = True
        result['key'] = KEY_MAP.get(key_var.get(), 'C')
        result['mode'] = mode_var.get().lower()
        result['channel'] = int(ch_var.get()) - 1  # 0-indexed for MIDI
        result['octave'] = int(oct_var.get())
        result['camera'] = int(cam_var.get())
        root.destroy()

    # Start button
    start_btn = ttk.Button(root, text="Start", command=on_start)
    start_btn.pack(pady=25, ipadx=30, ipady=5)

    # Center window on screen
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - 340) // 2
    y = (sh - 380) // 2
    root.geometry(f"340x380+{x}+{y}")

    root.mainloop()

    if result['started']:
        return result
    return None
