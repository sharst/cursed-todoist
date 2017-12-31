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
    ADD_SUBTASK = "SUBTASK"
    ADD_TASK_BELOW = "TASK BELOW"
    SELECT = "SELECT"
    COMPLETE = "COMPLETE"
    GOTO_PROJECT = "GO TO PROJECT"
    QUIT = "QUIT"

class CursesUI(object):
    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        self.todo = TodoistAbstractor()
        self.main_items = []
        self.selected_projects = []
        self.selected_task = None
        self.available_commands = []
        self.active_command = 0
        self.ctrl_pressed = False
        self.command = u""
        self.menu_width = 25
        self.option_width = 15
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
        self.optionbox = curses.newwin(2, self.option_width, height-2, width - (self.option_width + 1))

    def resize_windows(self):
        height, width = self.stdscr.getmaxyx()
        self.menubox.resize(height, self.menu_width)
        self.mainbox.resize(height-3, width - (self.menu_width + 1))
        self.commandbox.resize(2, width - (self.menu_width + 1) - (self.option_width + 1))
        self.optionbox.resize(2, self.option_width)

        self.commandbox.mvwin(height-2, self.menu_width + 1)
        self.optionbox.mvwin(height-2, width - (self.menu_width + 1))

    def execute_command(self, user_input, command):
        if command in [Commands.ADD,
                       Commands.ADD_SUBTASK,
                       Commands.ADD_TASK_BELOW]:
            project = None

            if self.selected_projects:
                project = self.selected_projects[0]

            content = " ".join([word for word in user_input.split(' ')
                                if not word.startswith('#')])

            if command == Commands.ADD:
                self.todo.add_item(content, project)
            elif command == Commands.ADD_SUBTASK:
                if self.selected_task is not None:
                    self.todo.add_item(content,
                                       self.selected_task['project_id'],
                                       item_order = self.selected_task['item_order'] + 1,
                                       indent = self.selected_task['indent'] + 1)

            elif command == Commands.ADD_TASK_BELOW:
                if self.selected_task is not None:
                    self.todo.add_item(content,
                                       self.selected_task['project_id'],
                                       item_order = self.selected_task['item_order'] + 1,
                                       indent = self.selected_task['indent'])
                    self.log.info("Added {}, order {}, indent {}".format(content,
                                                         self.selected_task['item_order'] + 1,
                                                         self.selected_task['indent']))


        elif command == Commands.COMPLETE:
            self.todo.complete_item(self.main_items[0]['id'])

        elif command == Commands.SELECT:
            self.log.info("Task selected!")
            self.selected_task = self.main_items[0]

        elif command == Commands.GOTO_PROJECT:
            name = self.todo.get_project_names([self.main_items[0]['project_id']])[0]
            self.command = u'#' + name + " "

        elif command == Commands.QUIT:
            curses.endwin()
            sys.exit()



    def handle_user_input(self):
        key = self.stdscr.getch()
        self.stdscr.nodelay(True)
        second = self.stdscr.getch()
        self.stdscr.nodelay(False)

        if key == curses.KEY_BACKSPACE:
            self.command = self.command[:-1]
        elif key == curses.KEY_ENTER or key == 10:
            if self.active_command < len(self.available_commands):
                self.execute_command(self.command, self.available_commands[self.active_command])
                self.command = u" ".join([word for word in self.command.split(' ')
                                          if word.startswith('#')]) + " "
        elif key == curses.KEY_RESIZE:
            self.resize_windows()
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
        self.menubox.clear()
        self.menubox.border(' ', 0, ' ', ' ', ' ', ' ', ' ', ' ')
        height, _ = self.menubox.getmaxyx()
        max_row = height - 3
        for i, project in enumerate(self.todo.get_projects()):
            if i < max_row:
                if project['name'] in self.selected_projects:
                    self.menubox.addstr(i+1,
                                        (project['indent']-1)*2,
                                        self.shorten_string(project['name'].encode('UTF-8'), self.menu_width-4),
                                        curses.A_STANDOUT)
                else:
                    self.menubox.addstr(i+1,
                                        (project['indent']-1)*2,
                                        self.shorten_string(project['name'].encode('UTF-8'), self.menu_width-4))
            elif i == max_row:
                self.menubox.addstr(i+1, 2, "...")
            else:
                break

        self.menubox.refresh()

    def shorten_string(self, string, cols, keep_back=False):
        if len(string) <= cols:
            return string
        else:
            if keep_back:
                return ".." + string[-(cols-2):]
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
        _, width = self.commandbox.getmaxyx()
        if self.command:
            cmd = self.shorten_string(self.command, width-2, keep_back=True)
            self.commandbox.addstr(1, 1, cmd.encode('UTF-8'))
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
        if len(clean_cmd) or len(sel_proj):
            for item in items:
                if all([cmd in item.data['content'] for cmd in clean_cmd]):
                    filt_items.append(item)

        return filt_items

    def check_available_commands(self):
        if len(self.main_items) == 1:
            self.command_available(Commands.COMPLETE)
            self.command_available(Commands.SELECT)
            self.command_available(Commands.GOTO_PROJECT)
        else:
            self.command_unavailable(Commands.COMPLETE)
            self.command_unavailable(Commands.SELECT)
            self.command_unavailable(Commands.GOTO_PROJECT)

        if len(self.main_items) == 0:
            self.command_available(Commands.ADD)
            if self.selected_task is not None:
                self.command_available(Commands.ADD_TASK_BELOW)
                self.command_available(Commands.ADD_SUBTASK)
        else:
            self.command_unavailable(Commands.ADD)
            self.command_unavailable(Commands.ADD_TASK_BELOW)
            self.command_unavailable(Commands.ADD_SUBTASK)

        if len(self.command) > 0:
            self.command_unavailable(Commands.QUIT)
        else:
            self.command_available(Commands.QUIT)


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

    def paint_item(self, y, x, item, standout=False):
        height, width = self.mainbox.getmaxyx()

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


        if standout:
            self.mainbox.addstr(y, x + item['indent'] * 2, text, curses.A_STANDOUT)
        else:
            self.mainbox.addstr(y, x + item['indent'] * 2, text)

        if date is not None:
            self.mainbox.addstr(y, x + item['indent'] * 2 + len(text), date, curses.A_DIM)


    def list_items(self, items):
        items = sorted(items,
                       key=lambda item: (item.data['project_id'],
                                         (item.data['item_order']
                                         if 'item_order' in item.data else 0)))
        self.mainbox.clear()
        height, width = self.mainbox.getmaxyx()
        max_row = height - 2
        row_num = len(items)
        # pages = int(ceil(row_num / max_row))
        # position = 1
        # page = 1
        for i, item in enumerate(items):
            if i >= max_row:
                break

            standout = False
            if len(items) == 1:
                standout = True

            self.paint_item(i+1, 0, item, standout=standout)


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
