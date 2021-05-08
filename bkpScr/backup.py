import datetime
import os
import sys
import time
import json
import shutil
import math
import socket
import urllib.request
import argparse
import locale
import platform
from pathlib import Path

from typing import Dict, Set, List, Optional

HARD_CONFIG_VER = 1
LATEST_VER_DATA_URL = "https://raw.githubusercontent.com/DimasDSF/BackupScript/master/bkpScr/version.json"
class Arguments(object):
    def __init__(self):
        self.args: argparse.Namespace = argparse.Namespace()

    def update_args(self, args):
        self.args = args


launch_args = Arguments()

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
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), "r") as data:
            config = json.load(data)
            if config.get("config_version") < HARD_CONFIG_VER:
                print("Config Format Update Required.")
                print("Creating Config Backup")
                time.sleep(4)
                ts = int(time.time())
                shutil.copy2(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), os.path.join(os.path.dirname(os.path.realpath(__file__)), "config{0}.json.bkp".format(ts)))
                print("Created a config Backup: config_{0}.json.bkp\nLaunching Modifier.".format(ts))
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
                    "force_backup": False,
                    "snapshot_mode": False
                }
            ],
            "path_reduction": 0,
            "local_backup_root_folder": "bkp",
            "tz": {
                "hours": 0,
                "minutes": 0
            }
        }
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), "w+") as data:
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

############################
#        CLI Utils         #
############################

class ANSIEscape(object):
    ESC = "\x1b"
    CSI = "\x1b["
    OSC = "\x1b]"
    CONTROLSYMBOL_clear_after_cursor = "\x1b[0K"

    @staticmethod
    def enable_ansi_escape():
        if os.name == 'nt' and platform.release() == '10' and platform.version() >= '10.0.14393':
            import ctypes
            from ctypes import wintypes
            try:
                kernel32 = ctypes.windll.kernel32
                outhandle = kernel32.GetStdHandle(-11)
                kernel32.SetConsoleMode(outhandle, 7)
            except WindowsError as exc:
                if exc.winerror == 0x0057:  # ERROR_INVALID_PARAMETER
                    raise NotImplementedError
                raise
        elif os.name == 'posix':
            pass
        else:
            raise OSError("ANSI Escape Character Support is Unavailable.")

    @staticmethod
    def is_ansi_escape_available():
        if os.name == 'nt' and platform.release() == '10' and platform.version() >= '10.0.14393':
            return True
        elif os.name == 'posix':
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
    def delete_lines(num: int = 1):
        if num - 1 > 0:
            ANSIEscape.move_cursor_n_lines(num - 1, False)
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

def clear_terminal():
    if ANSIEscape.ansi_escape_ready():
        ANSIEscape.clear_console_text()
    else:
        os.system('cls' if sys.platform.lower() == "win32" else 'clear')
        sys.stdout.flush()

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
        print("Update Failed due to an Exception: {0} / {1}".format(type(update_exception).__name__, update_exception.args))
    else:
        print("Update Finished.\nRestarting", end="")
        for t in range(3):
            print(".", end="")
            sys.stdout.flush()
            time.sleep(1)
        python = sys.executable
        os.execl(python, python, *sys.argv)

#####################################################

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
    CH_TYPE_RENAME = 'rename'
    CH_TYPE_REMOVE = 'remove'
    CH_TYPE_CREATE = 'create'
    CH_TYPE_FOLDER = 'folder'
    CH_TYPE_REMOVEFOLDER = 'removef'

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
    def __init__(self, change_type: str, sourcefiledir: str, targetfilepath: str = None):
        if change_type not in ChangeTypes.all_types():
            raise TypeError(f"Change Type {change_type} is not a correct change type.")
        self.change_type = change_type
        self.source = sourcefiledir
        self.target = targetfilepath

    @property
    def diffspace(self):
        return self.sourcesize - self.targetsize

    @property
    def diffsize(self):
        return abs(self.diffspace)

    @property
    def sourcesize(self):
        if self.source is None:
            return 0
        elif not os.path.exists(self.source):
            return 0
        return os.stat(self.source).st_size

    @property
    def targetsize(self):
        if self.target is None:
            return 0
        elif not os.path.exists(self.target):
            return 0
        return os.stat(self.target).st_size

    def __hash__(self):
        return hash((self.change_type, self.source, self.target))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Cannot compare a {type(self).__name__} with {type(other).__name__}")
        return other.__hash__() == self.__hash__()

    def __str__(self):
        return f"[{self.change_type}]:{self.source} -> {self.target}"

class InstructionStorage(object):
    def __init__(self):
        self.filechanges: Set[FileChangeInstruction] = set()

    @property
    def space_requirement(self):
        return sum(x.diffspace for x in self.filechanges)

    @property
    def bytes_to_modify(self):
        return sum(x.diffsize for x in self.filechanges)

    @property
    def changes_num(self):
        return len(self.filechanges)

    def add_file_change(self, change_type: str, sourcefiledir: str, targetfiledir: Optional[str] = None):
        if change_type not in ChangeTypes.all_types():
            raise TypeError(f"Change Type {change_type} is not a correct change type.")
        if targetfiledir is None and change_type not in (ChangeTypes.CH_TYPE_REMOVE, ChangeTypes.CH_TYPE_REMOVEFOLDER):
            raise ValueError("Target File Directory can only be empty if change type is removal.")
        self.filechanges.add(FileChangeInstruction(change_type=change_type, sourcefiledir=sourcefiledir, targetfilepath=targetfiledir))

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
        if cur_file is None:
            cur_file = os.path.basename(cur_dir)
        if cur_dir in cur_file:
            cur_file = cur_file[len(cur_dir):]
        print(f">>{cur_file if len(cur_file) > 0 else '~'}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        print(f"Changes required: {self.changes_num}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        for fct in ChangeTypes.all_types():
            _specific_change_group_len = len(tuple(x for x in self.filechanges if x.change_type == fct))
            if _specific_change_group_len > 0:
                print(f"{fct.title()}: {_specific_change_group_len}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
        print(f"{cur_num}/{total_num} done. {get_progress_bar(round(cur_num/total_num , 2) * 100)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")


change_tracker = ChangeTracker()
file_instruction_list = InstructionStorage()

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
        return datetime.datetime.fromtimestamp(os.stat(filepath).st_mtime)
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

def get_bkp_path(nodrivepath: str):
    split_path: list = pathsplitall(nodrivepath)
    split_path = list(filter(lambda x: ":" not in x, split_path))
    try:
        split_path.remove(" ")
    except:
        pass
    split_path = split_path[path_reduction::]
    ret = ""
    for p in split_path:
        ret = os.path.join(ret, p)
    return ret

def get_src_path(srcpath: str, nodrivepath: str):
    split_src_path: list = pathsplitall(srcpath)
    split_path: list = pathsplitall(nodrivepath)
    split_path = list(filter(lambda x: ":" not in x, split_path))
    try:
        split_src_path.remove(" ")
    except:
        pass
    try:
        split_path.remove(" ")
    except:
        pass
    split_src_path = split_src_path[:path_reduction+1 if path_reduction is not None else 1:]
    split_src_path.extend(split_path[path_reduction+1 if path_reduction is not None else 1::])
    ret = ""
    for p in split_src_path:
        ret = os.path.join(ret, p)
    return ret

def recursive_fileiter(sdir):
    ret = list()
    folders = list()
    if os.path.exists(sdir):
        for f in os.scandir(sdir):
            f: os.DirEntry
            try:
                if f.is_dir():
                    folders.append(f.path)
            except FileNotFoundError as _e:
                if os.path.islink(_e.filename) or Path(_e.filename).is_symlink():
                    change_tracker.add_error(f"Folder {_e.filename} was found but it apparently is a {'sym' if Path(_e.filename).is_symlink() else ''}link that cannot be reached. {_e.__class__.__name__} {_e.args}")
        for folder in folders:
            ret.extend(recursive_fileiter(folder))
        if os.path.isfile(sdir):
            ret.append(sdir)
        for item in os.scandir(sdir):
            item: os.DirEntry
            try:
                if item.is_file():
                    ret.append(item)
            except FileNotFoundError as _e:
                if os.path.islink(_e.filename) or Path(_e.filename).is_symlink():
                    change_tracker.add_error(f"File {_e.filename} | {item.name} was found but it apparently is a {'sym' if Path(_e.filename).is_symlink() else ''}link that cannot be reached. {_e.__class__.__name__} {_e.args}")
            except Exception as _e:
                change_tracker.add_error(f"Scanning File {item.name} raised an exception: {_e.__class__.__name__}: {_e.args}")
    else:
        change_tracker.add_error(f"Recursive FileIter could not find {sdir}", 2)
    return ret

def recursive_folderiter(sdir):
    ret = list()
    f: os.DirEntry
    subfolders = [f for f in os.scandir(sdir) if f.is_dir()]
    ret.extend(subfolders)
    for folder in subfolders:
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

def process():
    clear_terminal()
    print("Initializing.")
    time.sleep(1)
    if not os.path.exists(bkp_root):
        os.mkdir(bkp_root)
    allbkps: list = config['backup_dirs']
    if launch_args.args.nooutput:
        print("Checking Files for changes | No Output Mode.")
    num_bkps = len(allbkps)
    if not launch_args.args.nooutput:
        clear_terminal()
    ANSIEscape.set_cursor_display(False)
    for n, b in enumerate(allbkps):
        sd = os.path.normpath(b['path'])
        try:
            if not launch_args.args.nooutput:
                file_instruction_list.print_scan_status("Checking Files for changes:", sd, n, num_bkps)
            p = os.path.splitdrive(sd)[1]
            fp = os.path.join(bkp_root, get_bkp_path(p[1:] if p.startswith(("\\", "/")) else p))
            if os.path.exists(sd):
                # Source Dir Exists
                if os.path.isfile(sd):
                    if os.path.exists(fp):
                        if os.stat(sd).st_mtime > os.stat(fp).st_mtime + 1 or b.get('force_backup', False):
                            file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, sd, fp)
                    else:
                        file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_CREATE, sd, fp)
                else:
                    for f in recursive_fileiter(sd):
                        fspldrv = os.path.splitdrive(f.path)[1]
                        fp = os.path.join(bkp_root, get_bkp_path(fspldrv[1:] if fspldrv.startswith(("\\", "/")) else fspldrv))
                        if f.is_file():
                            if not launch_args.args.nooutput:
                                file_instruction_list.print_scan_status("Checking Files for changes:", sd, n, num_bkps, cur_file=f.path)
                            if os.path.exists(fp):
                                if os.stat(f.path).st_mtime > os.stat(fp).st_mtime + 1 or b.get('force_backup', False):
                                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_UPDATE, f.path, fp)
                            else:
                                file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_CREATE, f.path, fp)
                    if b.get('snapshot_mode', False):
                        rnodrivetd = os.path.splitdrive(sd)[1]
                        if os.path.exists(os.path.join(bkp_root, get_bkp_path(rnodrivetd[1:] if rnodrivetd.startswith(("\\", "/")) else rnodrivetd))):
                            for f in recursive_fileiter(os.path.join(bkp_root, get_bkp_path(rnodrivetd[1:] if rnodrivetd.startswith(("\\", "/")) else rnodrivetd))):
                                rsflunod = os.path.splitdrive(f.path)[1]
                                sf = get_src_path(sd, rsflunod)
                                if not launch_args.args.nooutput:
                                    file_instruction_list.print_scan_status("Checking Files for changes:", os.path.join(bkp_root, get_bkp_path(rnodrivetd[1:] if rnodrivetd.startswith(("\\", "/")) else rnodrivetd)), n, num_bkps, cur_file=f.path)
                                if not os.path.exists(sf):
                                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE if os.path.isfile(f.path) else ChangeTypes.CH_TYPE_REMOVEFOLDER, f.path)
                            for f in recursive_folderiter(os.path.join(bkp_root, get_bkp_path(rnodrivetd[1:] if rnodrivetd.startswith(("\\", "/")) else rnodrivetd))):
                                rsflunod = os.path.splitdrive(f.path)[1]
                                sf = get_src_path(sd, rsflunod)
                                if not os.path.exists(sf):
                                    file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE if os.path.isfile(f.path) else ChangeTypes.CH_TYPE_REMOVEFOLDER, f.path)
            else:
                if b.get('snapshot_mode', False):
                    if os.path.exists(fp):
                        file_instruction_list.add_file_change(ChangeTypes.CH_TYPE_REMOVE if os.path.isfile(fp) else ChangeTypes.CH_TYPE_REMOVEFOLDER, fp)
                else:
                    change_tracker.add_error("{} Backup Source is Unavailable.".format(sd), wait_time=1)
        except Exception as _e:
            change_tracker.add_error(f"Scanning File {sd} raised an exception: {_e.__traceback__.tb_lineno} | {_e.__class__.__name__}: {_e.args}")
    ANSIEscape.set_cursor_display(True)
    if file_instruction_list.changes_num > 0:
        clear_terminal()
        print("{0} Changes Required. {1} Updates, {2} Creations, {3} Removals. {4} I/OAction Size".format(file_instruction_list.changes_num,
                                                                                       len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_UPDATE, file_instruction_list.filechanges))),
                                                                                       len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_CREATE, file_instruction_list.filechanges))),
                                                                                       len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_REMOVE, file_instruction_list.filechanges))) + len(list(filter(lambda x: x.change_type == ChangeTypes.CH_TYPE_REMOVEFOLDER, file_instruction_list.filechanges))),
                                                                                       format_bytes(file_instruction_list.bytes_to_modify)))
        dinfo = shutil.disk_usage(os.path.realpath('/' if os.name == 'nt' else __file__))
        print("This will {3} approximately {0} of space. {1} Available from {2}".format(format_bytes(abs(file_instruction_list.space_requirement)), format_bytes(dinfo.free), format_bytes(dinfo.total), "require" if file_instruction_list.space_requirement >= 0 else "free up"))
        if not launch_args.args.nopause:
            os.system("pause")
        ANSIEscape.set_cursor_display(False)
        if file_instruction_list.space_requirement > dinfo.free:
            print("Not Enough Space to finish the backup process. Exiting.")
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
            print(f"{current_file_num} / {num_files} done. DiffSize: {format_bytes(_cur_file.diffsize)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print(f"{get_progress_bar(round(current_file_num * 100 / num_files, 2))}{round(current_file_num * 100 / num_files, 2)}%")
            print(f"{get_progress_bar(round(((abs(bytes_done) / bytes_to_modify) if bytes_to_modify != 0 else 1) * 100, 2))}{format_bytes(bytes_done)}/{format_bytes(bytes_to_modify)}{ANSIEscape.CONTROLSYMBOL_clear_after_cursor}")
            print("\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else "")
        if launch_args.args.nooutput:
            print("In Progress | No Output Mode.")
        num_files = file_instruction_list.changes_num
        current_file_num = 0
        while file_instruction_list.changes_num > 0:
            _cur_file = file_instruction_list.get_file_change()
            current_file_num += 1
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
                if _cur_file.change_type == ChangeTypes.CH_TYPE_UPDATE:
                    bytes_done += _cur_file.diffsize
                    act_filepath = get_actual_filepath(_cur_file.target)
                    shutil.copy2(_cur_file.source, os.path.dirname(act_filepath))
                    change_tracker.add_file_change(ChangeTypes.CH_TYPE_UPDATE, "Updated | {0} | {1} -> {2}".format(_cur_file.source,
                                                                                                 get_modification_dt_from_file(_cur_file.source),
                                                                                                 get_modification_dt_from_file(_cur_file.target)),
                                                   should_print=False)
                    if os.path.basename(act_filepath) != os.path.basename(_cur_file.source):
                        os.rename(act_filepath, os.path.join(os.path.dirname(act_filepath), os.path.basename(_cur_file.source)))
                        change_tracker.add_file_change('rename', "Renamed | {0} | {1} -> {2}".format(act_filepath,
                                                                                                     os.path.basename(act_filepath),
                                                                                                     os.path.basename(_cur_file.source)))
                elif _cur_file.change_type == ChangeTypes.CH_TYPE_CREATE:
                    bytes_done += _cur_file.diffsize
                    shutil.copy2(_cur_file.source, os.path.dirname(_cur_file.target))
                    change_tracker.add_file_change(ChangeTypes.CH_TYPE_CREATE, "Created | {0}".format(_cur_file.source), should_print=False)
                elif _cur_file.change_type == ChangeTypes.CH_TYPE_REMOVE or _cur_file.change_type == ChangeTypes.CH_TYPE_REMOVEFOLDER:
                    bytes_done += _cur_file.diffsize
                    del_file_or_dir(get_actual_filepath(_cur_file.source))
                    change_tracker.add_file_change(_cur_file.change_type, "Removed | {0}".format(get_actual_filepath(_cur_file.source)), should_print=False)
            except Exception as fileupd_exception:
                change_tracker.add_error("Failed to {3} file: {0} due to an Exception {1}. {2}".format(str(_cur_file), type(fileupd_exception).__name__, fileupd_exception.args, _cur_file.change_type), wait_time=5)
                file_change_errors += 1
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
                                                             "\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else ""), should_print=False)
    else:
        print("{0}/{0}. 0 Required Changes Indexed.".format(len(allbkps)))
        print("No Changes Found")
        time.sleep(2)


finished_init = False
def start_menu():
    global finished_init
    ap = argparse.ArgumentParser()
    ap.add_argument("-O", "--offline", help="Run in guaranteed offline mode, prevents version checks", action="store_true")
    ap.add_argument("-no", "--nooutput", help="disable interface updates", action="store_true")
    ap.add_argument("-np", "--nopause", help="disable user input requirement", action="store_true")
    ap.add_argument("-nl", "--nologs", help="disable log creation", action="store_true")
    args = ap.parse_args()
    launch_args.update_args(args)
    clear_terminal()
    modes = ""
    for a, ast in args.__dict__.items():
        if ast is True:
            if len(modes) > 0:
                modes += "\n"
            modes += "{0} mode enabled".format(a)
    print("Automated Backup Script.{2}\nVersion:{0}/{1}\nPress any key to proceed\nClose the app to cancel.".format(version.get('version', "Unavailable"), version.get('coderev', "Unavailable"), "\n{}".format(modes) if len(modes) > 0 else ""))
    if not args.offline:
        lvd = is_latest_version()
        if lvd is None:
            print("Latest Version Data is Unavailable")
        else:
            if lvd[2] is True:
                print('-------------------------------')
                print('INDEV VERSION PREVENTING UPDATE')
                print(f'Latest: {lvd[1].get("version")}/{lvd[1].get("coderev")} Built: {lvd[1].get("buildtime")}')
                print('INDEV VERSION PREVENTING UPDATE')
                print('-------------------------------')
            else:
                if lvd[0] is True:
                    print("This is the latest version")
                else:
                    print("!OUTDATED Version! Latest: {0}/{1}. Built: {2}".format(lvd[1].get("version"), lvd[1].get("coderev"), lvd[1].get("buildtime")))
                    print('Press any key to download an update.')
                    if not args.nopause:
                        os.system('pause >nul')
                    else:
                        time.sleep(5)
                    dl_update()
    else:
        _buildstamp = version.get("buildstamp", 0)
        if time.time() - _buildstamp > 5184000:  # 60 days
            print(f"Running in OFFLINE Mode\nBuild time: {datetime.datetime.fromtimestamp(_buildstamp, tz=shift_tz)} ({datetime.timedelta(seconds=(time.time() - _buildstamp)).days} days old).\nMay be outdated.")
    if not args.nopause:
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
    if not args.nologs and (sum(x.num_changes for x in change_tracker.typetrackers.values()) + change_tracker.num_errors) > 0:
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
    if change_tracker.num_errors > 0:
        print(f"Encountered {change_tracker.num_errors} errors.")
        time.sleep(2)
        if args.nologs:
            print("\n".join(change_tracker.errors))
        else:
            ulp = os.path.join("bkpLogs", str(start_dt.date()))
            os.system("start " + os.path.join(ulp, 'errors.log').replace('\\', '/'))
    if not args.nopause:
        os.system("pause")
    sys.exit()


if __name__ == "__main__":
    ANSIEscape.ansi_escape_ready()
    try:
        start_menu()
    except Exception as e:
        if finished_init is False:
            print("Exception Occured while Launching: {0} : {1}".format(type(e).__name__, e.args))
            print('Press any key to try redownloading the script.')
            os.system('pause >nul')
            dl_update()
        else:
            import traceback
            print("Exception Occured: {0} : {1}".format(type(e).__name__, e.args))
            print("\n".join(traceback.format_tb(e.__traceback__)))
            os.system("pause")
            raise e

