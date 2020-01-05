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

HARD_CONFIG_VER = 1
LATEST_VER_DATA_URL = "https://raw.githubusercontent.com/DimasDSF/BackupScript/master/bkpScr/version.json"
args = None

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
    try:
        vts = version.get('buildstamp', "Unavailable")
        if vts.isnumeric():
            if get_cur_dt() - datetime.datetime.fromtimestamp(int(vts)) < datetime.timedelta(minutes=20):
                return True
    except:
        pass
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
                        return [True, vdata]
            except:
                return None
        return [False, vdata]
    else:
        return None

def dl_update():
    Github_Raw_links = [
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
        for filedata in Github_Raw_links:
            with urllib.request.urlopen(filedata['url']) as dld_data:
                if filedata['type'] == "json":
                    j = json.loads(dld_data.read().decode())
                    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), filedata['name']), "w+") as dl:
                        json.dump(j, dl, indent=4)
                elif filedata['type'] == "py":
                    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), filedata['name']), "w+") as dl:
                        text = dld_data.read().decode(encoding=locale.getdefaultlocale()[1])
                        dl.write(text)
    except Exception as e:
        print("Update Failed due to an Exception: {0} / {1}".format(type(e).__name__, e.args))
    else:
        print("Update Finished.\nRestarting", end="")
        for t in range(3):
            print(".", end="")
            sys.stdout.flush()
            time.sleep(1)
        python = sys.executable
        os.execl(python, python, *sys.argv)

log = []
errors_list = []
file_changes = {
    "update": [],
    "create": [],
    "remove": [],
    "removef": [],
    "folder": []
}
file_list = list()
def add_log(log_text: str, end: str = "\n", should_print=True, wait_time: float = 0):
    if should_print:
        print(log_text, end=end)
        if "\r" in end:
            sys.stdout.flush()
    log.append("\n{0}:\n{1}".format(notzformat.format(get_cur_dt()), log_text))
    if wait_time != 0:
        time.sleep(wait_time)

def add_error(error_text: str, wait_time: float = 0):
    print(error_text)
    errors_list.append("\n{}".format(error_text))
    if wait_time != 0:
        time.sleep(wait_time)

def add_file_change(change_type: str, change_text: str, should_print=True, wait_time: float = 0):
    if change_type in file_changes.keys():
        if should_print:
            print(change_text)
        file_changes[change_type].append("\n{}".format(change_text))
        if wait_time != 0:
            time.sleep(wait_time)
    else:
        add_error("Incorrect file change type passed {}.".format(change_type), 2.0)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

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
    splitPath: list = pathsplitall(nodrivepath)
    splitPath = list(filter(lambda x: ":" not in x, splitPath))
    try:
        splitPath.remove(" ")
    except:
        pass
    splitPath = splitPath[path_reduction::]
    ret = ""
    for p in splitPath:
        ret = os.path.join(ret, p)
    return ret

def get_src_path(srcpath: str, nodrivepath: str):
    splitSrcPath: list = pathsplitall(srcpath)
    splitPath: list = pathsplitall(nodrivepath)
    splitPath = list(filter(lambda x: ":" not in x, splitPath))
    try:
        splitSrcPath.remove(" ")
    except:
        pass
    try:
        splitPath.remove(" ")
    except:
        pass
    splitSrcPath = splitSrcPath[:path_reduction+1 if path_reduction is not None else 1:]
    splitSrcPath.extend(splitPath[path_reduction+1 if path_reduction is not None else 1::])
    ret = ""
    for p in splitSrcPath:
        ret = os.path.join(ret, p)
    return ret


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


def recursive_fileiter(sdir):
    ret = list()
    folders = [f.path for f in os.scandir(sdir) if f.is_dir()]
    for folder in folders:
        ret.extend(recursive_fileiter(folder))
    if os.path.isfile(sdir):
        ret.append(sdir)
    with os.scandir(sdir) as directory:
        for item in directory:
            if item.is_file():
                ret.append(item)
    return ret

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

def process():
    clear_terminal()
    print("Initializing.")
    time.sleep(2)
    if not os.path.exists(bkp_root):
        os.mkdir(bkp_root)
    space_req = 0
    bytes_to_modify = 0
    allbkps: list = config['backup_dirs']
    if args.nooutput:
        print("Checking Files for changes | No Output Mode.")
    for n, b in enumerate(allbkps):
        sd = os.path.normpath(b['path'])
        if not args.nooutput:
            clear_terminal()
            print("Checking Files for changes:")
            print("Reading {0}".format(sd))
            print("{0}/{1}. {2} Required Changes Indexed.".format(n, len(allbkps), len(file_list)))
        p = os.path.splitdrive(sd)[1]
        fp = os.path.join(bkp_root, get_bkp_path(p[1:] if p.startswith(("\\", "/")) else p))
        if os.path.exists(sd):
            if os.path.isfile(sd):
                if os.path.exists(fp):
                    if os.stat(sd).st_mtime > os.stat(fp).st_mtime + 1 or b.get('force_backup', False):
                        file_list.append(dict(type="update", sfile=sd, dfilepath=fp, diffsize=abs(os.stat(fp).st_size - os.stat(sd).st_size)))
                        space_req += os.stat(fp).st_size - os.stat(sd).st_size
                        bytes_to_modify += abs(os.stat(fp).st_size - os.stat(sd).st_size)
                else:
                    file_list.append(dict(type="create", sfile=sd, dfilepath=fp, diffsize=os.stat(sd).st_size))
                    space_req += os.stat(sd).st_size
                    bytes_to_modify += os.stat(sd).st_size
            else:
                for f in recursive_fileiter(sd):
                    fspldrv = os.path.splitdrive(f.path)[1]
                    fp = os.path.join(bkp_root, get_bkp_path(fspldrv[1:] if fspldrv.startswith(("\\", "/")) else fspldrv))
                    if f.is_file():
                        if os.path.exists(fp):
                            if os.stat(f.path).st_mtime > os.stat(fp).st_mtime + 1 or b.get('force_backup', False):
                                file_list.append(dict(type="update", sfile=f.path, dfilepath=fp, diffsize=abs(os.stat(f.path).st_size - os.stat(fp).st_size)))
                                space_req += os.stat(f.path).st_size - os.stat(fp).st_size
                                bytes_to_modify += abs(os.stat(f.path).st_size - os.stat(fp).st_size)
                        else:
                            file_list.append(dict(type="create", sfile=f.path, dfilepath=fp, diffsize=os.stat(f.path).st_size))
                            space_req += os.stat(f.path).st_size
                            bytes_to_modify += os.stat(f.path).st_size
                if b.get('snapshot_mode', False):
                    rnodrivetd = os.path.splitdrive(sd)[1]
                    for f in recursive_fileiter(os.path.join(bkp_root, get_bkp_path(rnodrivetd[1:] if rnodrivetd.startswith(("\\", "/")) else rnodrivetd))):
                        rsflunod = os.path.splitdrive(f.path)[1]
                        sf = get_src_path(sd, rsflunod)
                        if not os.path.exists(sf):
                            file_list.append(dict(type="remove" if os.path.isfile(f.path) else "removef", sfile=f.path, dfilepath=f.path, diffsize=os.stat(f.path).st_size))
                            space_req += -os.stat(f.path).st_size
                            bytes_to_modify += os.stat(f.path).st_size
        else:
            if b.get('snapshot_mode', False):
                if os.path.exists(fp):
                    file_list.append(dict(type="remove" if os.path.isfile(fp) else "removef", sfile=fp, dfilepath=fp, diffsize=os.stat(fp).st_size))
                    space_req += -os.stat(fp).st_size
                    bytes_to_modify += os.stat(fp).st_size
            else:
                add_error("{} Backup Source is Unavailable.".format(sd), wait_time=1)
    if len(file_list) > 0:
        clear_terminal()
        print("{0} Changes Required. {1} Updates, {2} Creations, {3} Removals. {4} I/OAction Size".format(len(file_list),
                                                                                       len(list(filter(lambda x: x['type'] == "update", file_list))),
                                                                                       len(list(filter(lambda x: x['type'] == "create", file_list))),
                                                                                       len(list(filter(lambda x: x['type'] == "remove", file_list))) + len(list(filter(lambda x: x['type'] == "removef", file_list))),
                                                                                       format_bytes(bytes_to_modify)))
        dinfo = shutil.disk_usage(os.path.realpath('/' if os.name == 'nt' else __file__))
        print("This will {3} approximately {0} of space. {1} Available from {2}".format(format_bytes(abs(space_req)), format_bytes(dinfo.free), format_bytes(dinfo.total), "require" if space_req >= 0 else "free up"))
        if not args.nopause:
            os.system("pause")
        if space_req > dinfo.free:
            print("Not Enough Space to finish the backup process. Exiting.")
            raise IOError("Not Enough Space")
        file_change_errors = 0
        bytes_done = 0
        if args.nooutput:
            print("In Progress | No Output Mode.")
        for num, file in enumerate(file_list):
            if not os.path.exists(os.path.dirname(file['dfilepath'])):
                try:
                    os.makedirs(os.path.dirname(file['dfilepath']))
                except FileExistsError:
                    pass
                else:
                    add_file_change('folder', "Created folder {0}".format(os.path.dirname(file['dfilepath'])), should_print=False)
            try:
                if not args.nooutput:
                    clear_terminal()
                    print("In Progress | Ctrl+C to cancel.")
                    print("Folder:{4}\nFile:{5}\n{0} / {1} done. DiffSize:{9}\n{6}{2}%\n{7}{8}{3}".format(num,
                                                                                                len(file_list),
                                                                                                round(num * 100 / len(file_list), 2),
                                                                                                "\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else "",
                                                                                                os.path.split(file['sfile'])[0],
                                                                                                os.path.split(file['sfile'])[1],
                                                                                                get_progress_bar(round(num * 100 / len(file_list), 2)),
                                                                                                get_progress_bar(round(((abs(bytes_done) / bytes_to_modify) if bytes_to_modify != 0 else 1) * 100, 2)),
                                                                                                "{0}/{1}".format(format_bytes(bytes_done), format_bytes(bytes_to_modify)),
                                                                                                format_bytes(file['diffsize'])))
                if not args.nologs:
                    add_log("Folder:{2}\nFile:{3}\n{0} / {1} done. DiffSize:{4}".format(num,
                                                                                        len(file_list),
                                                                                        os.path.split(file['sfile'])[0],
                                                                                        os.path.split(file['sfile'])[1],
                                                                                        format_bytes(file['diffsize'])), should_print=False)
                if file['type'] == "update":
                    bytes_done += file['diffsize']
                    shutil.copy2(file['sfile'], os.path.dirname(file['dfilepath']))
                    add_file_change('update', "Updated | {0} | {1} -> {2}".format(file['sfile'],
                                                                                  get_modification_dt_from_file(file['sfile']),
                                                                                  get_modification_dt_from_file(file['dfilepath'])), should_print=False)
                elif file['type'] == "create":
                    bytes_done += file['diffsize']
                    shutil.copy2(file['sfile'], os.path.dirname(file['dfilepath']))
                    add_file_change('create', "Created | {0}".format(file['sfile']), should_print=False)
                elif file['type'] == "remove" or file['type'] == "removef":
                    bytes_done += file['diffsize']
                    del_file_or_dir(file['sfile'])
                    add_file_change(file['type'], "Removed | {0}".format(file['sfile']), should_print=False)
            except Exception as e:
                add_error("Failed to update file: {0} due to an Exception {1}. {2}".format(file, type(e).__name__, e.args), wait_time=5)
                file_change_errors += 1
        clear_terminal()
        print("Finished Copying.")
        print("{0} / {1} done.\n{4}{2}%\n{5}{6}{3}".format(len(file_list) - file_change_errors,
                                                             len(file_list),
                                                             round((len(file_list) - file_change_errors) * 100 / len(file_list), 2),
                                                             "\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else "",
                                                             get_progress_bar(round((len(file_list) - file_change_errors) * 100 / len(file_list), 2)),
                                                             get_progress_bar(round(((abs(bytes_done) / bytes_to_modify) if bytes_to_modify != 0 else 1) * 100, 2)),
                                                             "{0}/{1}".format(format_bytes(bytes_done), format_bytes(bytes_to_modify))))
        add_log("{0} / {1} done.\n{2}%\n{3}".format(len(file_list) - file_change_errors,
                                                             len(file_list),
                                                             round((len(file_list) - file_change_errors) * 100 / len(file_list), 2),
                                                             "\n\n{} errors".format(file_change_errors) if file_change_errors != 0 else ""), should_print=False)
    else:
        print("No Changes Found")
        time.sleep(2)

finished_init = False
def start_menu():
    global args, finished_init
    ap = argparse.ArgumentParser()
    ap.add_argument("-O", "--offline", help="Run in guaranteed offline mode, prevents version checks", action="store_true")
    ap.add_argument("-no", "--nooutput", help="disable interface updates", action="store_true")
    ap.add_argument("-np", "--nopause", help="disable user input requirement", action="store_true")
    ap.add_argument("-nl", "--nologs", help="disable log creation", action="store_true")
    args = ap.parse_args()
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
    if not args.nopause:
        os.system("pause >nul")
    add_log("Starting backup process")
    time.sleep(2)
    start_dt = datetime.datetime.now(shift_tz)
    finished_init = True
    try:
        process()
    except IOError as e:
        print("{0}: {1}".format(type(e).__name__, e.args))
        os.system("pause")
        sys.exit()
    except KeyboardInterrupt:
        print("Manually Cancelled.")
        time.sleep(2)
    add_log("Finished after {3} with {0} errors, {1} File Changes, {2} Folder Changes.".format(len(errors_list),
                                                                                                 len(file_changes['update']) + len(file_changes['create']) + len(file_changes['remove']),
                                                                                                 len(file_changes['folder']) + len(file_changes['removef']),
                                                                                                 str(datetime.datetime.now(shift_tz) - start_dt)))
    if not args.nologs and (len(file_changes['update']) + len(file_changes['create']) + len(file_changes['remove']) + len(file_changes['removef']) + len(file_changes['folder']) + len(errors_list)) > 0:
        add_log("Writing Logs")
        if not os.path.exists("bkpLogs"):
            os.mkdir("bkpLogs")
        ulp = os.path.join("bkpLogs", str(start_dt.date()))
        if not os.path.exists(ulp):
            os.mkdir(ulp)
        if len(log) > 0:
            with open(os.path.join(ulp, "full.log"), "a", encoding="utf-8") as ul:
                ul.writelines(log)
        if len(file_changes['update']) > 0:
            with open(os.path.join(ulp, "updates.log"), "a", encoding="utf-8") as ul:
                ul.writelines(file_changes['update'])
        if len(file_changes['create']) > 0:
            with open(os.path.join(ulp, "additions.log"), "a", encoding="utf-8") as ul:
                ul.writelines(file_changes['create'])
        if len(file_changes['remove']) > 0:
            with open(os.path.join(ulp, "removals.log"), "a", encoding="utf-8") as ul:
                ul.writelines(file_changes['remove'])
        if len(file_changes['removef']) > 0:
            with open(os.path.join(ulp, "folderremovals.log"), "a", encoding="utf-8") as ul:
                ul.writelines(file_changes['removef'])
        if len(file_changes['folder']) > 0:
            with open(os.path.join(ulp, "folders.log"), "a", encoding="utf-8") as ul:
                ul.writelines(file_changes['folder'])
        if len(errors_list) > 0:
            with open(os.path.join(ulp, "errors.log"), "a", encoding="utf-8") as ul:
                ul.writelines(errors_list)
    print("Done.")
    if not args.nopause:
        os.system("pause")
    sys.exit()

if __name__ == "__main__":
    try:
        start_menu()
    except Exception as e:
        if finished_init is False:
            print("Exception Occured while Launching: {0} : {1}".format(type(e).__name__, e.args))
            print('Press any key to try redownloading the script.')
            os.system('pause >nul')
            dl_update()
        else:
            print("Exception Occured: {0} : {1}".format(type(e).__name__, e.args))
            os.system("pause")
            raise e
