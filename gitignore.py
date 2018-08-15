import os
import zipfile

import sublime
import sublime_plugin

GITIGNORE_EXT = '.gitignore'
loader = None


def plugin_loaded():
    global loader
    loader = Loader()


class Loader():
    _bp_list = []
    _bp_folder = 'boilerplates'
    _user_gitignore_folder = os.path.join('User', 'gitignores')
    _package_path = None
    _is_zipfile = False
    _address = {}
    _user_files = []

    def __init__(self):
        self._find_package_path()
        self._is_zipfile = zipfile.is_zipfile(self._package_path)
        self._build_list()

    def _find_package_path(self):
        paths = [os.path.join(sublime.installed_packages_path(), 'Gitignore.sublime-package'),
                 os.path.join(sublime.packages_path(), 'Gitignore'),
                 os.path.join(sublime.packages_path(), 'Sublime-Gitignore')]
        for path in paths:
            if os.path.exists(path):
                self._package_path = path
                break

    def _list_dir(self, user_file=False):
        if not user_file and self._is_zipfile:
            # Dealing with .sublime-package file
            package = zipfile.ZipFile(self._package_path, 'r')
            path = self._bp_folder + os.sep
            return [file for file in package.namelist() if file.startswith(path) and file.endswith(GITIGNORE_EXT)]
        else:
            path = (os.path.join(sublime.packages_path(), self._user_gitignore_folder)
                    if user_file
                    else os.path.join(self._package_path, self._bp_folder))
            return [os.path.join(step[0][len(path) + 1:], file)
                    for step in os.walk(path) for file in step[2] if file.endswith(GITIGNORE_EXT)]

    def _load_file(self, path, is_user_file=False):
        file_path = (os.path.join(sublime.packages_path(), self._user_gitignore_folder, path)
                     if is_user_file
                     else os.path.join(self._package_path, self._bp_folder, path))
        if not is_user_file and self._is_zipfile:
            # Dealing with .sublime-package file
            package = zipfile.ZipFile(self._package_path, 'r')
            with package.open(path, 'r') as f:
                text = f.read().decode()
        else:
            with open(file_path, 'r') as f:
                text = f.read()
        return text

    def _get_key(self, bp_file):
        return bp_file[bp_file.rfind(os.sep) + 1:].replace(GITIGNORE_EXT, '')

    def _build_list(self):
        for bp_file in self._list_dir():
            self._address[self._get_key(bp_file)] = bp_file
        for bp_file in self._list_dir(True):
            self._address[self._get_key(bp_file)] = bp_file
            self._user_files.append(self._get_key(bp_file))
        self._bp_list = list(self._address.keys())
        self._bp_list.sort()

    def get_list(self):
        return self._bp_list.copy()

    def load_bp(self, bp):
        return self._load_file(self._address[bp], bp in self._user_files)


class RunCommand(sublime_plugin.WindowCommand):
    def show_quick_panel(self, options, done):
        # Fix from http://www.sublimetext.com/forum/viewtopic.php?f=6&t=10999
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 10)

    def run(self):
        self.chosen_array = []
        self.bp_list = loader.get_list()
        self.is_first = True
        self.show_quick_panel(self.bp_list, self.on_select)

    def on_select(self, index):
        if not self.is_first and index == 0:
            self.write_file()
        elif index >= 0:
            self.chosen_array.append(self.bp_list[index])
            self.bp_list.remove(self.bp_list[index])
            if self.is_first:
                self.bp_list.insert(0, 'Done')
                self.is_first = False
            self.show_quick_panel(self.bp_list, self.on_select)

    def write_file(self):
        final = ''

        for bp in self.chosen_array:
            text = loader.load_bp(bp)
            final = final + '### ' + bp + ' ###\n\n' + text + '\n\n'

        final = final.strip()
        final += '\n'
        view = sublime.active_window().new_file()
        view.run_command('write', {'bp': final})


class WriteCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):
        self.view.insert(edit, 0, kwargs['bp'])
        self.view.set_name(GITIGNORE_EXT)
        self.view.set_syntax_file(os.path.join('Packages', 'Git Formats', 'Git Ignore.sublime-syntax'))
