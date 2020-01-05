##### Obligatory Think Twice Before Using<br>A freetime project full of workarounds to make it work, most probably bugs, and no tests whatsoever.<br>I also cannot be sure that it doesn't break with some file extensions/names especially the ones made with the intent to break it
##### Only made Public due to the version check requiring an online version file(and me being lazy enough not to make a token for it)

--------------------

A Configurable Backup Script.<br>
Designed for use on Portable Devices, Tested on Windows<br>
Only Semi-compatible with UNC Drives(Requires use of temporary virtual drives, setup with `pushd`/`popd`)

Launch Parameters:<br>
`-O : --offline : Launches in offline mode, prevents update checks.`<br>
`-no : --nooutput : Disables progress updates.`<br>
`-nl : --nologs : Disables log creation.`<br>
`-np : --nopause : Disables user interaction requirement, still pauses on errors.`<br>

Usage:
- On first launch script generates a base config file and exits
- Setup folders and files to backup <b>be sure to escape back slashes(`\ -> \\` | `\ -> /`) in file paths or use forward slashes</b>
<br>`force_backup` Flag can be useful when the file is updated by software that somehow does not cause the modification date to change
<br>`snapshot_mode` Flag can be useful if you want to keep the backup updated with source deletions as well as additions and modifications
- Setup your timezone offset from UTC
- Setup Path Reduction (Drops a set amount of directories between slashes when copying to backup
<br>e.g `C:\Users\User\Documents` with Path Reduction of 2 turns into `bkp\Documents` instead of `bkp\Users\User\Documents`)
