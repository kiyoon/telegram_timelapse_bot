# telegram_timelapse_bot

Control time lapse using Telegram.

```
*Timelapse*
                                      Available commands:
                                      /help
                                      Show this help
                                      /timelapse INTERVAL COUNT
                                      Capture without downloading.
                                      /timelapsedl INTERVAL COUNT
                                      Capture and download.
                                      /stop
                                      stop the timelapse process
                                      /status
                                      Show the status.
                                      /preview INDEX=-1
                                      Preview the last image captured (only with /timelapsedl).
                                      /video INDEX=-1
                                      Return the time lapse video (only with /timelapsedl).
                                      /list
                                      List the time lapse dir
                                      /rmdir INDEX
                                      FORCE remove the directory of the index.
                                      /rmvid INDEX
                                      FORCE remove the video.mp4 in the directory of the index.
                                      /ifconfig
                                      Return ifconfig output
                                      /du
                                      Check captured file size
                                      /df
                                      Check system storage
```

# Installation on Raspberry Pi OS

```bash
sudo pip3 install -r requirements.txt
sudo apt update
sudo apt install gphoto2

# optional: ffmpeg
```

Make the programme start on boot. Edit /etc/rc.local and add `sudo python3 /path/to/telegram_timelapse_bot/polling.py &` before the last line `exit 0`.
