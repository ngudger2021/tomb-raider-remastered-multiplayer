# SPDX-License-Identifier: GPL-3.0-only
"""Native desktop UI using the original Burn's Mods Windows branding."""
from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, messagebox
import queue
import webbrowser

ASSETS = Path(__file__).resolve().parent / 'assets'
BG, PANEL, TEXT, MUTED, ORANGE = '#010101', '#141312', '#f5f3f0', '#9ca3af', '#fb6010'
LINKS = [('discord', 'Discord', 'https://discord.gg/DJrkR77HJD'),
         ('github', 'GitHub', 'https://github.com/burn-sours/tomb-raider-remastered-multiplayer'),
         ('support', 'Donate', 'https://ko-fi.com/burn_sours'),
         ('speedrun', 'Speedruns', 'https://www.speedrun.com/tr123456_remastered_ce')]
DESCRIPTIONS = {
    'infinite-oxygen': 'Keep breathing while Lara is underwater.',
    'infinite-health': 'Refill health while Lara is alive.',
    'no-fall-damage': 'Limit falling speed on dry ground.',
    'super-jump': 'Give Lara a much higher jump.',
}


def create_window(controller, settings_path, log_path, version, features):
    win = tk.Tk(className='SuperLara')
    win.title("Burn's Mods — Super Lara (Linux)")
    win.geometry('800x760')
    win.minsize(760, 740)
    win.configure(background=BG)
    # Retain every PhotoImage for the complete window lifetime.
    images = {name: tk.PhotoImage(file=str(ASSETS / 'images' / name))
              for name in ['burn.png', 'burn_256.png', 'logo.png']}
    win.iconphoto(True, images['burn_256.png'], images['burn.png'])
    images['header'] = images['logo.png'].subsample(12)
    for name in ['discord', 'github', 'support', 'speedrun', 'stopModsButton', 'selectExeButton']:
        images[name] = tk.PhotoImage(file=str(ASSETS / 'icons' / (name + '.png')))
    win.branding_images = images
    style = ttk.Style(win)
    style.theme_use('clam')
    style.configure('.', background=BG, foreground=TEXT, font=('Sans', 10))
    style.configure('TFrame', background=BG)
    style.configure('Panel.TFrame', background=PANEL)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Title.TLabel', font=('Sans', 20, 'bold'))
    style.configure('Section.TLabel', font=('Sans', 16, 'bold'), foreground=ORANGE)
    style.configure('State.TLabel', font=('Sans', 12, 'bold'))
    style.configure('TButton', background='#262321', foreground=TEXT, padding=(10, 8))
    style.map('TButton', background=[('active', '#3b2b22')], foreground=[('active', '#ffffff')])
    style.configure('Link.TButton', background=BG, font=('Sans', 8), padding=(5, 3), borderwidth=0)
    style.configure('Mod.TCheckbutton', background=PANEL, foreground=TEXT, font=('Sans', 12, 'bold'), padding=4)
    style.map('Mod.TCheckbutton', background=[('active', '#24201d')], foreground=[('selected', ORANGE)])
    style.configure('Help.TLabel', background=PANEL, foreground=MUTED, font=('Sans', 10))

    header = ttk.Frame(win, padding=(22, 12))
    header.pack(fill='x')
    ttk.Label(header, image=images['header']).pack(side='left', padx=(0, 16))
    title = ttk.Frame(header)
    title.pack(side='left')
    ttk.Label(title, text="Burn’s Mods", style='Title.TLabel').pack(anchor='w')
    ttk.Label(title, text='Super Lara · Linux beta', style='Muted.TLabel').pack(anchor='w', pady=(4, 0))
    links = ttk.Frame(header)
    links.pack(side='right')
    for name, label, url in LINKS:
        ttk.Button(links, image=images[name], text=label, compound='top', style='Link.TButton',
                   command=lambda target=url: webbrowser.open(target), takefocus=True).pack(side='left', padx=3)
    tk.Frame(win, height=1, background='#2a2522').pack(fill='x')
    body = ttk.Frame(win, padding=(26, 20))
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Super Lara', style='Section.TLabel').pack(anchor='w')
    ttk.Label(body, text='Tomb Raider I–III Remastered', style='Muted.TLabel').pack(anchor='w', pady=(4, 15))
    state = tk.StringVar(value='Connecting…')
    detail = tk.StringVar(value='Looking for your Steam game…')
    state_label = ttk.Label(body, textvariable=state, style='State.TLabel')
    state_label.pack(anchor='w')
    ttk.Label(body, textvariable=detail, wraplength=730, style='Muted.TLabel').pack(anchor='w', pady=(5, 15))
    panel = ttk.Frame(body, padding=(14, 8), style='Panel.TFrame')
    panel.pack(fill='x')
    variables = {key: tk.BooleanVar(value=False) for key in features}
    pref = Path(settings_path)
    try:
        settings = json.loads(pref.read_text())
    except (OSError, ValueError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}

    def change():
        requested = {key: variable.get() for key, variable in variables.items()}
        try:
            tmp = pref.with_suffix('.tmp')
            tmp.write_text(json.dumps({'preferred_features': requested}, indent=2) + '\n')
            tmp.replace(pref)
        except OSError as exc:
            controller.diag('settings', str(exc))
            messagebox.showwarning('Settings could not be saved', str(exc), parent=win)
        controller.features = requested
        controller.diag('control', f'features requested={requested}')

    checkboxes = {}
    for key, label in features.items():
        row = ttk.Frame(panel, padding=(0, 5), style='Panel.TFrame')
        row.pack(fill='x')
        checkboxes[key] = ttk.Checkbutton(row, text=label, variable=variables[key], command=change, style='Mod.TCheckbutton')
        checkboxes[key].pack(anchor='w')
        ttk.Label(row, text=DESCRIPTIONS[key], style='Help.TLabel').pack(anchor='w', padx=(28, 0))
    ttk.Label(body, text='Closing this app stops all mods. Every new session starts with mods off.',
              style='Muted.TLabel', wraplength=730).pack(anchor='w', pady=(14, 8))
    preferred = settings.get('preferred_features', {})
    saved = ', '.join(features[key] for key in features if isinstance(preferred, dict) and preferred.get(key))
    if saved:
        ttk.Label(body, text='Saved preferences: ' + saved, style='Muted.TLabel', wraplength=730).pack(anchor='w', pady=(0, 8))
    buttons = ttk.Frame(body)
    buttons.pack(fill='x', pady=(5, 0))

    def disable_all():
        for variable in variables.values():
            variable.set(False)
        change()

    def show_log():
        pane = tk.Toplevel(win)
        pane.title('Super Lara diagnostic log')
        pane.geometry('900x500')
        box = tk.Text(pane, background=PANEL, foreground=TEXT, insertbackground=TEXT, wrap='word', font=('Monospace', 10))
        scrollbar = ttk.Scrollbar(pane, orient='vertical', command=box.yview)
        scrollbar.pack(side='right', fill='y')
        box.configure(yscrollcommand=scrollbar.set)
        box.pack(fill='both', expand=True)
        log = Path(log_path)
        box.insert('1.0', log.read_text()[-60000:] if log.exists() else 'No log yet')
        box.configure(state='disabled')

    stop = ttk.Button(buttons, image=images['stopModsButton'], text='Disable all mods', compound='left', command=disable_all)
    stop.pack(side='left', padx=(0, 12))
    ttk.Button(buttons, image=images['selectExeButton'], text='Diagnostic log', compound='left', command=show_log).pack(side='left')
    footer = ttk.Frame(win, padding=(26, 12))
    footer.pack(fill='x', side='bottom')
    ttk.Label(footer, text=f'Linux beta {version} · Steam patch 5.4', style='Muted.TLabel').pack(anchor='w')
    ttk.Label(footer, text='Based on Burn’s Mods by burn_sours · GPL-3.0-only · Independent Linux adaptation',
              style='Muted.TLabel', font=('Sans', 9)).pack(anchor='w', pady=(4, 0))

    update_id = None

    def update():
        nonlocal update_id
        latest = None
        try:
            while True:
                latest = controller.events.get_nowait()
        except queue.Empty:
            pass
        if latest:
            state.set(latest['state'])
            detail.set(latest['detail'])
            status = latest['state']
            color = '#59ca81' if status == 'Mods active' else '#f08462' if status in ('Connection failure', 'Unsupported build') else TEXT
            state_label.configure(foreground=color)
            if status in ('Connection failure', 'Unsupported build'):
                for variable in variables.values():
                    variable.set(False)
        update_id = win.after(150, update)

    def close():
        if update_id is not None:
            win.after_cancel(update_id)
        controller.shutdown()
        win.destroy()

    win.protocol('WM_DELETE_WINDOW', close)
    update()
    return win, {'variables': variables, 'checkboxes': checkboxes, 'stop': stop, 'state': state, 'close': close}


def run_ui(controller, settings_path, log_path, version, features):
    win, _ = create_window(controller, settings_path, log_path, version, features)
    win.mainloop()
