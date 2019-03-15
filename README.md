# Yet another Twitter archive tool

Simple commandline application to let you decide about tweets while browsing your Twitter archive. Decisions to make: keep or mark to delete, decide later.

If you provide Twitter API credentials, you can bulk-delete all marked tweets.

### Offline browsing:
1. Download archive.zip from Twitter:
    https://help.twitter.com/managing-your-account/how-to-download-your-twitter-archive

2. Unpack you archive.zip to a working directory
3. Run Yatat:
```bash
python3 yatat.py /path/to/unpacked/archive
```
Browsing and decision progress is stored in:
+ */path/to/unpacked/archive/yatat.keep*
+ */path/to/unpacked/archive/yatat.kill*

### Online destruction:
+ Run Yata with [Twitter API credentials](https://developer.twitter.com): 
*(auth.yaml is created on-the-fly and you will be asked for credentials)*
```bash
python3 yatat.py /path/to/unpacked/archive /path/to/auth.yaml
```
