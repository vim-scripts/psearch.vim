# -*- coding: utf-8 -*-
"""
psearch.py
~~~~~~~~~~

Main class for the PSearch plugin.
"""

import os
import re
import sys
import vim
import bisect

sys.path.insert(0, os.path.dirname(
    vim.eval('globpath(&runtimepath, "autoload/psearch.py")')))

import psearch.utils.settings
import psearch.utils.misc
import psearch.input


class PSearch:

    def __init__(self):
        self.settings = psearch.utils.settings
        self.misc = psearch.utils.misc

        self.name = 'psearch.launcher'
        self.prompt = self.settings.get('prompt')
        self.max_height = self.settings.get('max_height', int)

        self.input_so_far = ''
        self.launcher_curr_pos = None
        self.find_new_matches = True
        self.matches = {}
        self.view_buffer = None

        self.curr_buf = None
        self.curr_buf_pos = None

        self.mapper = {}
        self.nohidden_set = False
        self.RE_MATH = re.compile('(\d+|\+|\*|\/|-)')

        self.selection_pending = False
        self.mark_map = {}

        self.cache = []

        # setup highlight groups
        vim.command('hi link PSearchLine String')
        vim.command('hi link PSearchDots Comment')
        vim.command('hi link PSearchMatches Search')
        vim.command('hi link PSearchMarks Type')

    def reset_launcher(self):
        """To reset the launcher state."""
        self.input_so_far = ''
        self.launcher_curr_pos = None
        self.find_new_matches = True
        self.matches = {}
        self.view_buffer = None
        self.curr_buf = None
        self.curr_buf_pos = None
        self.mapper = {}
        self.nohidden_set = False
        self.selection_pending = False
        self.mark_map = {}
        self.cache = []

    def setup_buffer(self):
        """To setup buffer properties of the matches list window."""
        vim.command("setlocal buftype=nofile")
        vim.command("setlocal bufhidden=wipe")
        vim.command("setlocal encoding=utf-8")
        vim.command("setlocal nobuflisted")
        vim.command("setlocal noundofile")
        vim.command("setlocal nobackup")
        vim.command("setlocal noswapfile")
        vim.command("setlocal nowrap")
        vim.command("setlocal nonumber")
        if vim.eval("&hidden") == '0':
            vim.command("set hidden")
            self.nohidden_set = True  # mmh...

    def clear_highlighting(self):
        """To clear search highlighting."""
        for match in vim.eval('getmatches()'):
            if match['group'] == 'PSearchMatches':
                vim.command("call matchdelete({0})".format(match['id']))

    def highlight(self):
        """To setup highlighting."""
        vim.command("call matchadd('PSearchLine', '\%<6vLine:')")
        vim.command("call matchadd('PSearchDots', '\%<18v\.')")
        vim.command("call matchadd('PSearchMarks', '\ <[a-z]>\ ')")
        if self.input_so_far:
            vim.command('call matchadd("PSearchMatches", "\\\\M\\\\%>18v{0}")'
                .format(self.input_so_far
                    .replace('\\', '\\\\').replace('"', '\\"')))

    def close_launcher(self):
        """To close the matches list window."""
        self.misc.go_to_win(self.misc.bufwinnr(self.name))
        if self.misc.bufname() == self.name:
            vim.command('q')
            self.misc.go_to_win(self.misc.bufwinnr(self.curr_buf.name))
            if self.nohidden_set:
                vim.command("set nohidden")
            self.reset_launcher()

    def open_launcher(self):
        """To open the matches list window."""
        vim.command('silent! botright split {0}'.format(self.name))
        self.setup_buffer()

    def buffers_with_matches(self):
        lst = list(set(self.misc.buffers()) &
                   set(self.matches.keys()))
        if self.curr_buf.name not in lst:
            lst.append(self.curr_buf.name)
        return lst

    def search(self, target):
        self.matches.clear()
        if self.misc.bufwinnr(self.curr_buf.name):
            self.misc.go_to_win(self.misc.bufwinnr(self.curr_buf.name))

            # this speeds things up with multi buffer search
            eventignore = vim.eval("&eventignore")
            vim.command("set eventignore=all")

            vim.command('silent! bufdo '
                'py psearch_plugin.search_single_buffer("{0}")'
                .format(target.replace('\\', '\\\\').replace('"', '\\"')))
            vim.command("b {0}".format(self.curr_buf.name))

            vim.command("set eventignore={0}".format(eventignore))
            self.misc.go_to_win(self.misc.bufwinnr(self.name))

    def search_single_buffer(self, target):
        """To search in the current buffer the given pattern."""
        buf = vim.current.buffer
        if not buf.name:
            return

        self.matches[buf.name] = []
        if not self.input_so_far:
            return

        orig_pos = vim.current.window.cursor
        vim.current.window.cursor = (1, 1)

        while True:
            try:
                line, col = vim.eval('searchpos("\\\\M{0}", "W")'
                    .format(self.input_so_far
                        .replace('\\', '\\\\').replace('"', '\\"')))
            except vim.error:
                break
            line, col = int(line), int(col)
            if line == 0 and col == 0:
                break
            if not any(True for m in self.matches[buf.name]
                        if m[0] == line):
                self.matches[buf.name].append((line, col, buf[line - 1]))

        vim.current.window.cursor = orig_pos

    def update_launcher(self):
        """To update the matches list content."""
        if not self.misc.bufwinnr(self.name):
            self.open_launcher()

        self.mapper.clear()
        self.clear_highlighting()
        self.misc.go_to_win(self.misc.bufwinnr(self.name))
        self.misc.set_buffer(None)

        buffer_list = sorted(self.buffers_with_matches())
        if not self.view_buffer:
            self.view_buffer = self.curr_buf.name

        i = buffer_list.index(self.view_buffer)
        buf_prev = buffer_list[-1 if not i else i - 1]
        buf_next = buffer_list[0 if i == len(buffer_list) - 1 else i + 1]

        vim.command("setlocal stl=\ \ ⇠\ {0}\ \ [{1}]\ \ {2}\ ⇢\ \ ".format(
            os.path.split(buf_prev)[1].replace(' ', '\\'),
            os.path.split(self.view_buffer)[1].replace(' ', '\\'),
            os.path.split(buf_next)[1].replace(' ', '\\')))

        # self.matches = {'bufname': [(linenr, col, line), ...], ...}
        if self.find_new_matches:
            if not self.cache:
                self.search(self.input_so_far)
                self.cache = list(self.matches)

            _matches = self.matches[self.view_buffer]
            if _matches:
                if self.view_buffer == self.curr_buf.name:
                    pos = bisect.bisect_left(_matches, self.curr_buf_pos)
                    _matches.insert(pos, self.curr_buf_pos)
        else:
            _matches = self.matches[self.view_buffer]

        if _matches:
            self.misc.set_buffer(
                [self.render_line(m, j) for j, m in enumerate(_matches)])

            # set the position to the current line
            if self.find_new_matches:
                if self.view_buffer == self.curr_buf.name:
                    self.launcher_curr_pos = pos
                else:
                    self.launcher_curr_pos = 0

            if self.launcher_curr_pos is not None:
                length = len(vim.current.buffer)
                if self.launcher_curr_pos >= length:
                    self.launcher_curr_pos = length - 1
                vim.current.window.cursor = (self.launcher_curr_pos + 1, 1)

            self.render_curr_line()
            self.highlight()

            # adjust the window height according to the total
            # number of matches
            n = len(_matches)
            if n > self.max_height:
                vim.current.window.height = self.max_height
            else:
                vim.current.window.height = n

            vim.command("normal! zz")

        else:
            vim.command('syntax clear')
            self.misc.set_buffer([' nothing found...'])
            vim.current.window.height = 1
            self.launcher_curr_pos = 0

    def render_line(self, match, i):
        """To format a match displayed in the matches list window."""
        if len(match) == 2:
            return '  ------ * ------'.format(match[0])
        else:
            self.mapper[i] = match
            return '  Line: {0: <4}  ... {1}'.format(match[0], match[2])

    def render_curr_line(self):
        """To format the current line in the laucher window."""
        if self.launcher_curr_pos is None:
            self.launcher_curr_pos = len(vim.current.buffer) - 1
        line = vim.current.buffer[self.launcher_curr_pos]
        vim.current.buffer[self.launcher_curr_pos] = '▸ ' + line[2:]

    def go_to_selected_match(self):
        """To go to the selected match."""
        match = self.mapper.get(self.launcher_curr_pos)
        if match and self.view_buffer:
            self.misc.go_to_win(self.misc.bufwinnr(self.curr_buf.name))
            vim.command('silent! e {0}'.format(self.view_buffer))
            vim.current.window.cursor = (match[0], match[1] - 1)
            vim.command("normal! zz")
            return True

    def open(self, word_under_cursor):
        """To open the launcher."""

        if not vim.current.buffer.name:
            return

        if word_under_cursor:
            self.input_so_far = word_under_cursor

        self.curr_buf = vim.current.buffer
        self.curr_buf_pos = vim.current.window.cursor

        input = psearch.input.Input()
        # Start the input loop
        while True:
            self.find_new_matches = False

            # Display the prompt and the text the user has been typed so far
            vim.command('echo "{0}{1}"'.format(
                self.prompt,
                self.input_so_far.replace('\\', '\\\\').replace('"', '\\"')))

            # Get the next character
            input.reset()
            input.get()

            if input.RETURN or input.CTRL and input.CHAR == 'g':
                if self.go_to_selected_match():
                    self.close_launcher()
                    break

            if input.BS:
                # This acts just like the normal backspace key
                self.input_so_far = self.input_so_far[:-1]
                self.find_new_matches = True
                self.mapper.clear()
                self.cache = []
                # Reset the position of the selection in the matches list
                # because the list has to be rebuilt
                self.launcher_curr_pos = None

            elif input.ESC or input.INTERRUPT:
                # The user want to close the launcher
                self.close_launcher()
                break

            elif input.UP or input.CTRL and input.CHAR == 'k':
                # Move up in the matches list
                if self.launcher_curr_pos > 0:
                    self.launcher_curr_pos -= 1

            elif input.DOWN or input.CTRL and input.CHAR == 'j':
                # Move down in the matches list
                last_index = len(vim.current.buffer) - 1
                if self.launcher_curr_pos < last_index:
                    self.launcher_curr_pos += 1

            elif input.LEFT or input.CTRL and input.CHAR == 'h':
                buf_list = sorted(self.buffers_with_matches())
                i = buf_list.index(self.view_buffer)
                self.view_buffer = buf_list[-1 if not i else i - 1]

            elif input.RIGHT or input.CTRL and input.CHAR == 'l':
                buf_list = sorted(self.buffers_with_matches())
                i = buf_list.index(self.view_buffer)
                self.view_buffer = buf_list[
                    0 if i == len(buf_list) - 1 else i + 1]

            elif input.CTRL and input.CHAR == 't':
                self.launcher_curr_pos = 0

            elif input.CTRL and input.CHAR == 'b':
                self.launcher_curr_pos = len(vim.current.buffer) - 1

            elif input.CTRL and input.CHAR == 'a':
                self.selection_pending = True
                marks = list('qwertyuiopasdfghjklzxcvbnm')
                b, w = vim.current.buffer, vim.current.window

                vim.command("normal! H")
                top_line = w.cursor[0]
                vim.command("normal! L")
                bot_line = w.cursor[0]

                span = bot_line - top_line
                if span > len(marks):
                    diff = span - len(marks)
                    top_line += diff / 2
                    bot_line -= diff / 2

                for i in range(top_line-1, bot_line):
                    line = b[i]
                    if 'Line:' in line and marks:
                        m = marks.pop()
                        b[i] = line.replace('...', '<{0}>'.format(m), 1)
                        self.mark_map[m] = i

                self.misc.redraw()
                continue

            elif input.CHAR:

                if self.selection_pending:

                    selected_line = self.mark_map.get(input.CHAR)
                    if selected_line:
                        self.launcher_curr_pos = selected_line
                        self.go_to_selected_match()
                        self.close_launcher()
                        break

                else:

                    # A printable character has been pressed. We have to
                    # remember it so that in the next loop we can display
                    # exactly what the user has been typed so far
                    self.input_so_far += input.CHAR
                    self.find_new_matches = True
                    self.mapper.clear()
                    self.cache = []

                    # Reset the position of the selection in the matches list
                    # because the list has to be rebuilt
                    self.launcher_curr_pos = None

            else:
                self.misc.redraw()
                continue

            self.update_launcher()

            # Clean the command line
            self.misc.redraw()
