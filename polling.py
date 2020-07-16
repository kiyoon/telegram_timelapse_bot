#!/usr/bin/env python3
import coloredlogs, logging
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from configparser import ConfigParser
import os
import subprocess
from subprocess import PIPE

import json

logger = logging.getLogger(__name__)

class TimelapseBot:
    def __init__(self, token, filter_chat_ids):
        self.TABLE_NAME_PREFIX = 'viddb_'      # viddb_{chat_id} format.
        self.updater = Updater(token, use_context=True)
        self.dp = self.updater.dispatcher
        self.filter_chat_ids = filter_chat_ids

        self.proc = None
    
    def run(self):
        self.dp.add_handler(CommandHandler('start', self.start, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('help', self.help, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('timelapse', self.timelapse, pass_args = True, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('stop', self.stop, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CommandHandler('ifconfig', self.ifconfig, filters=Filters.user(self.filter_chat_ids)))
        self.dp.add_handler(CallbackQueryHandler(self.button))
        self.dp.add_handler(MessageHandler(Filters.text & Filters.user(self.filter_chat_ids),
                                               self.message))
        self.dp.add_error_handler(self.error)
        self.updater.start_polling()
        logger.info('Listening...')
        self.updater.idle()




    def _is_proc_running(self):
        if self.proc is not None:
            if self.proc.returncode is None:
                return True
        return False


    def start(self, update, context):
        self.help(update, context)

    def help(self, update, context):
        #context.bot.send_message(chat_id=update.message.chat_id, text="")
        #context.bot.send_message(chat_id=update.effective_chat.id, text="")
        update.message.reply_text("*Timelapse*\n"
                                      "Available commands:\n\n"
                                      "/help\n"
                                      "Show this help\n\n"
                                      "/timelapse\n"
                                      "\n\n"
                                      "/stop\n"
                                      "Stop the timelapse process\n\n"
                                      "/ifconfig\n"
                                      "Return ifconfig output\n\n")


    def timelapse(self, update, context):
        if len(context.args) != 2:
            update.message.reply_text("You need 2 arguments")
            return

        interval = args[0]
        num_photos = args[1]

        # execute, and then not wait.
        self.proc = subprocess.Popen(
                ["gphoto2", "--set-config", "capturetarget=1", "-I", interval, "-F", num_photos, "--capture-image"],
                shell=False, stdin=None, stdout=None, stderr=None)


    def stop(self, update, context):
        if self._is_proc_running:
            #os.kill(self.proc.pid, signal.SIGINT)
            #proc.send_signal(signal.SIGINT)
            #proc.kill()
            self.proc.terminate()
            update.message.reply_text("Killed")
        else:
            update.message.reply_text("No process running")

    def ifconfig(self, update, context):
        proc = subprocess.Popen(
                ["ifconfig", "-a"],
                shell=False, stdout=PIPE)
        update.message.reply_text(proc.stdout.read().decode('utf-8'))


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
    coloredlogs.install(fmt='%(asctime)s - %(name)s: %(lineno)4d - %(levelname)s - %(message)s', level='DEBUG')

    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    config = ConfigParser()
    config.read(os.path.join(__location__, "key.ini"))
    token = config['Telegram']['token']
    filter_chat_ids = list(map(int, config['Telegram']['filter_chat_ids'].split(",")))

    bot = TimelapseBot(token, filter_chat_ids)
    bot.run()
    


