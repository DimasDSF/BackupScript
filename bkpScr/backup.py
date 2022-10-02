import datetime
import io
import os
import sys
import time
import json
import shutil
import stat
import math
import socket
import urllib.request
import argparse
import locale
import platform
from pathlib import Path
from functools import cached_property, partial, reduce
import operator

from msvcrt import getch
from msvcrt import kbhit

from typing import Dict, Set, List, Optional, Callable, Union

HARD_CONFIG_VER = 2
LATEST_VER_DATA_URL = "https://raw.githubusercontent.com/DimasDSF/BackupScript/master/bkpScr/version.json"
class Arguments(object):
    def __init__(self):
        self.args: argparse.Namespace = argparse.Namespace()

    def update_args(self, args):
        self.args = args


launch_args = Arguments()

MAX_MODIFICATION_TIME_ERROR_OFFSET = 5

class ManageModes(object):
    M_MODE_DEFAULT = 'default'
    M_MODE_SNAPSHOT = 'snapshot'
    M_MODE_SYNC = 'sync'

    @staticmethod
    def all_types() -> List[str]:
        return [y for x, y in ChangeTypes.__dict__.items() if x.startswith('M_MODE')]


try:
    if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")):
        def config_updater():
            cm = config['config_version']
            if cm < 1:
                print("Config File is Corrupted, deleting to regenerate.")
                os.system('pause')
                os.remove(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"))
                print('Restart to generate new config')
                time.sleep(3)
                sys.exit()
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), "r", encoding='utf-8') as data:
            config = json.load(data)
            if config.get("config_version") < HARD_CONFIG_VER:
                print("Config Format Update Required.")
                print("Creating Config Backup")
                time.sleep(4)
                ts = int(time.time())
                shutil.copy2(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), os.path.join(os.path.dirname(os.path.realpath(__file__)), "old_config_{0}.json.bkp".format(ts)))
                print("Created a config Backup: old_config_{0}.json.bkp\nLaunching Modifier.".format(ts))
                time.sleep(2)
                while config['config_version'] < HARD_CONFIG_VER:
                    pre_ver = config.copy()['config_version']
                    config_updater()
                    after_ver = config['config_version']
                    print("Updated Config from version {0} to {1}".format(pre_ver, after_ver))
                print("Config Update Finished, Restart.")
                time.sleep(4)
                sys.exit()
    else:
        config = {
            "config_version": HARD_CONFIG_VER,
            "backup_dirs": [
                {
                    "path": "SourcePath_Here",
                    "subpath": None,
                    "force_backup": False,
                    "mode": ManageModes.M_MODE_DEFAULT,
                    "ignored_paths": []
                }
            ],
            "path_reduction": 0,
            "local_backup_root_folder": "bkp",
            "tz": {
                "hours": 0,
                "minutes": 0
            }
        }
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), "w+", encoding='utf-8') as data:
            json.dump(config, data, indent=4)
        print("Setup Config and Restart.")
        time.sleep(5)
        sys.exit()
except json.JSONDecodeError as e:
    print("Config Init Failed due to a JSON Decoding Error. {0}\n{1}".format(type(e).__name__, e.args))
    print("\nMake sure to properly escape back slashes or use forward slashes.\n\\->\\\\ or \\ -> /")
    os.system('pause')
    raise e
except Exception as e:
    print("Config Init Failed. Exception: {0}\n{1}".format(type(e).__name__, e.args))
    os.system('pause')
    raise e

try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "version.json"), "r") as data:
        version = json.load(data)
except Exception as e:
    version = dict()
    print("Version Data Unavailable.")

def get_cur_dt():
    return datetime.datetime.now(shift_tz)

def deep_get(data, vals: list, default: any = None, *, return_none: bool = False):
    def _getter(__a, __b):
        try:
            return operator.getitem(__a, __b)
        except TypeError as _e:
            try:
                if hasattr(__a, __b):
                    return getattr(__a, __b)
            except:
                raise _e
    try:
        return reduce(_getter, vals, data)
    except (KeyError, IndexError, NameError) as _e:
        if default is not None or return_none:
            return default
        else:
            raise

def get_first_available(data, keys: list, default: any = None):
    for k in keys:
        try:
            if isinstance(k, list):
                return deep_get(data, k)
            elif isinstance(k, (str, int)):
                return data[k]
        except:
            continue
    return default

############################
#        CLI Utils         #
############################
def terminal_size():
    _ts = os.get_terminal_size()
    return dict(height=_ts.lines, width=_ts.columns)

def count_lines(msg: str, limit: Optional[int] = None):
    cur_line_chars = 0
    lines = 0
    if limit is None:
        limit = terminal_size()['width']
    for char in msg:
        cur_line_chars += 1
        while cur_line_chars >= limit:
            cur_line_chars -= limit
            lines += 1
        if char == "\n":
            lines += 1
            cur_line_chars = 0
    if cur_line_chars > 0:
        lines += 1
    return lines

class ANSIEscape(object):
    ESC = "\x1b"
    CSI = "\x1b["
    OSC = "\x1b]"
    CONTROLSYMBOL_clear_after_cursor = "\x1b[0K"

    class ForegroundTextColor(object):
        black = 30
        red = 31
        green = 32
        yellow = 33
        blue = 34
        magenta = 35
        cyan = 36
        white = 37
        extended = 38
        default = 39
        bright_black = 90
        bright_red = 91
        bright_green = 92
        bright_yellow = 93
        bright_blue = 94
        bright_magenta = 95
        bright_cyan = 96
        bright_white = 97

    class BackgroundTextColor(object):
        black = 40
        red = 41
        green = 42
        yellow = 43
        blue = 44
        magenta = 45
        cyan = 46
        white = 47
        extended = 48
        default = 49
        bright_black = 100
        bright_red = 101
        bright_green = 102
        bright_yellow = 103
        bright_blue = 104
        bright_magenta = 105
        bright_cyan = 106
        bright_white = 107

    @staticmethod
    def enable_ansi_escape():
        if os.name == 'nt' and platform.release() == '10' and platform.version() >= '10.0.14393':
            import ctypes
            from ctypes import wintypes
            try:
                kernel32 = ctypes.windll.kernel32
                outhandle = kernel32.GetStdHandle(-11)
                kernel32.SetConsoleMode(outhandle, 7)
            except WindowsError as err:
                if err.winerror == 0x0057:  # ERROR_INVALID_PARAMETER
                    raise NotImplementedError
                raise
        elif os.name == 'posix':
            pass
        else:
            raise OSError("ANSI Escape Character Support is Unavailable.")

    @staticmethod
    def is_ansi_escape_available():
        if (os.name == 'nt' and platform.release() == '10' and platform.version() >= '10.0.14393') or os.name == 'posix':
            return True
        return False

    @staticmethod
    def is_ansi_escape_enabled():
        if os.name == 'nt' and platform.release() == '10' and platform.version() >= '10.0.14393':
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL('kernel32')
            mode = wintypes.DWORD()
            kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(mode))
            return (mode.value & 0x0004) > 0
        elif os.name == 'posix':
            return True
        return False

    @staticmethod
    def ansi_escape_ready():
        if ANSIEscape.is_ansi_escape_enabled():
            return True
        if ANSIEscape.is_ansi_escape_available():
            try:
                ANSIEscape.enable_ansi_escape()
                return True
            except:
                pass
        return False

    @staticmethod
    def set_cursor_to_top_line():
        sys.__stdout__.write(f'{ANSIEscape.CSI}H\r')
        sys.__stdout__.flush()

    @staticmethod
    def set_cursor_pos(column: int = 1, line: int = 1):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{line};{column}f")
        sys.__stdout__.flush()

    @staticmethod
    def save_cursor_pos(restore: bool = False):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{'u' if restore else 's'}")
        sys.__stdout__.flush()

    @staticmethod
    def move_cursor_n_lines(lines: int = 1, up: bool = True):
        """
        Moves the cursor to the beginning of the line n lines up/down
        """
        sys.__stdout__.write(f"{ANSIEscape.CSI}{lines}{'F' if up else 'E'}")
        sys.__stdout__.flush()

    @staticmethod
    def move_cursor(vertical: int = 0, horizontal: int = 0):
        if vertical != 0:
            up = vertical > 0
            sys.__stdout__.write(f"{ANSIEscape.CSI}{abs(vertical)}{'A' if up else 'B'}")
        if horizontal != 0:
            right = horizontal > 0
            sys.__stdout__.write(f"{ANSIEscape.CSI}{abs(horizontal)}{'C' if right else 'D'}")
        sys.__stdout__.flush()

    @staticmethod
    def move_cursor_to_column(column: int = 1):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{column}G")
        sys.__stdout__.flush()

    @staticmethod
    def set_cursor_display(show: bool = True):
        sys.__stdout__.write(f'{ANSIEscape.CSI}?25{"h" if show else "l"}')
        sys.__stdout__.flush()

    @staticmethod
    def set_cursor_blinking(enable: bool = True):
        sys.__stdout__.write(f'{ANSIEscape.CSI}?12{"h" if enable else "l"}')
        sys.__stdout__.flush()

    @staticmethod
    def insert_lines(num: int = 1):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{num}L")
        sys.__stdout__.flush()

    @staticmethod
    def delete_lines(num: int = 1):
        if num-1 > 0:
            ANSIEscape.move_cursor_n_lines(num-1, True)
        sys.__stdout__.write(f"{ANSIEscape.CSI}{num}M")
        sys.__stdout__.flush()

    @staticmethod
    def clear_current_line(after_cursor: bool = False):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{'0' if after_cursor else '2'}K")
        sys.__stdout__.flush()

    @staticmethod
    def clear_console_text():
        sys.__stdout__.write(f'{ANSIEscape.CSI}H\r')
        sys.__stdout__.write(f'{ANSIEscape.CSI}J\r')
        sys.__stdout__.flush()

    @staticmethod
    def set_window_title(text: str):
        text = text[:255]  # Title can only be less or equal to 255 characters
        sys.__stdout__.write(f"{ANSIEscape.OSC}2;{text}\x07")  # Terminating character is "Bell" \x07

    @staticmethod
    def set_scrolling_margins(top: int = None, bottom: int = None):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{top if isinstance(top, int) else ''};{bottom if isinstance(bottom, int) else ''}r")
        sys.__stdout__.flush()

    @staticmethod
    def alternate_screen_buffer(enable: bool):
        sys.__stdout__.write(f"{ANSIEscape.CSI}?1049{'h' if enable else 'l'}")

    @staticmethod
    def get_graphics_mode_changer(*, foreground_color: int = None, background_color: int = None, extended_foreground: tuple = (255, 255, 255), extended_background: tuple = (0, 0, 0)):
        parameters = ""
        if foreground_color is not None:
            parameters += f"{';' if len(parameters) > 0 else ''}{foreground_color}"
        if foreground_color == ANSIEscape.ForegroundTextColor.extended:
            parameters += f"{';' if len(parameters) > 0 else ''}{';'.join([hex(x)[2:] for x in extended_foreground])}"
        if background_color is not None:
            parameters += f"{';' if len(parameters) > 0 else ''}{background_color}"
        if background_color == ANSIEscape.BackgroundTextColor.extended:
            parameters += f"{';' if len(parameters) > 0 else ''}{';'.join([hex(x)[2:] for x in extended_background])}"
        return f"{ANSIEscape.CSI}{parameters}m"

    @staticmethod
    def set_graphics_mode(*, foreground_color: int = None, background_color: int = None, extended_foreground: tuple = (255, 255, 255), extended_background: tuple = (0, 0, 0)):
        sys.__stdout__.write(ANSIEscape.get_graphics_mode_changer(foreground_color=foreground_color,
                                                                  background_color=background_color,
                                                                  extended_foreground=extended_foreground,
                                                                  extended_background=extended_background))

    @staticmethod
    def set_text_underline(enable: bool = False):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{'4' if enable else '24'}m")

    @staticmethod
    def swap_colors(negative: bool = True):
        sys.__stdout__.write(f"{ANSIEscape.CSI}{'7' if negative else '27'}m")

    @staticmethod
    def get_graphics_mode_reset_char(text: bool = False, background: bool = False):
        return f"{ANSIEscape.CSI}{'0' if text and background else ANSIEscape.ForegroundTextColor.default if text else ANSIEscape.BackgroundTextColor.default}m"

    @staticmethod
    def reset_graphics_mode(text: bool = False, background: bool = False):
        sys.__stdout__.write(ANSIEscape.get_graphics_mode_reset_char(text, background))

    @staticmethod
    def get_colored_text(text: str, text_color: int = None, background_color: int = None):
        if text_color is None and background_color is None:
            return text
        return f"{ANSIEscape.get_graphics_mode_changer(foreground_color=text_color, background_color=background_color)}{text}{ANSIEscape.get_graphics_mode_reset_char(text=True, background=True)}"

    @staticmethod
    def set_drawing_mode(enable: bool):
        sys.__stdout__.write(f"{ANSIEscape.ESC}{'(0' if enable else '(B'}")

def clear_terminal():
    if ANSIEscape.ansi_escape_ready():
        ANSIEscape.clear_console_text()
    else:
        os.system('cls' if sys.platform.lower() == "win32" else 'clear')
        sys.stdout.flush()

def get_specific_character(numericonly, inplist: (list, tuple) = ()):
    if kbhit():
        character = getch().lower()
        try:
            character = character.decode()
        except:
            try:
                character = character.decode(encoding=locale.getdefaultlocale()[1])
            except:
                character = None
        if character is not None:
            if numericonly:
                if character.isnumeric():
                    character = int(character)
                    if character in inplist or len(inplist) == 0:
                        return character
            else:
                if character in inplist or len(inplist) == 0:
                    return character
    else:
        time.sleep(0.1)

def selection_menu(numericonly, inplist: (list, tuple) = (), text="", cls=False, timeout: int = None, *, text_end: str = None):
    if cls:
        clear_terminal()
    if len(text) > 0:
        if text_end is None:
            text_end = '\n'
        print(text, end=text_end, flush=True)
    ch = None
    if timeout is not None:
        endtime = time.time() + timeout
    else:
        endtime = -1
    while time.time() < endtime or timeout is None:
        ch = get_specific_character(numericonly, inplist)
        if ch is not None:
            if ch in inplist or len(inplist) == 0:
                return ch
    else:
        raise TimeoutError('Selection Timed Out.')

def splitintochunks(inlist, n):
    for i in range(0, len(inlist), n):
        yield inlist[i:i + n]

class SelectionCancelledException(Exception):
    pass

def item_selection_menu(text: str = "", items: list = (), *, return_none_on_cancel: bool = True, item_name_function: Callable = None):
    if len(items) <= 0:
        return None
    if item_name_function is None:
        item_name_function = str
    _cur_page = 0
    _pages = list(splitintochunks(items, 8))
    while True:
        try:
            clear_terminal()
            _controls = [0]
            _controls_desc = []
            if _cur_page == 0:
                _controls_desc.append("0: Cancel")
            else:
                _controls_desc.append("0: Prev Page")
            if _cur_page + 1 < len(_pages):
                _controls.append(9)
                _controls_desc.append("9: Next Page")
            _selection = selection_menu(True, _controls + list(range(1, len(_pages[_cur_page]) + 1)), "{0}\n{1}\n{2}\n{3}".format(text, f"Page: {_cur_page}", "".join([f'{newline_character}{n+1}: {item_name_function(x)}' for n, x in enumerate(_pages[_cur_page])]), newline_character.join(reversed(_controls_desc))))
            if _selection in _controls:
                if _selection == 0:
                    if _cur_page > 0:
                        _cur_page -= 1
                    else:
                        raise KeyboardInterrupt()
                if _selection == 9:
                    if _cur_page + 1 < len(_pages):
                        _cur_page += 1
            else:
                return _pages[_cur_page][_selection-1]
        except KeyboardInterrupt:
            if return_none_on_cancel:
                return None
            raise SelectionCancelledException("Cancelled")

def confirmation_menu(text="", *, print_selection: bool = False):
    ch = selection_menu(False, ('y', 'n'), text, text_end='' if print_selection else None)
    if ch == 'y':
        if print_selection and len(text) > 0:
            print(" Y")
        return True
    if print_selection and len(text) > 0:
        print(" N")
    return False


def get_progress_bar(perc: float):
    status_slots = 50
    status_bars = math.floor((perc / 100) * status_slots)
    status_line = '['
    for n in range(status_bars):
        status_line = status_line + '░'
    if math.floor(status_slots - status_bars) > 0:
        for n in range(status_slots - status_bars):
            status_line = status_line + ' '
    return "{}]".format(status_line)

def format_bytes(bytesn):
    negative = abs(bytesn) > bytesn
    if bytesn is None:
        return 'N/A'
    if type(bytesn) is str:
        bytesn = float(bytesn)
    bytesn = abs(bytesn)
    if bytesn == 0.0:
        exponent = 0
    else:
        exponent = int(math.log(bytesn, 1024.0))
    suffix = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'][exponent]
    converted = float(bytesn) / float(1024 ** exponent)
    return '%s%.2f%s' % ("-" if negative else "", converted, suffix)

############################


bkp_root = config['local_backup_root_folder']
shift_tz = datetime.timezone(datetime.timedelta(hours=config['tz'].get('hours', 0), minutes=config['tz'].get('minutes', 0)))
path_reduction = config.get('path_reduction', None)
path_reduction = None if path_reduction == 0 else path_reduction
notzformat = '{:%d-%m-%Y %H:%M:%S}'
newline_character = "\n"

#####################################################
# Version Check
#####################################################
def connection_available(timeout=3):
    """
    Check if Internet Connection is available
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except socket.error:
        return False

def is_latest_version():
    if connection_available():
        try:
            if LATEST_VER_DATA_URL != "":
                with urllib.request.urlopen(LATEST_VER_DATA_URL) as url:
                    vdata = json.loads(url.read().decode())
        except:
            return None
        else:
            try:
                latest_cr: str = vdata.get("coderev", "Unavailable")
                current_cr: str = version.get('coderev', "Unavailable")
                if latest_cr.isnumeric() and current_cr.isnumeric():
                    if int(current_cr) == int(latest_cr):
                        return [True, vdata, False]
                    elif int(current_cr) > int(latest_cr):
                        return [True, vdata, True]
            except:
                return None
        return [False, vdata, False]
    else:
        return None

def dl_update():
    github_raw_links = [
        {
            "url": LATEST_VER_DATA_URL,
            "type": "json",
            "name": "version.json"
        },
        {
            "url": "https://raw.githubusercontent.com/DimasDSF/BackupScript/master/bkpScr/backup.py",
            "type": "py",
            "name": "backup.py"
        }
    ]
    try:
        for filedata in github_raw_links:
            with urllib.request.urlopen(filedata['url']) as dld_data:
                if filedata['type'] == "json":
                    j = json.loads(dld_data.read().decode())
                    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), filedata['name']), "w+") as dl:
                        json.dump(j, dl, indent=4)
                elif filedata['type'] == "py":
                    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), filedata['name']), "w+") as dl:
                        text = dld_data.read().decode(encoding=locale.getdefaultlocale()[1])
                        dl.write(text)
    except Exception as update_exception:
        print(ANSIEscape.get_colored_text("Update Failed due to an Exception: {0} / {1}".format(type(update_exception).__name__, update_exception.args), ANSIEscape.ForegroundTextColor.red))
    else:
        print("Update Finished.\nRestarting", end="")
        for t in range(3):
            print(".", end="")
            sys.stdout.flush()
            time.sleep(1)
        python = sys.executable
        os.execl(python, python, *sys.argv)

#####################################################

############################################
# shutil replacement with callback support #
############################################
def copy_with_callback(src, dst, *, follow_symlinks=True, callback: Callable[[int, int], None] = None):
    """Copy data and metadata. Return the file's destination.
    Metadata is copied with copystat(). Please see the copystat function
    for more information.
    The destination may be a directory.
    If follow_symlinks is false, symlinks won't be followed. This
    resembles GNU's "cp -P src dst".
    """
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    copyfile_w_callback(src, dst, follow_symlinks=follow_symlinks, callback=callback)
    shutil.copystat(src, dst, follow_symlinks=follow_symlinks)
    return dst

# noinspection PyUnresolvedReferences,PyProtectedMember
def copyfile_w_callback(src, dst, *, follow_symlinks=True, callback: Callable[[int, int], None] = None):
    """Copy data from src to dst in the most efficient way possible.
    If follow_symlinks is not set and src is a symbolic link, a new
    symlink will be created instead of copying the file it points to.
    """
    sys.audit("shutil.copyfile", src, dst)

    if shutil._samefile(src, dst):
        raise shutil.SameFileError("{!r} and {!r} are the same file".format(src, dst))

    file_size = 0
    for i, fn in enumerate([src, dst]):
        try:
            st = shutil._stat(fn)
        except OSError:
            # File most likely does not exist
            pass
        else:
            # XXX What about other special files? (sockets, devices...)
            if stat.S_ISFIFO(st.st_mode):
                fn = fn.path if isinstance(fn, os.DirEntry) else fn
                raise shutil.SpecialFileError("`%s` is a named pipe" % fn)
            if shutil._WINDOWS and i == 0:
                file_size = st.st_size

    if not follow_symlinks and shutil._islink(src):
        os.symlink(os.readlink(src), dst)
    else:
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            # macOS
            if shutil._HAS_FCOPYFILE:
                try:
                    shutil._fastcopy_fcopyfile(fsrc, fdst, shutil.posix._COPYFILE_DATA)
                    return dst
                except shutil._GiveupOnFastCopy:
                    pass
            # Linux
            elif shutil._USE_CP_SENDFILE:
                try:
                    shutil._fastcopy_sendfile(fsrc, fdst)
                    return dst
                except shutil._GiveupOnFastCopy:
                    pass
            # Windows, see:
            # https://github.com/python/cpython/pull/7160#discussion_r195405230
            elif shutil._WINDOWS and file_size > 0:
                _copyfileobj_readinto_w_cb(fsrc, fdst, min(file_size, shutil.COPY_BUFSIZE), callback=callback, filesize=file_size)  # noqa
                return dst

            copyfileobj_w_callback(fsrc, fdst, callback=callback, filesize=file_size)

    return dst

# noinspection PyUnresolvedReferences,PyProtectedMember
def copyfileobj_w_callback(fsrc, fdst, length=0, *, callback: Callable[[int, int], None] = None, filesize: int = None):
    """copy data from file-like object fsrc to file-like object fdst"""
    # Localize variable access to minimize overhead.
    if not length:
        length = shutil.COPY_BUFSIZE
    fsrc_read = fsrc.read
    fdst_write = fdst.write
    copied = 0
    while True:
        buf = fsrc_read(length)
        if not buf:
            break
        fdst_write(buf)
        if callback is not None:
            copied += len(buf)
            callback(copied, filesize)

# noinspection PyUnresolvedReferences,PyProtectedMember
def _copyfileobj_readinto_w_cb(fsrc, fdst, length=shutil.COPY_BUFSIZE, *, callback: Callable[[int, int], None] = None, filesize: int = None):
    """readinto()/memoryview() based variant of copyfileobj().
    *fsrc* must support readinto() method and both files must be
    open in binary mode.
    """
    # Localize variable access to minimize overhead.
    fsrc_readinto = fsrc.readinto
    fdst_write = fdst.write
    copied = 0
    with memoryview(bytearray(length)) as mv:
        while True:
            n = fsrc_readinto(mv)
            if not n:
                break
            elif n < length:
                with mv[:n] as smv:
                    fdst.write(smv)
            else:
                fdst_write(mv)
            if callback is not None:
                copied += n
                callback(copied, filesize)

#####################################################

def get_file_stat_data(f: Union[str, os.stat_result, os.DirEntry]):
    if isinstance(f, os.stat_result):
        return dict(ctime=f.st_ctime, mtime=f.st_mtime)
    if not os.path.exists(f):
        return dict(ctime=0.0, mtime=0.0)
    if isinstance(f, os.DirEntry):
        _stat = f.stat()
    else:
        _stat = os.stat(f)
    return dict(ctime=_stat.st_ctime, mtime=_stat.st_mtime)

class ModTimestampDB(object):
    COLRES_MODE_MANUAL = 0
    COLRES_MODE_AUTOLATEST = 1

    DEFAULT_FILEDATA = dict(mtime=0.0, ctime=0.0, colresmode=0.0)

    def __init__(self, storage_path: str = "db/timestamps.json", *, autosave: bool = False):
        self.storage_rel_path = storage_path
        self.__data = dict(timestamp=0.0, files=dict())
        self.load()
        self.changes = dict()
        self.unsaved_changes = 0
        self.autosave = autosave

    @property
    def data(self):
        return self.__data.get('files', dict())

    @property
    def storage(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), self.storage_rel_path)

    def check_autosave(self):
        if self.unsaved_changes > 10 and self.autosave:
            self.save()

    @staticmethod
    def get_empty_filedata_with_changes(**kwargs):
        _empty = dict(ModTimestampDB.DEFAULT_FILEDATA)
        if len(kwargs) > 0:
            _empty.update(kwargs)
        return _empty

    def get_timestamp(self, filepath: Union[str, os.DirEntry], *, get_from_file: bool = True):
        fp = filepath if isinstance(filepath, str) else filepath.path
        _ts = self.data.get(fp.replace("\\", "/"), None)
        if not isinstance(_ts, dict):
            _ts = None
        if _ts is None:
            f_ts = ModTimestampDB.get_empty_filedata_with_changes(**get_file_stat_data(filepath))
            self.save_timestamp(fp, f_ts, force=True)
            if get_from_file:
                _ts = f_ts
            else:
                return ModTimestampDB.get_empty_filedata_with_changes()
        return _ts

    def save_timestamp(self, filepath: str, timestamp: Dict[str, float] = None, *, bypass_changes_buffer: bool = False, force: bool = False):
        if timestamp is None:
            timestamp = ModTimestampDB.get_empty_filedata_with_changes(**get_file_stat_data(filepath))
        if timestamp['mtime'] > 0.0:
            _ts = self.data.get(filepath.replace("\\", "/"), None)
            if _ts is None or not isinstance(_ts, dict):
                _ts = ModTimestampDB.get_empty_filedata_with_changes()
            if abs(_ts['mtime'] - timestamp['mtime']) > MAX_MODIFICATION_TIME_ERROR_OFFSET or force:
                if bypass_changes_buffer:
                    self.data.setdefault(filepath.replace("\\", "/"), ModTimestampDB.get_empty_filedata_with_changes()).update(timestamp)
                else:
                    self.changes.setdefault(filepath.replace("\\", "/"), ModTimestampDB.get_empty_filedata_with_changes()).update(timestamp)
                self.unsaved_changes += 1
                self.check_autosave()

    def get_resolve_mode(self, filepath: Union[str, os.DirEntry]):
        fp = filepath if isinstance(filepath, str) else filepath.path
        if self.changes.get(fp.replace("\\", "/"), None) is not None:
            return self.changes[fp.replace("\\", "/")].get("colresmode", ModTimestampDB.COLRES_MODE_MANUAL)
        return self.data.get(fp.replace("\\", "/"), dict()).get("colresmode", ModTimestampDB.COLRES_MODE_MANUAL)

    def set_resolve_mode(self, filepath: str, mode: int):
        filedata = self.data.get(filepath.replace("\\", "/"), ModTimestampDB.get_empty_filedata_with_changes())
        if filedata["colresmode"] != mode:
            self.changes.setdefault(filepath.replace("\\", "/"))["colresmode"] = mode
            self.unsaved_changes += 1
            self.check_autosave()

    def remove_timestamp(self, filepath: str):
        _removed_ts = self.data.pop(filepath.replace("\\", "/"), None)
        if _removed_ts is not None:
            self.unsaved_changes += 1
            self.check_autosave()

    @property
    def snapshot_ts(self):
        return self.__data.get('timestamp', 0)

    @snapshot_ts.setter
    def snapshot_ts(self, value: float):
        self.__data['timestamp'] = value

    def load(self):
        if not os.path.exists(self.storage):
            self.save(init=True)
        with open(self.storage, "r", encoding='utf-8') as f:
            self.__data = json.load(f)

    def save(self, init: bool = False):
        if not init:
            self.snapshot_ts = time.time()
        self.data.update(self.changes)
        self.changes.clear()
        if not os.path.exists(os.path.dirname(self.storage)):
            os.makedirs(os.path.dirname(self.storage), exist_ok=True)
        with open(self.storage, "w+", encoding='utf-8') as f:
            json.dump(self.__data, f, indent=4)
        self.unsaved_changes = 0

class FileChange(object):
    def __init__(self, change_type: str, change_text: str):
        self.change_type = change_type
        self.change_text = change_text

    def __str__(self):
        return self.change_text

    def __hash__(self):
        return hash((self.change_type, self.change_text))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Cannot compare a {type(self).__name__} with {type(other).__name__}")
        return other.__hash__() == self.__hash__()

class ChangeTypes(object):
    CH_TYPE_UPDATE = 'update'
    CH_TYPE_UPDATE_NOTS = 'update_nots'
    CH_TYPE_RENAME = 'rename'
    CH_TYPE_REMOVE = 'remove'
    CH_TYPE_CREATE = 'create'
    CH_TYPE_CREATE_NOTS = 'create_nots'
    CH_TYPE_FOLDER = 'folder'
    CH_TYPE_REMOVEFOLDER = 'removef'

    TYPE_TO_NAME_MAP = {
        CH_TYPE_UPDATE: "Update S => B",
        CH_TYPE_UPDATE_NOTS: "Update S <= B",
        CH_TYPE_RENAME: "Rename",
        CH_TYPE_REMOVE: "Remove",
        CH_TYPE_CREATE: "Create S => B",
        CH_TYPE_CREATE_NOTS: "Create S <= B",
        CH_TYPE_FOLDER: "CreateFolder",
        CH_TYPE_REMOVEFOLDER: "RemoveFolder"
    }

    @staticmethod
    def get_name(t):
        return ChangeTypes.TYPE_TO_NAME_MAP.get(t, t if t in ChangeTypes.all_types() else f"UnknownChangeType({t})")

    @staticmethod
    def all_types() -> List[str]:
        return [y for x, y in ChangeTypes.__dict__.items() if x.startswith('CH_TYPE_')]

class ChangeTypeTracker(object):
    def __init__(self):
        self.changes = set()

    @property
    def num_changes(self):
        return len(self.changes)

    @property
    def has_changes(self):
        return self.num_changes > 0

    def add(self, item):
        self.changes.add(item)

    def remove(self, item):
        self.changes.remove(item)

    def __contains__(self, item):
        return item in self.changes

class ChangeTracker(object):
    def __init__(self):
        self.typetrackers: Dict[str, ChangeTypeTracker] = dict()
        for t in ChangeTypes.all_types():
            self.typetrackers[t] = ChangeTypeTracker()
        self.log = list()
        self.errors = list()

    @property
    def sorted_changes(self):
        return dict((x, y.changes) for x, y in self.typetrackers.items())

    @property
    def sorted_changes_count(self):
        return dict((x, y.num_changes) for x, y in self.typetrackers.items())

    def num_changes(self, c_type: str):
        if c_type not in ChangeTypes.all_types():
            raise TypeError(f"Incorrect type {c_type} passed.")
        return self.typetrackers[c_type].num_changes

    def has_changes(self, c_type: str):
        if c_type not in ChangeTypes.all_types():
            raise TypeError(f"Incorrect type {c_type} passed.")
        return self.typetrackers[c_type].has_changes

    @property
    def num_errors(self):
        return len(self.errors)

    def add_log(self, log_text: str, end: str = "\n", should_print=True, wait_time: float = 0):
        if should_print:
            print(log_text, end=end)
            if "\r" in end:
                sys.stdout.flush()
        self.log.append("\n{0}:\n{1}".format(notzformat.format(get_cur_dt()), log_text))
        if wait_time != 0:
            time.sleep(wait_time)

    def add_error(self, error_text: str, wait_time: float = 0):
        self.errors.append("\n{}".format(error_text))
        if not launch_args.args.nooutput:
            print(error_text)
            if wait_time != 0:
                time.sleep(wait_time)

    def add_file_change(self, change_type: str, change_text: str, should_print=True, wait_time: float = 0):
        try:
            if change_type not in ChangeTypes.all_types():
                raise TypeError(f"Change Type {change_type} is not a correct change type.")
            _change = FileChange(change_type, change_text)
        except TypeError:
            self.add_error("Incorrect file change type passed {}.".format(change_type), 2.0)
        else:
            if should_print:
                print(change_text)
            self.typetrackers[change_type].add(_change)
            if wait_time != 0:
                time.sleep(wait_time)

class FileChangeInstruction(object):
    def __init__(self, change_type: str, sourcefiledir: str, targetfilepath: str = None, *, is_forced: bool = False):
        if change_type not in ChangeTypes.all_types():
            raise TypeError(f"Change Type {change_type} is not a correct change type.")
        self.change_type = change_type
        self.source = sourcefiledir
        self.target = targetfilepath
        self.is_forced = is_forced

    @property
    def diffspace(self):
        return self.sourcesize - self.targetsize

    @property
    def diffsize(self):
        return abs(self.diffspace)

    @cached_property
    def sourcesize(self):
        if self.source is None:
            return 0
        elif not os.path.exists(self.source):
            return 0
        return os.stat(self.source).st_size

    @cached_property
    def targetsize(self):
        if self.target is None:
            return 0
        elif not os.path.exists(self.target):
            return 0
        return os.stat(self.target).st_size

    @cached_property
    def sourcemtime(self):
        if self.source is None:
            return 0
        elif not os.path.exists(self.source):
            return 0
        return get_file_stat_data(self.source)['mtime']

    @cached_property
    def targetmtime(self):
        if self.target is None:
            return 0
        elif not os.path.exists(self.target):
            return 0
        return get_file_stat_data(self.target)['mtime']

    def __hash__(self):
        return hash((self.change_type, self.source, self.target))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Cannot compare a {type(self).__name__} with {type(other).__name__}")
        return other.__hash__() == self.__hash__()

    def __str__(self):
        return f"[{self.change_type}{'<F>' if self.is_forced else ''}]:{self.source} -> {self.target}"

class InstructionStorage(object):
    def __init__(self):
        self.filechanges: Set[FileChangeInstruction] = set()
        self.cache = {
            "space_req": [0, False],
            "bytes_to_mod": [0, False]
        }

    @property
    def space_requirement(self):
        _cache = self.cache['space_req']
        if _cache[1]:
            return _cache[0]
        _sum = sum(x.diffspace for x in self.filechanges)
        _cache = [_sum, True]
        return _sum

    @property
    def bytes_to_modify(self):
        _cache = self.cache['bytes_to_mod']
        if _cache[1]:
            return _cache[0]
        _sum = sum(x.diffsize for x in self.filechanges)
        _cache = [_sum, True]
        return _sum

    @property
    def changes_num(self):
        return len(self.filechanges)

    def add_file_change(self, change_type: str, sourcefiledir: str, targetfiledir: Optional[str] = None, *, is_forced: bool = False):
        if change_type not in ChangeTypes.all_types():
            raise TypeError(f"Change Type {change_type} is not a correct change type.")
        if targetfiledir is None and change_type not in (ChangeTypes.CH_TYPE_REMOVE, ChangeTypes.CH_TYPE_REMOVEFOLDER):
            raise ValueError("Target File Directory can only be empty if change type is removal.")
        self.filechanges.add(FileChangeInstruction(change_type=change_type, sourcefiledir=sourcefiledir, targetfilepath=targetfiledir, is_forced=is_forced))
        self.invalidate_cache()

    def invalidate_cache(self, key: str = None):
        if key is not None and key in self.cache:
            self.cache[key][1] = False
        else:
            for k in self.cache.keys():
                self.cache[k][1] = False

    def get_file_change(self):
        if self.changes_num <= 0:
            return None
        return self.filechanges.pop()

    def print_scan_status(self, header: str = "", cur_dir: str = "", cur_num: int = -1, total_num: int = -1, *, cur_file: str = None):
        ANSIEscape.set_cursor_pos(1, 1)
        print(f"{header}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        print(f"Reading {cur_dir}>>{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        ANSIEscape.clear_current_line()
        ANSIEscape.set_cursor_pos(1, 4)
        if len(cur_dir) > 0:
            if cur_file is None:
                cur_file = os.path.basename(cur_dir)
            if cur_dir in cur_file:
                cur_file = cur_file[len(cur_dir):]
        else:
            if cur_file is None:
                cur_file = ""
        print(f">>{cur_file if len(cur_file) > 0 else '~'}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        ANSIEscape.clear_current_line()
        ANSIEscape.set_cursor_pos(1, 6)
        print(f"Changes required: {self.changes_num}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        for fct in ChangeTypes.all_types():
            _specific_change_group_len = len(tuple(x for x in self.filechanges if x.change_type == fct))
            if _specific_change_group_len > 0:
                print(f"{fct.title()}: {_specific_change_group_len}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        print(f"{cur_num}/{total_num} done. {get_progress_bar(round(cur_num/total_num , 2) * 100)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")


change_tracker = ChangeTracker()
file_instruction_list = InstructionStorage()
modification_timestamp_db = ModTimestampDB()

def del_file_or_dir(path):
    try:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            else:
                os.rmdir(path)
    except IsADirectoryError:
        os.rmdir(path)
    except:
        pass

def get_modification_dt_from_file(filepath):
    try:
        return datetime.datetime.fromtimestamp(get_file_stat_data(filepath)['mtime'])
    except:
        return None

def pathsplitall(path):
    allparts = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def get_path_reduction(source_data: Dict[str, Union[str, int]]):
    override_path_reduction = source_data.get("override_path_reduction", None)
    path_red = path_reduction if override_path_reduction is None else override_path_reduction
    return None if (path_red is None or (path_red is not None and path_red == 0)) else path_red

def get_bkp_path(path, source_data: Dict[str, str]):
    subpath: Optional[str] = source_data.get("subpath", "")
    _nodrive_path = os.path.splitdrive(path)[1].replace("\\", "/")
    _path_parts = [x for x in _nodrive_path.split("/") if len(x) > 0]
    return os.path.join(bkp_root, subpath, *_path_parts[get_path_reduction(source_data):]).replace("\\", "/")

def get_src_path(bkpp: str, source_data: Dict[str, str]):
    path: str = source_data.get("path")
    _subp = bkpp.replace("\\", "/")[len(source_data.get("subpath", "")) + len(bkp_root) + 1:]
    if get_path_reduction(source_data) is not None:
        _path_red = get_path_reduction(source_data) + 1 if get_path_reduction(source_data) is not None else None
        _bkpdir = os.path.join(*path.split("/")[_path_red:]).replace("\\", "/")
        bkpdir_ind = path.find(_bkpdir)
        if len(_bkpdir) > 0 and bkpdir_ind != -1:
            _fixed_sourcedir = path[:bkpdir_ind] + path[bkpdir_ind + len(_bkpdir):]
        else:
            _fixed_sourcedir = path
    else:
        _drive = os.path.splitdrive(path)[0]
        _fixed_sourcedir = f"{_drive}/" if len(_drive) > 0 else "/"
    _p = os.path.join(_fixed_sourcedir, _subp[1 if _subp.startswith("/") else None:]).replace("\\", "/")
    return _p

def is_in_ignored(path: str, ignored_paths: Set[Optional[str]]):
    path = path.replace('\\', '/')
    for ip in ignored_paths:
        ip = ip.replace('\\', '/')
        if path.startswith(ip):
            return True
    return False

def scan_directory(sdir: str, ignored_paths: Set[Optional[str]] = (), *, filenum: List[int] = None,  print_progress: bool = False) -> Union[Dict[str, os.DirEntry], os.DirEntry]:
    ret = dict()
    if os.path.exists(sdir):
        try:
            if print_progress:
                ANSIEscape.set_cursor_pos(1, 1)
                print(f"Scanning {sdir}:{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
                if filenum is None:
                    filenum = [0]
            for f in os.scandir(sdir):
                f: os.DirEntry
                if not is_in_ignored(f.path, ignored_paths):
                    if f.is_file():
                        ret[f.name] = f
                        if print_progress:
                            filenum[0] = filenum[0] + 1
                    elif f.is_dir():
                        ret[f.name] = scan_directory(f.path, ignored_paths=ignored_paths, filenum=filenum, print_progress=print_progress)
                    if print_progress:
                        ANSIEscape.set_cursor_pos(1, 3)
                        print(f"{filenum[0]} Files found.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        except NotADirectoryError:
            ret = get_file_direntry(sdir)
    return ret

def scan_backup_dirs(allbkps: list):
    _scanresult: Dict[str, os.DirEntry] = dict()
    filen = [0]
    for b in allbkps:
        sd = get_bkp_path(b.get('path'), b)
        ignored_paths_var = b.get("ignored_paths", ())
        ignored_paths = {f"{os.path.join(sd, x)}" for x in ignored_paths_var}
        _res = scan_directory(sd, ignored_paths, filenum=filen, print_progress=True)
        if isinstance(_res, dict) and len(_res) > 0 or isinstance(_res, os.DirEntry):
            _scanresult[os.path.basename(sd)] = _res
    return _scanresult


def get_file_direntry(path: str):
    if os.path.isdir(path):
        raise TypeError("get_file_direntry should only be used on files, received a directory path")
    try:
        return list(x for x in os.scandir(os.path.dirname(path)))[0]
    except:
        return None

def recursive_fileiter(sdir, ignored_paths: Set[Optional[str]] = ()):
    ret = list()
    folders = list()
    if os.path.exists(sdir):
        if os.path.isfile(sdir):
            for x in os.scandir(os.path.dirname(sdir)):
                x: os.DirEntry
                if x.name == os.path.basename(sdir):
                    return [x]
        for f in os.scandir(sdir):
            f: os.DirEntry
            try:
                if f.is_dir():
                    folders.append(f.path)
            except FileNotFoundError as _e:
                if os.path.islink(_e.filename) or Path(_e.filename).is_symlink():
                    change_tracker.add_error(f"Folder {_e.filename} was found but it apparently is a {'sym' if Path(_e.filename).is_symlink() else ''}link that cannot be reached. {_e.__class__.__name__}: {_e.args}")
        for folder in folders:
            ret.extend(recursive_fileiter(folder, ignored_paths))
        if os.path.isfile(sdir) and not is_in_ignored(sdir, ignored_paths):
            ret.append(sdir)
        for item in os.scandir(sdir):
            item: os.DirEntry
            try:
                if item.is_file() and not is_in_ignored(item.path, ignored_paths):
                    ret.append(item)
            except FileNotFoundError as _e:
                if os.path.islink(_e.filename) or Path(_e.filename).is_symlink():
                    change_tracker.add_error(f"File {_e.filename} | {item.name} was found but it is apparently is a {'sym' if Path(_e.filename).is_symlink() else ''}link that cannot be reached. {_e.__class__.__name__}: {_e.args}")
            except Exception as _e:
                change_tracker.add_error(f"Scanning File {item.name} raised an exception: {_e.__class__.__name__}: {_e.args}")
    else:
        change_tracker.add_error(f"Recursive FileIter could not find {sdir}", 2)
    return ret

def recursive_folderiter(sdir, ignored_paths: Set[Optional[str]] = ()):
    ret = list()
    f: os.DirEntry
    subfolders = [f for f in os.scandir(sdir) if f.is_dir()]
    ret.extend(subfolders)
    for folder in subfolders:
        if is_in_ignored(folder.path, ignored_paths):
            ret.extend(recursive_folderiter(folder.path))
    return ret

def get_actual_filepath(p: str):
    try:
        return str(Path(p).resolve())
    except FileNotFoundError:
        print(f"Failed to find File at: {p} returning path")
        return p

def get_actual_filename(p: str):
    return Path(p).resolve().name

class FileState(object):
    def __init__(self, bpath: str, spath: str, *, sourceexists: bool = False, backupexists: bool = False, sourcemtime: float = 0.0, backupmtime: float = 0.0, sourcectime: float = 0.0, backupctime: float = 0.0):
        self.bpath = bpath
        self.spath = spath
        self.sourceexists = sourceexists
        self.backupexists = backupexists
        self.sourcemtime = sourcemtime
        self.sourcectime = sourcectime
        self.backupmtime = backupmtime
        self.backupctime = backupctime

    def __hash__(self):
        return hash((self.spath, self.bpath))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Cannot compare a {type(self).__name__} with {type(other).__name__}")
        return other.__hash__() == self.__hash__()

def scan_changes(allbkps: list):
    if launch_args.args.nooutput:
        print("Checking Files for changes | No Output Mode.")
    num_bkps = len(allbkps)
    if not launch_args.args.nooutput:
        clear_terminal()
    ANSIEscape.set_cursor_display(False)
    print("Compiling pathlists...")
    bkpscan = scan_backup_dirs(allbkps)
    print("Done.")
    time.sleep(2)
    latest_change_ts = [0.0, 0.0]
    collisions: Set[FileState] = set()
    for n, b in enumerate(allbkps):
        sd = b.get('path')
        mode = b.get("mode", ManageModes.M_MODE_DEFAULT)
        ignored_paths_var = b.get("ignored_paths", ())
        ignored_paths = {f"{os.path.join(sd, x)}" for x in ignored_paths_var}
        try:
            if not launch_args.args.nooutput:
                file_instruction_list.print_scan_status("Checking Files for changes:", sd, n, num_bkps)
            fp = get_bkp_path(sd, b)
            _file_states: Dict[str, FileState] = dict()
            if os.path.exists(sd):
                sourcescan = recursive_fileiter(sd, ignored_paths)
                for f in sourcescan:
                    filep: str = get_bkp_path(f.path.replace("\\", "/"), b)
                    fp_dir = os.path.dirname(fp).replace("\\", "/")
                    scan_filep = filep[len(fp_dir) if filep.startswith(fp_dir) else None:]
                    file: Optional[os.DirEntry] = deep_get(bkpscan, scan_filep.split("/")[1:], return_none=True)
                    if not launch_args.args.nooutput:
                        file_instruction_list.print_scan_status("Checking Files for changes:", sd, n, num_bkps, cur_file=f.path)
                    if mode == ManageModes.M_MODE_SYNC:
                        _fs = _file_states.setdefault(filep, FileState(filep, f.path, sourceexists=True, sourcemtime=get_file_stat_data(f.stat())['mtime'], sourcectime=get_file_stat_data(f.stat())['ctime']))
                        if latest_change_ts[0] < max(_fs.sourcemtime, _fs.sourcectime):
                            latest_change_ts[0] = max(_fs.sourcemtime, _fs.sourcectime)
                        if file is not None:
                            _fs.backupexists = True
                            _fs.backupmtime, _fs.backupctime = get_file_stat_data(file.stat())['mtime'], get_file_stat_data(file.stat())['ctime']
                            if latest_change_ts[1] < max(_fs.backupmtime, _fs.backupctime):
                                latest_change_ts[1] = max(_fs.backupmtime, _fs.backupctime)
                    else:
                        if file is not None:
                            if get_file_stat_data(f.stat())['mtime'] > modification_timestamp_db.get_timestamp(file)['mtime'] + MAX_MODIFICATION_TIME_ERROR_OFFSET or b.get('force_backup', False):
                                file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, f.path, filep, is_forced=b.get('force_backup', False))
                        else:
                            file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_CREATE, f.path, filep)
            else:
                if mode == ManageModes.M_MODE_SNAPSHOT:
                    if os.path.exists(fp):
                        file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE if os.path.isfile(fp) else ChangeTypes.CH_TYPE_REMOVEFOLDER, fp)
                elif mode != ManageModes.M_MODE_SYNC:
                    change_tracker.add_error("{} Backup Source is Unavailable.".format(sd), wait_time=1)
            if os.path.exists(fp) and mode in (ManageModes.M_MODE_SNAPSHOT, ManageModes.M_MODE_SYNC):
                _back_ignored_paths = {os.path.join(fp, x).replace('\\', '/') for x in ignored_paths_var}
                bkp_rec_scan: List[os.DirEntry] = recursive_fileiter(fp, _back_ignored_paths)
                if os.path.exists(sd):
                    reverse_source_scan: Union[Dict[str, os.DirEntry], os.DirEntry] = scan_directory(sd, ignored_paths)
                else:
                    reverse_source_scan: Union[Dict[str, os.DirEntry], os.DirEntry] = dict()
                for bkpf in bkp_rec_scan:
                    sf = get_src_path(bkpf.path, b)
                    sfile: Optional[os.DirEntry] = deep_get(reverse_source_scan, sf[len(sd) + 1 if sf.startswith(sd) else None:].split("/"), return_none=True)
                    if not launch_args.args.nooutput:
                        file_instruction_list.print_scan_status("Checking Files for changes:", sd, n, num_bkps, cur_file=bkpf.path)
                    if mode == ManageModes.M_MODE_SNAPSHOT:
                        if sfile is None:
                            file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE if os.path.isfile(bkpf.path) else ChangeTypes.CH_TYPE_REMOVEFOLDER, bkpf.path)
                    elif mode == ManageModes.M_MODE_SYNC:
                        _fs = _file_states.setdefault(bkpf.path.replace("\\", "/"), FileState(bkpf.path.replace("\\", "/"), sf, backupexists=True, backupmtime=get_file_stat_data(bkpf.stat())['mtime'], backupctime=get_file_stat_data(bkpf.stat())['ctime']))
                        if latest_change_ts[1] < max(_fs.backupmtime, _fs.backupctime):
                            latest_change_ts[1] = max(_fs.backupmtime, _fs.backupctime)
                        if sfile is not None:
                            _fs.sourceexists = True
                            _fs.sourcemtime, _fssourcectime = get_file_stat_data(sfile.stat())['mtime'], get_file_stat_data(sfile.stat())['ctime']
                            if latest_change_ts[0] < max(_fs.sourcemtime, _fs.sourcectime):
                                latest_change_ts[0] = max(_fs.sourcemtime, _fs.sourcectime)
            if mode == ManageModes.M_MODE_SYNC:
                for filestate in _file_states.values():
                    if not launch_args.args.nooutput:
                        file_instruction_list.print_scan_status("Running file sync logic:", sd, n, num_bkps, cur_file=filestate.bpath)
                    file_snapshot_ts = modification_timestamp_db.get_timestamp(filestate.bpath, get_from_file=False)
                    if filestate.sourceexists != filestate.backupexists:
                        # Only one file exists, time to figure out if it was deleted or added
                        snap_change_time = max(file_snapshot_ts.get('ctime', 0), file_snapshot_ts.get('mtime', 0))
                        _max_bkp_mod_time = max(filestate.backupctime, filestate.backupmtime)
                        _max_src_mod_time = max(filestate.sourcectime, filestate.sourcemtime)
                        _max_mod_time = max(_max_bkp_mod_time, _max_src_mod_time)
                        if (snap_change_time == 0) or (snap_change_time != 0 and (snap_change_time < _max_mod_time)):
                            if filestate.sourceexists:
                                file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_CREATE, filestate.spath, filestate.bpath)
                            else:
                                file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_CREATE_NOTS, filestate.bpath, filestate.spath)
                        else:
                            file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE, filestate.spath if filestate.sourceexists else filestate.bpath)
                    else:
                        mtime_diff = abs(filestate.sourcemtime - filestate.backupmtime)
                        if mtime_diff > MAX_MODIFICATION_TIME_ERROR_OFFSET:
                            if filestate.sourcemtime > modification_timestamp_db.snapshot_ts and filestate.backupmtime > modification_timestamp_db.snapshot_ts:
                                collisions.add(filestate)
                            else:
                                if filestate.sourcemtime > filestate.backupmtime:
                                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, filestate.spath, filestate.bpath)
                                elif filestate.sourcemtime < filestate.backupmtime:
                                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE_NOTS, filestate.bpath, filestate.spath)
        except Exception as _e:
            change_tracker.add_error(f"Scanning File {sd} raised an exception: {_e.__traceback__.tb_lineno} | {_e.__class__.__name__}: {_e.args}")
    else:
        if not launch_args.args.nooutput:
            file_instruction_list.print_scan_status("Checking Files for changes:", "", num_bkps, num_bkps)
    if len(collisions) > 0:
        clear_terminal()
        print(f"Sync mode found {len(collisions)} collisions")
        start_collisions = len(collisions)
        while len(collisions) > 0:
            _cur_col = collisions.pop()
            ANSIEscape.set_cursor_pos(1, 2)
            print(f"Processing collision {start_collisions-len(collisions)}/{start_collisions}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            if launch_args.args.autoupdatecollisions or modification_timestamp_db.get_resolve_mode(_cur_col.bpath) is ModTimestampDB.COLRES_MODE_AUTOLATEST:
                if _cur_col.sourcemtime > _cur_col.backupmtime:
                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, _cur_col.spath, _cur_col.bpath)
                elif _cur_col.sourcemtime < _cur_col.backupmtime:
                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE_NOTS, _cur_col.bpath, _cur_col.spath)
            else:
                _sel = selection_menu(True, (1, 2, 3, 4), f"{ANSIEscape.get_colored_text('Manual Intervention Required!', ANSIEscape.ForegroundTextColor.bright_green)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n1. Keep Source {_cur_col.spath}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n   {notzformat.format(datetime.datetime.fromtimestamp(_cur_col.sourcemtime))}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n\n< Last Sync: {ANSIEscape.get_colored_text(notzformat.format(datetime.datetime.fromtimestamp(modification_timestamp_db.snapshot_ts)), ANSIEscape.ForegroundTextColor.bright_cyan)} >{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n\n2. Keep Backup {_cur_col.bpath}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n   {notzformat.format(datetime.datetime.fromtimestamp(_cur_col.backupmtime))}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n3. Skip{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}\n4. Always Autoupdate this file{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
                if _sel == 1:
                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, _cur_col.spath, _cur_col.bpath)
                elif _sel == 2:
                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE_NOTS, _cur_col.bpath, _cur_col.spath)
                elif _sel == 4:
                    modification_timestamp_db.set_resolve_mode(_cur_col.bpath, ModTimestampDB.COLRES_MODE_AUTOLATEST)
                    if _cur_col.sourcemtime > _cur_col.backupmtime:
                        file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, _cur_col.spath,
                                                              _cur_col.bpath)
                    elif _cur_col.sourcemtime < _cur_col.backupmtime:
                        file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE_NOTS, _cur_col.bpath,
                                                              _cur_col.spath)
    ANSIEscape.set_cursor_display(True)

def process():
    clear_terminal()
    print("Initializing.")
    time.sleep(1)
    if not os.path.exists(bkp_root):
        os.mkdir(bkp_root)
    allbkps: list = config['backup_dirs']
    scan_changes(allbkps)
    if file_instruction_list.changes_num > 0:
        _changetext = "{0} Changes Required. {1} Updates, {2} Creations, {3} Removals. {4} I/OAction Size".format(file_instruction_list.changes_num,
                                                                                       len(list(filter(lambda x: x.change_type in (ChangeTypes.CH_TYPE_UPDATE, ChangeTypes.CH_TYPE_UPDATE_NOTS), file_instruction_list.filechanges))),
                                                                                       len(list(filter(lambda x: x.change_type in (ChangeTypes.CH_TYPE_CREATE, ChangeTypes.CH_TYPE_CREATE_NOTS), file_instruction_list.filechanges))),
                                                                                       len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_REMOVE, file_instruction_list.filechanges))) + len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_REMOVEFOLDER, file_instruction_list.filechanges))),
                                                                                       format_bytes(file_instruction_list.bytes_to_modify))
        clear_terminal()
        print(_changetext)
        dinfo = shutil.disk_usage(os.path.realpath('/' if os.name == 'nt' else __file__))
        print("This will {3} approximately {0} of space. {1} Available from {2}".format(format_bytes(abs(file_instruction_list.space_requirement)), format_bytes(dinfo.free), format_bytes(dinfo.total), "require" if file_instruction_list.space_requirement >= 0 else "free up"))
        if not launch_args.args.nochangelist:
            print(f"Printing a list of changes: {len(file_instruction_list.filechanges)}")
        if not launch_args.args.nopause:
            os.system("pause")
        ANSIEscape.set_cursor_display(False)
        if not launch_args.args.nochangelist:
            ANSIEscape.set_cursor_display(True)
            _changesnum = len(file_instruction_list.filechanges)
            for change in sorted(file_instruction_list.filechanges, key=lambda x: x.change_type):
                _text = f"[{ANSIEscape.get_colored_text(ChangeTypes.get_name(change.change_type).upper(), text_color=ANSIEscape.ForegroundTextColor.red if change.change_type == ChangeTypes.CH_TYPE_REMOVE else ANSIEscape.ForegroundTextColor.green if change.change_type in (ChangeTypes.CH_TYPE_CREATE, ChangeTypes.CH_TYPE_CREATE_NOTS) else ANSIEscape.ForegroundTextColor.bright_green if change.change_type in (ChangeTypes.CH_TYPE_UPDATE, ChangeTypes.CH_TYPE_UPDATE_NOTS) else None)}{ANSIEscape.get_colored_text(' <Forced>', text_color=ANSIEscape.ForegroundTextColor.bright_cyan) if change.is_forced else ''}]\n{change.source}"
                _text += f"\n  <{format_bytes(change.sourcesize)}>mod@{notzformat.format(datetime.datetime.fromtimestamp(change.sourcemtime))}({change.sourcemtime})"
                if change.target is not None:
                    _text += f"\n  ~{format_bytes(change.diffspace)}~\n{change.target}"
                if change.change_type in (ChangeTypes.CH_TYPE_UPDATE, ChangeTypes.CH_TYPE_UPDATE_NOTS):
                    _text += f"\n  <{format_bytes(change.targetsize)}>mod@{notzformat.format(datetime.datetime.fromtimestamp(change.targetmtime))}({change.targetmtime})"
                print(_text, flush=True)
            if not launch_args.args.nopause:
                os.system("pause")
            ANSIEscape.set_cursor_display(False)
            clear_terminal()
        if file_instruction_list.space_requirement > dinfo.free:
            print(ANSIEscape.get_colored_text("Not Enough Space to finish the backup process. Exiting.", text_color=ANSIEscape.ForegroundTextColor.red, background_color=ANSIEscape.BackgroundTextColor.yellow))
            raise IOError("Not Enough Space")
        file_change_errors = 0
        bytes_done = 0
        bytes_to_modify = file_instruction_list.bytes_to_modify

        def print_status():
            ANSIEscape.set_cursor_pos(1, 1)
            print(f"In Progress | Ctrl+C to cancel.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print(f"Folder: {os.path.split(_cur_file.source)[0]}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            ANSIEscape.clear_current_line()
            ANSIEscape.set_cursor_pos(1, 4)
            print(f"File: [{_cur_file.change_type.capitalize()}] {os.path.split(_cur_file.source)[1]}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            ANSIEscape.clear_current_line()
            ANSIEscape.set_cursor_pos(1, 6)
            print(f"{current_file_num} / {num_files} done. DiffSize: {format_bytes(_cur_file.diffsize)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print(f"{get_progress_bar(0)}0.00% | Current File.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print(f"{get_progress_bar(round(current_file_num * 100 / num_files, 2))}{round(current_file_num * 100 / num_files, 2)}% | Total files.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print(f"{get_progress_bar(round(((abs(bytes_done) / bytes_to_modify) if bytes_to_modify != 0 else 1) * 100, 2))}{format_bytes(bytes_done)}/{format_bytes(bytes_to_modify)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print("\n\n{0} errors".format(ANSIEscape.get_colored_text(str(file_change_errors), text_color=ANSIEscape.ForegroundTextColor.red)) if file_change_errors != 0 else "")

        def print_cur_status(diffsize, current, total):
            ANSIEscape.set_cursor_pos(1, 7)
            _ratio = current / total
            _percentage: float = round(_ratio * 100, 2)
            print(f"{get_progress_bar(_percentage)}{_percentage:.2f}% | Current File.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}", flush=True)
            print(f"{get_progress_bar(round((current_file_num+_ratio) * 100 / num_files, 2))}{round((current_file_num+_ratio) * 100 / num_files, 2):.2f}% | Total files.{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            _done = bytes_done + diffsize * _ratio
            print(f"{get_progress_bar(round(((abs(_done) / bytes_to_modify) if bytes_to_modify != 0 else 1) * 100, 2))}{format_bytes(_done)}/{format_bytes(bytes_to_modify)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")

        if launch_args.args.nooutput:
            print("In Progress | No Output Mode.")
        num_files = file_instruction_list.changes_num
        current_file_num = 0
        while file_instruction_list.changes_num > 0:
            _cur_file = file_instruction_list.get_file_change()
            if _cur_file.target is not None:
                if not os.path.exists(os.path.dirname(_cur_file.target)):
                    try:
                        os.makedirs(os.path.dirname(_cur_file.target))
                    except FileExistsError:
                        pass
                    else:
                        change_tracker.add_file_change('folder', "Created folder {0}".format(os.path.dirname(_cur_file.target)), should_print=False)
            try:
                if not launch_args.args.nooutput:
                    print_status()
                if not launch_args.args.nologs:
                    change_tracker.add_log("Folder:{2}\nFile:{3}\n{0} / {1} done. DiffSize:{4}".format(current_file_num,
                                                                                        num_files,
                                                                                        os.path.split(_cur_file.source)[0],
                                                                                        os.path.split(_cur_file.source)[1],
                                                                                        format_bytes(_cur_file.diffsize)), should_print=False)
                if _cur_file.change_type in (ChangeTypes.CH_TYPE_UPDATE, ChangeTypes.CH_TYPE_UPDATE_NOTS):
                    act_filepath = get_actual_filepath(_cur_file.target)
                    copy_with_callback(_cur_file.source, os.path.dirname(act_filepath), callback=partial(print_cur_status, _cur_file.diffsize))  # noqa
                    modification_timestamp_db.save_timestamp(_cur_file.source if _cur_file.change_type is ChangeTypes.CH_TYPE_UPDATE_NOTS else _cur_file.target)
                    bytes_done += _cur_file.diffsize
                    change_tracker.add_file_change(ChangeTypes.CH_TYPE_UPDATE, "Updated | {0} | {1} -> {2}".format(_cur_file.source,
                                                                                                 get_modification_dt_from_file(_cur_file.source),
                                                                                                 get_modification_dt_from_file(_cur_file.target)),
                                                   should_print=False)
                    if os.path.basename(act_filepath) != os.path.basename(_cur_file.source):
                        os.rename(act_filepath, os.path.join(os.path.dirname(act_filepath), os.path.basename(_cur_file.source)))
                        change_tracker.add_file_change(ChangeTypes.CH_TYPE_RENAME, "Renamed | {0} | {1} -> {2}".format(act_filepath,
                                                                                                     os.path.basename(act_filepath),
                                                                                                     os.path.basename(_cur_file.source)))
                elif _cur_file.change_type in (ChangeTypes.CH_TYPE_CREATE, ChangeTypes.CH_TYPE_CREATE_NOTS):
                    copy_with_callback(_cur_file.source, os.path.dirname(_cur_file.target), callback=partial(print_cur_status, _cur_file.diffsize))  # noqa
                    modification_timestamp_db.save_timestamp(_cur_file.source if _cur_file.change_type is ChangeTypes.CH_TYPE_CREATE_NOTS else _cur_file.target)
                    bytes_done += _cur_file.diffsize
                    change_tracker.add_file_change(ChangeTypes.CH_TYPE_CREATE, "Created | {0}".format(_cur_file.source), should_print=False)
                elif _cur_file.change_type == ChangeTypes.CH_TYPE_REMOVE or _cur_file.change_type == ChangeTypes.CH_TYPE_REMOVEFOLDER:
                    bytes_done += _cur_file.diffsize
                    del_file_or_dir(get_actual_filepath(_cur_file.source))
                    modification_timestamp_db.remove_timestamp(_cur_file.source)
                    change_tracker.add_file_change(_cur_file.change_type, "Removed | {0}".format(get_actual_filepath(_cur_file.source)), should_print=False)
            except Exception as fileupd_exception:
                change_tracker.add_error("Failed to {3} file: {0} due to an Exception {1}. {2}".format(str(_cur_file), type(fileupd_exception).__name__, fileupd_exception.args, _cur_file.change_type), wait_time=5)
                file_change_errors += 1
            finally:
                current_file_num += 1
        file_instruction_list.invalidate_cache()
        clear_terminal()
        print("Finished Copying.")
        ANSIEscape.set_cursor_display(True)
        print("{0} / {1}({2}%) done.\n{3}{4}".format(num_files - file_change_errors,
                                                     num_files,
                                                     round((num_files - file_change_errors) * 100 / num_files, 2),
                                                     "\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else "",
                                                     "\n".join([x[1:] if x.startswith("\n") else x for x in change_tracker.errors])))
        change_tracker.add_log("{0} / {1} done.\n{2}%\n{3}".format(num_files - file_change_errors,
                                                             num_files,
                                                             round((num_files - file_change_errors) * 100 / num_files, 2),
                                                             "\n\n{} errors".format(ANSIEscape.get_colored_text(str(file_change_errors), text_color=ANSIEscape.ForegroundTextColor.red)) if file_change_errors != 0 else ""), should_print=False)
    else:
        print("{0}/{0}. 0 Required Changes Indexed.".format(len(allbkps)))
        print("No Changes Found. Exiting")
        time.sleep(2)


finished_init = False
def start_menu():
    global finished_init
    clear_terminal()
    modes = ""
    for a, ast in launch_args.args.__dict__.items():
        if ast is True:
            if len(modes) > 0:
                modes += "\n"
            modes += "{0} mode enabled".format(a)
    print("Automated Backup Script.{2}\nVersion:{0}/{1}".format(version.get('version', "Unavailable"), version.get('coderev', "Unavailable"), "\n{}".format(modes) if len(modes) > 0 else ""))
    print(f"Timestamp DB entries: {len(modification_timestamp_db.data)}, @{notzformat.format(datetime.datetime.fromtimestamp(modification_timestamp_db.snapshot_ts, tz=shift_tz))}")
    print(f"{ANSIEscape.get_colored_text('Press any key to proceed', text_color=ANSIEscape.ForegroundTextColor.bright_yellow)}\n{ANSIEscape.get_colored_text('Close the app to cancel', text_color=ANSIEscape.ForegroundTextColor.bright_red)}.")
    if launch_args.args.nologs and launch_args.args.profile:
        print(ANSIEscape.get_colored_text("Profile Mode will output results to terminal due to NoLogs Mode being active!", text_color=ANSIEscape.ForegroundTextColor.red))
    if not launch_args.args.offline:
        lvd = is_latest_version()
        if lvd is None:
            print("Latest Version Data is Unavailable")
        else:
            if lvd[2] is True:
                print(ANSIEscape.get_colored_text('-------------------------------', text_color=ANSIEscape.ForegroundTextColor.red))
                print(ANSIEscape.get_colored_text('INDEV VERSION PREVENTING UPDATE', text_color=ANSIEscape.ForegroundTextColor.red))
                print(ANSIEscape.get_colored_text(f'Latest: {lvd[1].get("version")}/{lvd[1].get("coderev")} Built: {lvd[1].get("buildtime")}', text_color=ANSIEscape.ForegroundTextColor.red))
                print(ANSIEscape.get_colored_text('INDEV VERSION PREVENTING UPDATE', text_color=ANSIEscape.ForegroundTextColor.red))
                print(ANSIEscape.get_colored_text('-------------------------------', text_color=ANSIEscape.ForegroundTextColor.red))
            else:
                if lvd[0] is True:
                    print(ANSIEscape.get_colored_text("This is the latest version", text_color=ANSIEscape.ForegroundTextColor.green))
                else:
                    print(ANSIEscape.get_colored_text("!OUTDATED Version! Latest: {0}/{1}. Built: {2}".format(lvd[1].get("version"), lvd[1].get("coderev"), lvd[1].get("buildtime")), text_color=ANSIEscape.ForegroundTextColor.yellow))
                    print(ANSIEscape.get_colored_text('Press any key to download an update.', text_color=ANSIEscape.ForegroundTextColor.yellow))
                    if not launch_args.args.nopause:
                        os.system('pause >nul')
                    else:
                        time.sleep(5)
                    dl_update()
    else:
        _buildstamp = version.get("buildstamp", 0)
        _days = datetime.timedelta(seconds=(time.time() - _buildstamp)).days
        if _days > 60:  # 60 days
            print(f"{ANSIEscape.get_colored_text('Running in OFFLINE Mode', text_color=ANSIEscape.ForegroundTextColor.yellow)}\nBuild time: {datetime.datetime.fromtimestamp(_buildstamp, tz=shift_tz)} ({ANSIEscape.get_colored_text(str(_days), text_color=ANSIEscape.ForegroundTextColor.red if _days > 100 else ANSIEscape.ForegroundTextColor.yellow)} days old).\nMay be outdated.")
    if not launch_args.args.nopause:
        os.system("pause >nul")
    change_tracker.add_log("Starting backup process")
    time.sleep(2)
    start_dt = datetime.datetime.now(shift_tz)
    finished_init = True
    try:
        process()
    except IOError as ioexc:
        print("{0}: {1}".format(type(ioexc).__name__, ",".join(list(map(lambda x: str(x), ioexc.args)))), flush=True)
        os.system("pause")
        sys.exit()
    except KeyboardInterrupt:
        print("Manually Cancelled.")
        time.sleep(2)
    change_tracker.add_log("Finished after {3} with {0} errors, {1} File Changes, {2} Folder Changes.{4}".format(change_tracker.num_errors,
                                                                                                    change_tracker.num_changes(ChangeTypes.CH_TYPE_UPDATE) +
                                                                                                    change_tracker.num_changes(ChangeTypes.CH_TYPE_CREATE) +
                                                                                                    change_tracker.num_changes(ChangeTypes.CH_TYPE_REMOVE),
                                                                                                    change_tracker.num_changes(ChangeTypes.CH_TYPE_FOLDER) +
                                                                                                    change_tracker.num_changes(ChangeTypes.CH_TYPE_REMOVEFOLDER),
                                                                                                    str(datetime.datetime.now(shift_tz) - start_dt),
                                                                                                    "\n{0} file{1} renamed due to filename case changes".format(change_tracker.num_changes(ChangeTypes.CH_TYPE_RENAME),
                                                                                                                                                                "s" if change_tracker.num_changes(ChangeTypes.CH_TYPE_RENAME) != 1 else "") if change_tracker.has_changes(ChangeTypes.CH_TYPE_RENAME) else ""))
    if not launch_args.args.nologs and (sum(x.num_changes for x in change_tracker.typetrackers.values()) + change_tracker.num_errors) > 0:
        change_tracker.add_log("Writing Logs")
        if not os.path.exists("bkpLogs"):
            os.mkdir("bkpLogs")
        ulp = os.path.join("bkpLogs", str(start_dt.date()))
        if not os.path.exists(ulp):
            os.mkdir(ulp)
        if len(change_tracker.log) > 0:
            with open(os.path.join(ulp, "full.log"), "a", encoding="utf-8") as ul:
                ul.writelines(change_tracker.log)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_UPDATE):
            with open(os.path.join(ulp, "updates.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_UPDATE].changes)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_RENAME):
            with open(os.path.join(ulp, "renames.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_RENAME].changes)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_CREATE):
            with open(os.path.join(ulp, "additions.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_CREATE].changes)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_REMOVE):
            with open(os.path.join(ulp, "removals.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_REMOVE].changes)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_REMOVEFOLDER):
            with open(os.path.join(ulp, "folderremovals.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_REMOVEFOLDER].changes)
        if change_tracker.has_changes(ChangeTypes.CH_TYPE_FOLDER):
            with open(os.path.join(ulp, "folders.log"), "a", encoding="utf-8") as ul:
                ul.writelines(f"{str(x)}\n" for x in change_tracker.typetrackers[ChangeTypes.CH_TYPE_FOLDER].changes)
        if change_tracker.num_errors > 0:
            with open(os.path.join(ulp, "errors.log"), "a", encoding="utf-8") as ul:
                ul.writelines(change_tracker.errors)
    print("Done.")
    if modification_timestamp_db.unsaved_changes > 0:
        print(ANSIEscape.get_colored_text(f"ModTimestamp DB changes: {modification_timestamp_db.unsaved_changes}", text_color=ANSIEscape.ForegroundTextColor.cyan))
        modification_timestamp_db.save()
    if change_tracker.num_errors > 0:
        print(f"{ANSIEscape.get_colored_text(f'Encountered {change_tracker.num_errors} errors.', text_color=ANSIEscape.ForegroundTextColor.yellow)}")
        time.sleep(2)
        if launch_args.args.nologs:
            print("\n".join(change_tracker.errors))
        else:
            ulp = os.path.join("bkpLogs", str(start_dt.date()))
            os.system("start " + os.path.join(ulp, 'errors.log').replace('\\', '/'))
    if not launch_args.args.nopause:
        os.system("pause")


if __name__ == "__main__":
    ANSIEscape.ansi_escape_ready()
    ap = argparse.ArgumentParser()
    ap.add_argument("-O", "--offline", help="Run in guaranteed offline mode, prevents version checks", action="store_true")
    ap.add_argument("-no", "--nooutput", help="disable interface updates", action="store_true")
    ap.add_argument("-np", "--nopause", help="disable user input requirement", action="store_true")
    ap.add_argument("-auc", "--autoupdatecollisions", help="skip collision intervention requirement and update to latest on collision", action="store_true")
    ap.add_argument("-nl", "--nologs", help="disable log creation", action="store_true")
    ap.add_argument("-ncl", "--nochangelist", help="disable showing a list of changes before copying", action="store_true")
    ap.add_argument("-ve", "--verboseerrors", help="show more info on error", action="store_true")
    ap.add_argument("-prof", "--profile", help="run with a profiler active, display the results in the end", action="store_true")
    args = ap.parse_args()
    launch_args.update_args(args)
    try:
        if launch_args.args.profile:
            import cProfile
            with cProfile.Profile() as profiler:
                start_menu()
            if not launch_args.args.nologs:
                if not os.path.exists("bkpLogs"):
                    os.mkdir("bkpLogs")
                ulp = os.path.join("bkpLogs", str(datetime.datetime.now().date()))
                if not os.path.exists(ulp):
                    os.mkdir(ulp)
                with open(os.path.join(ulp, "profiler_output.log"), "a", encoding="utf-8") as ul:
                    import pstats
                    s = io.StringIO()
                    pstats.Stats(profiler, stream=s).strip_dirs().sort_stats("cumtime").print_stats()
                    ul.write(s.getvalue())
                os.system("start " + os.path.join(ulp, 'profiler_output.log').replace('\\', '/'))
            else:
                profiler.print_stats("cumtime")
        else:
            start_menu()
    except Exception as e:
        print(f"Exception Occured {'while Launching' if finished_init is False else ''}: {type(e).__name__} : {e.args}")
        if launch_args.args.verboseerrors:
            import traceback
            print("\n".join(traceback.format_tb(e.__traceback__)))
        if finished_init is False:
            print('Press any key to try redownloading the script.')
            if not launch_args.args.nopause:
                os.system('pause >nul')
            dl_update()
        else:
            if not launch_args.args.nopause:
                os.system("pause")
            raise e
