#!/usr/bin/env python
# -*- coding: utf-8 -*-
import curses
import time
import datetime
import logging
import sys
import re
from todo import TodoistAbstractor
from curses import wrapper
import locale

class Commands(object):
    ADD = "ADD"
    COMPLETE = "COMPLETE"

class CursesUI(object):
    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        self.todo = TodoistAbstractor()
        self.main_items = []
        self.selected_projects = []
        self.available_commands = []
        self.active_command = 0
        self.ctrl_pressed = False
        self.command = u""
        self.menu_width = 25
        self.option_width = 10
        self.setup_logging()
        self.todo.start_sync()

    def setup_logging(self):
        self.log = logging.getLogger(__file__)
        hdlr = logging.FileHandler(__file__ + ".log")
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)
        self.log.setLevel(logging.DEBUG)

    def run(self):
        wrapper(self.main)

    def main(self, stdscr):
        self.stdscr = stdscr
        # self.splash()

        self.stdscr.clear()
        self.stdscr.leaveok(1)

        self.create_windows()
        self.paint_projects()
        self.paint_command_bar()
        self.paint_option_box()
        self.stdscr.refresh()

        while self.menu_loop():
            pass

    def create_windows(self):
        height, width = self.stdscr.getmaxyx()
        self.menubox = curses.newwin(height, self.menu_width, 0, 1)
        self.mainbox = curses.newwin(height-3, width - (self.menu_width + 1), 0, self.menu_width + 1)
        self.commandbox = curses.newwin(2, width - (self.menu_width + 1) - (self.option_width + 1),
                                        height-2, self.menu_width + 1)
        self.optionbox = curses.newwin(2, self.option_width, height-2, width - (self.menu_width + 1))

    def resize_windows(self):
        height, width = self.stdscr.getmaxyx()
        self.menubox.resize(height, self.menu_width)
        self.mainbox.resize(height-3, width - (self.menu_width + 1))
        self.commandbox.resize(2, width - (self.menu_width + 1) - (self.option_width + 1))
        self.optionbox.resize(2, self.option_width)

        self.commandbox.mvwin(height-2, self.menu_width + 1)
        self.optionbox.mvwin(height-2, width - (self.menu_width + 1))

    def execute_command(self, user_input, command):
        if command == Commands.ADD:
            project = None

            if len(self.selected_projects):
                project = self.selected_projects[0]

            content = [word for word in user_input.split(' ')
                       if not word.startswith('#')]

            self.todo.add_item(" ".join(content), project)

        elif command == Commands.COMPLETE:
            self.todo.complete_item(self.main_items[0]['id'])

    def handle_user_input(self):
        key = self.stdscr.getch()
        self.stdscr.nodelay(True)
        second = self.stdscr.getch()
        self.stdscr.nodelay(False)
        self.log.info("Print pressed: " +repr(key))

        if key == curses.KEY_BACKSPACE:
            self.command = self.command[:-1]
        elif key == curses.KEY_ENTER or key == 10:
            if self.active_command < len(self.available_commands):
                self.execute_command(self.command, self.available_commands[self.active_command])
                self.command = u" ".join([word for word in self.command.split(' ')
                                          if word.startswith('#')]) + " "
        elif key == curses.KEY_RESIZE:
            self.resize_windows()
            self.log.info("SCREEN RESIZED!")
        # XXX: Use this to end the application at some point
        elif key == ord('q') and self.ctrl_pressed:
            curses.endwin()
        elif key == 9:
            # TAB pressed
            self.active_command = (self.active_command + 1) % len(self.available_commands)
        else:
            try:
                if not second == -1:
                    key = (chr(key) + chr(second)).decode('utf-8')
                else:
                    key = chr(key)

                self.command += key
            except:
                pass

    def paint_projects(self):
        self.menubox.border(' ', 0, ' ', ' ', ' ', ' ', ' ', ' ')
        for i, project in enumerate(self.todo.get_projects()):
            if project['name'] in self.selected_projects:
                self.menubox.addstr(i+1,
                                    (project['indent']-1)*2,
                                    self.shorten_string(project['name'].encode('UTF-8'), self.menu_width-4),
                                    curses.A_STANDOUT)
            else:
                self.menubox.addstr(i+1,
                                    (project['indent']-1)*2,
                                    self.shorten_string(project['name'].encode('UTF-8'), self.menu_width-4))
        self.menubox.refresh()

    def shorten_string(self, string, cols):
        if len(string) <= cols:
            return string
        else:
            return string[:cols-2] + ".."

    def command_available(self, cmd):
        if not cmd in self.available_commands:
            self.available_commands.append(cmd)

    def command_unavailable(self, cmd):
        if cmd in self.available_commands:
            self.available_commands.remove(cmd)

    def paint_option_box(self):
        self.optionbox.clear()

        if len(self.available_commands):
            self.optionbox.addstr(1, 1,
                                  self.available_commands[self.active_command % len(self.available_commands)],
                                  curses.A_STANDOUT)

        self.optionbox.refresh()

    def paint_command_bar(self):
        self.commandbox.clear()
        if self.command:
            self.commandbox.addstr(1, 1, self.command.encode('UTF-8'))
        self.commandbox.refresh()

    def paint_main_window(self):
        self.list_items(self.main_items)

        self.mainbox.refresh()

    def projects_by_cmd(self, cmd):
        projects = [project['name'] for project in self.todo.get_projects()]
        selected = re.findall('(?<=#)\w+', cmd)
        return [project for project in projects
                for match in selected
                if project.find(match) > -1]

    def items_by_cmd(self, cmd):
        sel_proj = self.projects_by_cmd(cmd)
        if len(sel_proj):
            items = self.todo.get_items(projects=sel_proj)
        else:
            items = self.todo.get_items()

        clean_cmd = [word for word in cmd.split(' ')
                     if not word.startswith('#')]

        filt_items = []
        for item in items:
            if all([cmd in item.data['content'] for cmd in clean_cmd]):
                filt_items.append(item)

        return filt_items

    def check_available_commands(self):
        if len(self.main_items) == 1:
            self.command_available(Commands.COMPLETE)
        else:
            self.command_unavailable(Commands.COMPLETE)

        if len(self.main_items) == 0:
            self.command_available(Commands.ADD)
        else:
            self.command_unavailable(Commands.ADD)


    def menu_loop(self):
        self.handle_user_input()

        self.selected_projects = self.projects_by_cmd(self.command)
        self.main_items = self.items_by_cmd(self.command)
        self.check_available_commands()

        self.paint_projects()
        self.paint_command_bar()
        self.paint_option_box()
        self.paint_main_window()

        return True

    def list_items(self, items):
        items = sorted(items,
                       key=lambda item: (item.data['item_order']
                                         if 'item_order' in item.data else 0))
        self.mainbox.clear()
        height, width = self.mainbox.getmaxyx()
        max_row = height - 6
        row_num = len(items)
        # pages = int(ceil(row_num / max_row))
        # position = 1
        # page = 1
        for i, item in enumerate(items):
            text = item['content'].encode('UTF-8')
            if item['due_date_utc'] is not None:
                date = " ".join(item['due_date_utc'].split(' ')[1:5])
                date = datetime.datetime.strptime(date, "%d %b %Y %H:%M:%S")
                if item['all_day']:
                    date = date.strftime('  %d.%m.%Y')
                else:
                    date = date.strftime('  %d.%m.%Y %H:%M')


                text = self.shorten_string(item['content'].encode('UTF-8'), width-item['indent']*2-len(date))
            else:
                text = self.shorten_string(item['content'].encode('UTF-8'), width-item['indent']*2)
                date = None


            if len(items) == 1:
                self.mainbox.addstr(i+1, item['indent'] * 2, text, curses.A_STANDOUT)
            else:
                self.mainbox.addstr(i+1, item['indent'] * 2, text)

            if date is not None:
                self.mainbox.addstr(i+1, item['indent'] * 2 + len(text), date, curses.A_DIM)

            self.log.info(u'{}: {}'.format(item['content'], item['indent']))

            if i > max_row:
                self.log.info("{} items added".format(i))
                break

    def list_contents(self, item_list, box):
        box.clear()
        height, width = box.getmaxyx()
        max_row = height - 6
        row_num = len(item_list)
        # pages = int(ceil(row_num / max_row))
        # position = 1
        # page = 1
        for i in range(len(item_list)):
            text = self.shorten_string(item_list[i].encode('UTF-8'), width-2)
            if len(item_list) == 1:
                box.addstr(i+1, 2, text, curses.A_STANDOUT)
            else:
                box.addstr(i+1, 2, text)
            if i > max_row:
                self.log.info("{} items added".format(i))
                break

    def splash(self):
        self.stdscr.border(2)
        height, width = self.stdscr.getmaxyx()
        midheight = int(height / 2)
        midwidth = int(width / 2)
        self.stdscr.addstr(midheight, midwidth - 4, "Todoist!")
        self.stdscr.refresh()
        time.sleep(1)
        self.stdscr.clear()

if __name__== '__main__':
    ui = CursesUI()
    ui.run()
