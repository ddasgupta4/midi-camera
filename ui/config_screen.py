"""
Tkinter config screen — launches before the camera.

Lets you pick key, mode, MIDI channel, octave, and camera index.
Returns config dict when Start is clicked.
Uses tk.OptionMenu for reliable rendering on macOS.
"""

import tkinter as tk
from typing import Optional


KEY_OPTIONS = [
    'C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F',
    'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B'
]

KEY_MAP = {
    'C': 'C', 'C#/Db': 'C#', 'D': 'D', 'D#/Eb': 'D#', 'E': 'E',
    'F': 'F', 'F#/Gb': 'F#', 'G': 'G', 'G#/Ab': 'G#', 'A': 'A',
    'A#/Bb': 'A#', 'B': 'B'
}

BG = '#1a1a1a'
FG = '#e0e0e0'
ACCENT = '#8aff8a'
ENTRY_BG = '#2a2a2a'
BTN_BG = '#333333'
FONT = ('Helvetica', 13)
FONT_BOLD = ('Helvetica', 13, 'bold')
FONT_HEADER = ('Helvetica', 18, 'bold')
FONT_SUB = ('Helvetica', 10)


def make_option_menu(parent, var, options, width=12):
    """Create a styled OptionMenu that renders reliably on macOS."""
    menu = tk.OptionMenu(parent, var, *options)
    menu.config(
        bg=ENTRY_BG, fg=FG, activebackground='#444444', activeforeground=FG,
        highlightthickness=0, relief='flat', font=FONT, width=width,
        indicatoron=True, bd=0
    )
    menu['menu'].config(bg=ENTRY_BG, fg=FG, activebackground='#444444',
                        activeforeground=FG, font=FONT)
    return menu


def show_config_screen() -> Optional[dict]:
    """
    Show the config screen. Blocks until Start is clicked or window is closed.
    Returns config dict or None if cancelled.
    """
    result = {'started': False}

    root = tk.Tk()
    root.title("MIDI Camera")
    root.geometry("360x400")
    root.resizable(False, False)
    root.configure(bg=BG)

    # Header
    tk.Label(root, text="MIDI Camera", bg=BG, fg=ACCENT,
             font=FONT_HEADER).pack(pady=(24, 4))
    tk.Label(root, text="Hand Gesture MIDI Controller", bg=BG,
             fg='#888888', font=FONT_SUB).pack(pady=(0, 18))

    # Config grid
    frame = tk.Frame(root, bg=BG)
    frame.pack(padx=36, fill='x')

    def row(label, var, options, r):
        tk.Label(frame, text=label, bg=BG, fg=FG, font=FONT,
                 anchor='w').grid(row=r, column=0, sticky='w', pady=7)
        m = make_option_menu(frame, var, options)
        m.grid(row=r, column=1, sticky='e', pady=7, padx=(10, 0))

    key_var   = tk.StringVar(value='C')
    mode_var  = tk.StringVar(value='Major')
    ch_var    = tk.StringVar(value='1')
    oct_var   = tk.StringVar(value='3')
    cam_var   = tk.StringVar(value='0')

    row("Key",         key_var,  KEY_OPTIONS,                   0)
    row("Mode",        mode_var, ['Major', 'Minor'],            1)
    row("MIDI Channel",ch_var,   [str(i) for i in range(1,17)],2)
    row("Octave",      oct_var,  [str(i) for i in range(1, 7)],3)
    row("Camera",      cam_var,  ['0', '1', '2', '3'],          4)

    frame.columnconfigure(1, weight=1)

    def on_start():
        result['started'] = True
        result['key']     = KEY_MAP.get(key_var.get(), 'C')
        result['mode']    = mode_var.get().lower()
        result['channel'] = int(ch_var.get()) - 1   # 0-indexed for MIDI
        result['octave']  = int(oct_var.get())
        result['camera']  = int(cam_var.get())
        root.destroy()

    tk.Button(
        root, text="Start", command=on_start,
        bg=BTN_BG, fg=FG, activebackground='#555555', activeforeground=FG,
        font=FONT_BOLD, relief='flat', padx=30, pady=8, cursor='hand2',
        bd=0, highlightthickness=0
    ).pack(pady=28)

    # Center on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth()  - 360) // 2
    y = (root.winfo_screenheight() - 400) // 2
    root.geometry(f"360x400+{x}+{y}")

    root.mainloop()

    return result if result['started'] else None
