#!/usr/bin/env python3
import coloredlogs, logging
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from configparser import ConfigParser
import os
import subprocess
from subprocess import PIPE

import json

import time
import glob
from utils import *

import threading
import shutil


import definitions
import filepath

logger = logging.getLogger(__name__)

class TimelapseBot:
    def __init__(self, token, filter_chat_ids):
        self.updater = Updater(token, use_context=True)
        self.dp = self.updater.dispatcher
        self.filter_chat_ids = filter_chat_ids

        self.proc = None
    
    def run(self):
        self.dp.add_handler(CommandHandler('start', self.start, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('help', self.help, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('timelapse', self.timelapse, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('timelapsedl', self.timelapsedl, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('stop', self.stop, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('status', self.status, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('preview', self.preview, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('video', self.video, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('list', self.list, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('rmdir', self.rmdir, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('rmvid', self.rmvid, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('ifconfig', self.ifconfig, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('du', self.du, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('df', self.df, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CallbackQueryHandler(self.button))
        self.dp.add_handler(MessageHandler(Filters.text & Filters.user(self.filter_chat_ids),
                                               self.message))
        self.dp.add_error_handler(self.error)
        self.updater.start_polling()
        logger.info('Listening...')
        self.updater.idle()



    def _kill_gphoto2(self):
        # kill processes that locks the use of gphoto2
        subprocess.run(["killall", "/usr/lib/gvfs/gvfs-gphoto2-volume-monitor"])
        subprocess.run(["killall", "/usr/lib/gvfs/gvfsd-gphoto2"])


    def _estimate_size(self, num_photos):

        megabyte_per_photo = range(1, 31, 2)    # 1MiB to 10MiB
        ret_str = "Estimated total size if one photo is a size of:"

        for mb_per_photo in megabyte_per_photo:
            size = num_photos * mb_per_photo * 1024 * 1024
            str_size = sizeof_fmt(size)

            ret_str += "\n{:d} MiB -> {:s}".format(mb_per_photo, str_size)

        return ret_str



    def _is_proc_running(self):
        if self.proc is not None:
        #    if self.proc.returncode is None:
            if self.proc.poll() is None:
                return True
        return False


    def _wait_for_process(self, func_after, update, context):
        while self.proc.poll() is None:
            time.sleep(1)

        func_after(update, context)

    def _send_video(self, update, context):
        if len(context.args) < 1:
            index = filepath.get_last_index()
            if index < 0:
                update.message.reply_text("No file to preview")
                return
        else:
            try:
                index = int(context.args[0])
            except ValueError as e:
                update.message.reply_text("Index must be an integer")
                return


        update.message.reply_text("Encoding finished. Sending..")
        context.bot.send_video(chat_id=update.effective_chat.id, video=open(filepath.get_video_path(index), 'rb'))
        

    def _end_of_timelapse(self, update, context):
        update.message.reply_text("Time lapse finished in {:s}.".format(time_fmt(time.time() - self.proc_start_time)))


    def start(self, update, context):
        self.help(update, context)


    def help(self, update, context):
        #context.bot.send_message(chat_id=update.message.chat_id, text="")
        #context.bot.send_message(chat_id=update.effective_chat.id, text="")
        update.message.reply_text("*Timelapse*\n"
                                      "Available commands:\n\n"
                                      "/help\n"
                                      "Show this help\n\n"
                                      "/timelapse INTERVAL COUNT\n"
                                      "Capture without downloading.\n\n"
                                      "/timelapsedl INTERVAL COUNT\n"
                                      "Capture and download.\n\n"
                                      "/stop\n"
                                      "stop the timelapse process\n\n"
                                      "/status\n"
                                      "Show the status.\n\n"
                                      "/preview INDEX=-1\n"
                                      "Preview the last image captured (only with /timelapsedl).\n\n"
                                      "/video INDEX=-1\n"
                                      "Return the time lapse video (only with /timelapsedl).\n\n"
                                      "/list\n"
                                      "List the time lapse dir\n\n"
                                      "/rmdir INDEX\n"
                                      "FORCE remove the directory of the index.\n\n"
                                      "/rmvid INDEX\n"
                                      "FORCE remove the video.mp4 in the directory of the index.\n\n"
                                      "/ifconfig\n"
                                      "Return ifconfig output\n\n"
                                      "/du\n"
                                      "Check captured file size\n\n"
                                      "/df\n"
                                      "Check system storage\n\n")




    def timelapse(self, update, context):
        if len(context.args) != 2:
            update.message.reply_text("You need 2 arguments")
            return

        if self._is_proc_running():
            update.message.reply_text("Time lapse already running. Try to stop the process first.")
            return

        self._kill_gphoto2()

        interval = context.args[0]
        num_photos = context.args[1]

        try:
            self.interval = float(interval)
            self.num_photos = int(num_photos)
        except ValueError as e:
            update.message.reply_text("Only numbers are accepted")
            return

        self.command = "timelapse"
        self.expected_time = self.interval * self.num_photos

        update.message.reply_text("Expected time: {:s}\nTimelapse video of {:s} at {:.2f} fps.\n{:s}".format(time_fmt(self.expected_time), time_fmt(self.num_photos / definitions.fps), definitions.fps, self._estimate_size(self.num_photos)))

        # execute, and then not wait.
        self.proc = subprocess.Popen(
                ["gphoto2", "--set-config", "capturetarget=1", "-I", interval, "-F", num_photos, "--capture-image"],
                shell=False, stdin=None, stdout=None, stderr=None)
        self.proc_start_time = time.time()
        
        x = threading.Thread(target=self._wait_for_process, args=(self._end_of_timelapse,update,context))
        x.start()


    def timelapsedl(self, update, context):
        if len(context.args) != 2:
            update.message.reply_text("You need 2 arguments")
            return

        if self._is_proc_running():
            update.message.reply_text("Time lapse already running. Try to stop the process first.")
            return

        self._kill_gphoto2()

        interval = context.args[0]
        num_photos = context.args[1]

        try:
            self.interval = float(interval)
            self.num_photos = int(num_photos)
        except ValueError as e:
            update.message.reply_text("Only numbers are accepted")
            return

        self.command = "timelapsedl"
        self.expected_time = self.interval * self.num_photos
        self.video_index = filepath.get_last_index() + 1

        dest_dir = filepath.get_subdir(self.video_index)

        update.message.reply_text("Downloading in {:s}\nExpected time: {:s}\nTimelapse video of {:s} at {:.2f} fps.\n{:s}".format(dest_dir, time_fmt(self.expected_time), time_fmt(self.num_photos / definitions.fps), definitions.fps, self._estimate_size(self.num_photos)))

        # execute, and then not wait.
        dest_files = os.path.join(dest_dir, filepath.capture_filename_gphoto2)
        self.proc = subprocess.Popen(
                ["gphoto2", "--set-config", "capturetarget=1", "-I", interval, "-F", num_photos, "--capture-image-and-download", "--keep", "--keep-raw", "--filename", dest_files],
                shell=False, stdin=None, stdout=None, stderr=None)
        self.proc_start_time = time.time()

        x = threading.Thread(target=self._wait_for_process, args=(self._end_of_timelapse,update,context))
        x.start()


    def stop(self, update, context):
        if self._is_proc_running():
            #os.kill(self.proc.pid, signal.SIGINT)
            #proc.send_signal(signal.SIGINT)
            #proc.kill()
            self.proc.terminate()
            update.message.reply_text("Killed")
        else:
            update.message.reply_text("No process running")


    def status(self, update, context):
        if self._is_proc_running():
            if self.command.startswith("timelapse"):
                #update.message.reply_text(self.proc.stdout.read().decode('utf-8'))
                elapsed_time = time.time() - self.proc_start_time
                message = "Expected time: {:s}\n".format(time_fmt(self.expected_time))
                message += "Elapsed time: {:s}\n".format(time_fmt(elapsed_time))
                message += "{:2.1f}%".format(elapsed_time / self.expected_time * 100.0)

                if self.command == "timelapsedl":
                    num_taken = filepath.get_last_downloaded_num()
                    num_left = self.num_photos - num_taken
                    message += "\n\n"
                    message += "Total # of photos: {:d}\n".format(self.num_photos)
                    message += "# taken: {:d}\n".format(num_taken)
                    message += "# left: {:d}\n".format(num_left)
                    message += "{:2.1f}%\n".format(num_taken / self.num_photos * 100.0)
                    message += "ETA: {:s}".format(time_fmt(num_left * self.interval))

                update.message.reply_text(message)

            else:
                update.message.reply_text("Time lapse not running.")

        else:
            update.message.reply_text("No process running")


    def preview(self, update, context):
        if len(context.args) < 1:
            index = filepath.get_last_index()
            if index < 0:
                update.message.reply_text("No file to preview.")
                return
        else:
            try:
                index = int(context.args[0])
            except ValueError as e:
                update.message.reply_text("Index must be an integer")
                return

        last_filename = filepath.get_last_downloaded_filename(index)
        if last_filename is None:
            update.message.reply_text("No file to preview")
            return

        update.message.reply_text(last_filename)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(last_filename, 'rb'))

    def video(self, update, context):
        if self._is_proc_running():
            update.message.reply_text("Process already running. Wait or stop the process.")
            return

        if len(context.args) < 1:
            index = filepath.get_last_index()
            if index < 0:
                update.message.reply_text("No file to preview")
                return
        else:
            try:
                index = int(context.args[0])
            except ValueError as e:
                update.message.reply_text("Index must be an integer")
                return

        dest_video_path = filepath.get_video_path(index)
        if os.path.exists(dest_video_path):
            update.message.reply_text("Video already exist.")
            return

        if not filepath.index_exists(index):
            update.message.reply_text("Such index doesn't exist.")
            return

        update.message.reply_text("Encoding video..")
        self.command = "video"
        self.proc = subprocess.Popen(
                ["ffmpeg", "-i", os.path.join(filepath.get_subdir(index), filepath.capture_filename_ffmpeg), "-vf", "scale=-2:{:d}".format(definitions.encoded_video_height), "-sws_flags", "bicubic", "-c:v", "libx264", "-preset", "fast", "-crf", "25",
                    "-color_range", "pc", "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709", "-pix_fmt", "yuvj420p",
                    "-an", "-r", definitions.fps_str, dest_video_path],
                shell=False)

        x = threading.Thread(target=self._wait_for_process, args=(self._send_video,update,context))
        x.start()
        #self._wait_for_process(self._send_video, update, context)


    def list(self, update, context):
        ret_str = ""
        subdirs = filepath.list_subdirs()
        if len(subdirs) > 0:
            for subdirname in subdirs:
                jpgs = glob.glob(os.path.join(filepath.capture_dirpath, subdirname, "*.jpg"))
                ret_str += "{:s}\t{:d} jpgs\n".format(subdirname, len(jpgs))
                
            update.message.reply_text(ret_str)

        else:
            update.message.reply_text("No files to list")


    def rmdir(self, update, context):
        if len(context.args) < 1:
            update.message.reply_text("You must specify the index of the directory to remove.")
            return
        else:
            try:
                index = int(context.args[0])
            except ValueError as e:
                update.message.reply_text("Index must be an integer")
                return
        
        dir_to_remove = filepath.get_subdir(index)
        try:
            shutil.rmtree(dir_to_remove)
        except:
            update.message.reply_text("Error deleting {:s}".format(dir_to_remove))
            return
        
        update.message.reply_text("Successfully deleted {:s}".format(dir_to_remove))


    def rmvid(self, update, context):
        if len(context.args) < 1:
            update.message.reply_text("You must specify the index of the directory to remove.")
            return
        else:
            try:
                index = int(context.args[0])
            except ValueError as e:
                update.message.reply_text("Index must be an integer")
                return
        
        video_to_remove = filepath.get_video_path(index)
        try:
            os.remove(video_to_remove)
        except:
            update.message.reply_text("Error deleting {:s}".format(video_to_remove))
            return
        
        update.message.reply_text("Successfully deleted {:s}".format(video_to_remove))



    def ifconfig(self, update, context):
        proc = subprocess.Popen(
                ["ifconfig", "-a"],
                shell=False, stdout=PIPE)
        update.message.reply_text("```\n" + proc.stdout.read().decode('utf-8') + "\n```", parse_mode = "markdown")

    def du(self, update, context):
        proc = subprocess.Popen(
                ["du", "-h", filepath.capture_dirpath],
                shell=False, stdout=PIPE)
        update.message.reply_text("```\n" + proc.stdout.read().decode('utf-8') + "\n```", parse_mode = "markdown")

    def df(self, update, context):
        proc = subprocess.Popen(
                ["df", "-h"],
                shell=False, stdout=PIPE)
        update.message.reply_text("```\n" + proc.stdout.read().decode('utf-8') + "\n```", parse_mode = "markdown")

    def button(self, update, context):
        query = update.callback_query
        data = json.loads(query.data)
        if data['command'] == 'del':
            if data['option'] == 'Yes':
                msg = "Successfully removed from the DB!"
                remove = True
            else:
                msg = "Operation cancelled."
                remove = False
            
            # Remove the video info from the DB.
            self.mysql.connect()
            self.mysql.execute("DELETE FROM {:s}{:d} WHERE id={:d}".format(self.TABLE_NAME_PREFIX, update.effective_chat.id, data['id']), write=True)
            self.mysql.close()

            query.edit_message_text(text=query.message.text_html + "\n\n<b>Selected option: {}</b>\n\n{}".format(data['option'], msg), parse_mode='html')
        else:
            raise NotImplementedError("Unable to recognise the command using the inline keyboard button.")


    def _build_menu(self, buttons,n_cols,header_buttons=None,footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu


    def message(self, update, context):
        link_idx = update.message.text.find('https://')
        title = update.message.text[:link_idx]
        link = update.message.text[link_idx:]
        self.mysql.connect()
        self.mysql.execute("INSERT INTO {:s}{:d}(title,url,has_download) VALUES('{:s}', '{:s}', FALSE);".format(self.TABLE_NAME_PREFIX, update.effective_chat.id, title,link), write=True)
        self.mysql.close()
        update.message.reply_text(title + "added to DB at id {:d}.".format(self.mysql.curs.lastrowid))


    def error(self, update, context):
        import traceback
        logger.error('Update "%s" caused error "%s"' % (update, context.error))
        traceback.print_exc(context.error)

if __name__ == "__main__":
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    coloredlogs.install(fmt='%(asctime)s - %(name)s: %(lineno)4d - %(levelname)s - %(message)s', level='DEBUG')

    f_handler = logging.FileHandler(os.path.join(__location__, 'timelapse.log'))
    #f_handler.setLevel(logging.NOTSET)
    f_handler.setLevel(logging.DEBUG)

    # Create formatters and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(name)s: %(lineno)4d - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    root_logger = logging.getLogger()
    root_logger.addHandler(f_handler)

    while not is_internet():
        logger.debug("Checking internet connection to 8.8.8.8 failed.. Repeating")
        time.sleep(1)


    config = ConfigParser()
    config.read(os.path.join(__location__, "key.ini"))
    token = config['Telegram']['token']
    filter_chat_ids = list(map(int, config['Telegram']['filter_chat_ids'].split(",")))

    bot = TimelapseBot(token, filter_chat_ids)
    bot.run()
    


