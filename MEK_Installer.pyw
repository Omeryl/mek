#!/usr/bin/env python3

import importlib
import os
import subprocess
import sys
import tkinter as tk
import traceback
import zipfile
from threading import Thread
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from io import StringIO
from os import path
from sys import platform
from urllib import request

curr_dir = os.path.abspath(os.curdir)
mek_download_url = "https://bitbucket.org/Moses_of_Egypt/mek/get/default.zip"

mek_program_package_names = ("mozzarilla", "refinery", )
mek_library_package_names = ("reclaimer", )
program_package_names     = ("binilla", )
library_package_names     = ("supyr_struct", "arbytmap", )

required_module_extensions = {
    "arbytmap.ext": ("arbytmap_ext", "bitmap_io_ext", "dds_defs_ext",
                     "raw_packer_ext", "raw_unpacker_ext", "swizzler_ext")
    }

if "linux" in platform.lower():
    platform = "linux"

if platform == "linux":
    pip_exec_name = "pip3"
else:
    pip_exec_name = "pip"


class IORedirecter(StringIO):
    # Text widget to output text to
    text_out = None

    def __init__(self, text_out, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.text_out = text_out

    def write(self, string):
        self.text_out.config(state=tk.NORMAL)
        self.text_out.insert(tk.END, string)
        self.text_out.see(tk.END)
        self.text_out.config(state=tk.DISABLED)


def is_module_fully_installed(mod_path, attrs):
    if isinstance(attrs, str):
        attrs = (attrs, )

    mods = list(mod_path.split("."))
    mod_name = mod_path.replace(".", "_")
    glob = globals()
    if mod_name not in glob:
        import_str = ""
        if len(mods) > 1:
            for mod in mods[: -1]:
                import_str += "%s." % mod
            import_str = "from %s " % import_str[:-1]
        import_str += "import %s as %s" % (mods.pop(-1), mod_name)
        exec("global %s" % mod_name, glob)
        exec(import_str, glob)
    else:
        importlib.reload(glob[mod_name])
    mod = glob[mod_name]

    result = True
    for attr in attrs:
        result &= hasattr(mod, attr)
    return result


def _do_subprocess(exec_strs, action="Action", app=None):
    exec_strs = tuple(exec_strs)
    while True:
        if app is not None and getattr(app, "_running_thread", 1) is None:
            raise SystemExit(0)

        result = 1
        try:
            print("-"*80)
            print("%s "*len(exec_strs) % exec_strs)

            with subprocess.Popen(exec_strs, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=False) as p:
                if app is not None:
                    try:
                        for line in p.stdout:
                            app.write_redirect(line)
                    except:
                        p.kill()
                        p.wait()
                        raise
                else:
                    while p.poll() is None:
                        # wait until the process has finished
                        pass

            result = p.wait()
        except Exception:
            print(traceback.format_exc())

        if app is not None and getattr(app, "_running_thread", 1) is None:
            raise SystemExit(0)

        if result:
            print("  Error code: %02x" % result)

        if result and exec_strs[0] != "python":
            print("  %s failed. Trying with different arguments." % action)
            exec_strs = ("python", "-m") + exec_strs
        else:
            break

    if result:
        print("  %s failed.\n" % action)
    else:
        print("  %s succeeded.\n" % action)
    return result


def install(install_path=None, install_mek_programs=False, app=None):
    result = 1
    try:
        for mod_name in mek_program_package_names:
            exec_strs = [pip_exec_name, "install", mod_name, "--no-cache-dir"]

            if install_path is not None:
                exec_strs += ['--target=%s' % install_path]
            result &= _do_subprocess(exec_strs, "Install", app)

        if not install_mek_programs:
            pass
        elif install_path is None:
            download_mek_to_folder(curr_dir)
        else:
            download_mek_to_folder(install_path)
    except Exception:
        print(traceback.format_exc())

    print("-"*10 + " Finished " + "-"*10 + "\n")
    if platform != "linux":
        successes = []

        for mod_path, attrs in required_module_extensions.items():
            successes.append(is_module_fully_installed(mod_path, attrs))
            if not successes[-1]:
                print("%s did not fully compile its C extensions." % mod_path)

        if sum(successes) != len(successes):
            warn_msvc_compile()

    return result


def uninstall(partial_uninstall=True, app=None):
    result = 1
    try:
        # by default we wont uninstall supyr_struct, arbtmap, or
        # binilla since they may be needed by other applications
        modules = list(mek_program_package_names + mek_library_package_names)
        if not partial_uninstall:
            modules.extend(program_package_names + library_package_names)

        for mod_name in modules:
            exec_strs = [pip_exec_name, "uninstall", mod_name, "-y"]
            result &= _do_subprocess(exec_strs, "Uninstall", app)
    except Exception:
        print(traceback.format_exc())

    print("-"*10 + " Finished " + "-"*10 + "\n")
    return result


def update(install_path=None, force_reinstall=False,
           install_mek_programs=False, app=None):
    result = 0
    try:
        for mod in (library_package_names     + program_package_names +
                    mek_library_package_names + mek_program_package_names):

            exec_strs = [pip_exec_name, "install", mod,
                         "--upgrade", "--no-cache-dir"]
            if install_path is not None:
                exec_strs += ['--target=%s' % install_path]
            if force_reinstall:
                exec_strs += ['--force-reinstall']
            result |= _do_subprocess(exec_strs, "Update", app)

        if not install_mek_programs:
            pass
        elif install_path is None:
            download_mek_to_folder(curr_dir)
        else:
            download_mek_to_folder(install_path)

    except Exception:
        print(traceback.format_exc())

    print("-"*10 + " Finished " + "-"*10 + "\n")
    if platform != "linux":
        successes = []

        for mod_path, attrs in required_module_extensions.items():
            successes.append(is_module_fully_installed(mod_path, attrs))
            if not successes[-1]:
                print("%s did not fully compile its C extensions." % mod_path)

        if sum(successes) != len(successes):
            warn_msvc_compile()

    return result


def download_mek_to_folder(install_dir, src_url=None):
    if src_url is None:
        src_url = mek_download_url
    print("Downloading newest version of MEK from:\n    %s\nto:\n    %s" %
          (src_url, install_dir))

    mek_zipfile_path, _ = request.urlretrieve(src_url)
    if not mek_zipfile_path:
        print("    Could not download MEK zipfile.")
        return

    if os.sep == "/":  find = "\\"
    if os.sep == "\\": find = "/"

    with zipfile.ZipFile(mek_zipfile_path) as mek_zipfile:
        for name in mek_zipfile.namelist():
            filename = os.path.join(install_dir, name.split("/", 1)[-1])
            filename = filename.replace(find, os.sep)
            dirpath = os.path.dirname(filename)

            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            with mek_zipfile.open(name) as zf, open(filename, "wb+") as f:
                f.write(zf.read())

    try: os.remove(mek_zipfile_path)
    except Exception: pass


def run():
    try:
        installer = MekInstaller()
        installer.mainloop()
    except Exception:
        print(traceback.format_exc())
        input()


def warn_msvc_compile():
    if sys.version_info[0] != 3 or sys.version_info[1] < 3:
        pass
    elif sys.version_info[1] in (3, 4):
        messagebox.showinfo(
            "Accelerator modules were not compiled",
            "A properly set up environment is required for the accelerator\n"
            "modules these programs utilize to be compiled.\n"
            "These accelerators make certain things possible, like bitmap viewing.\n"
            "The MEK will still work fine without them, but anything that relies\n"
            "on their speedup will be significantly slower(sometimes 100x slower).\n\n"

            "If possible, the easiest way to fix this problem is to run this program's\n"
            "uninstall command, uninstall your current version of python, download and\n"
            "install python 3.5 or higher, download and install Microsoft's build tools\n"
            "for Visual Studio 2017 from the link below, and run this installer again.\n\n"

            "visualstudio.com/downloads/#build-tools-for-visual-studio-2017\n\n"

            "If you cannot change your python version, follow these direction:\n"
            "Run this program's uninstall command, follow the directions from the\n"
            "link below to get your system configured to compile C extensions, and\n"
            "run this installer again.\n\n"

            "https://blog.ionelmc.ro/2014/12/21/compiling-python-extensions-on-windows/#for-python-3-4\n\n"

            "If you have already done all of these things and you still\n"
            "get this message, please contact me so I can fix the problem.\n"
            )
    elif sys.version_info[1] > 4:
        messagebox.showinfo(
            "Accelerator modules were not compiled",
            "The Visual Studio 2017 build tools are required for the\n"
            "accelerator modules these programs utilize to be compiled.\n"
            "These accelerators make certain things possible, like bitmap viewing.\n"
            "The MEK will still work fine without them, but anything that relies\n"
            "on their speedup will be significantly slower(sometimes 100x slower).\n\n"

            "Run this program's uninstall command, download and install the\n"
            "build tools from the link below, and run this installer again.\n\n"

            "visualstudio.com/downloads/#build-tools-for-visual-studio-2017\n\n"

            "If you already have the build tools installed and you still\n"
            "get this message, please contact me so I can fix the problem.\n"
            )



class MekInstaller(tk.Tk):
    '''
    This class provides an interface for installing, uninstalling,
    and updating the libraries and programs that the MEK relies on.
    '''
    _running_thread = None
    alive = False

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("MEK installer v2.0.0")
        self.geometry("480x400+0+0")
        self.minsize(480, 260)
        
        self.install_dir = tk.StringVar(self)
        self.force_reinstall   = tk.BooleanVar(self, 1)
        self.update_programs   = tk.BooleanVar(self, 1)
        self.portable          = tk.BooleanVar(self)
        self.partial_uninstall = tk.BooleanVar(self)

        self.install_dir.set(curr_dir)

        # make the frames
        self.install_dir_frame = tk.LabelFrame(self, text="MEK directory")
        self.settings_frame    = tk.LabelFrame(self, text="Settings")
        self.actions_frame     = tk.LabelFrame(self, text="Action to perform")

        self.inner_settings0 = tk.Frame(self.settings_frame)
        self.inner_settings1 = tk.Frame(self.settings_frame)
        self.inner_settings2 = tk.Frame(self.settings_frame)
        self.inner_settings3 = tk.Frame(self.settings_frame)

        # add the filepath box
        self.install_dir_entry = tk.Entry(
            self.install_dir_frame, textvariable=self.install_dir)
        self.install_dir_entry.config(width=55, state='disabled')

        # add the buttons
        self.install_dir_browse_btn = tk.Button(
            self.install_dir_frame, text="Browse",
            width=6, command=self.install_dir_browse)
        
        self.install_btn = tk.Button(
            self.actions_frame, text="Install",
            width=10, command=self.install)
        self.uninstall_btn = tk.Button(
            self.actions_frame, text="Uninstall",
            width=10, command=self.uninstall)
        self.update_btn = tk.Button(
            self.actions_frame, text="Update",
            width=10, command=self.update)

        # add the checkboxes
        self.force_reinstall_checkbox = tk.Checkbutton(
            self.inner_settings0, variable=self.force_reinstall,
            text="force reinstall when updating libraries")
        self.update_programs_checkbox = tk.Checkbutton(
            self.inner_settings1, variable=self.update_programs,
            text="install up-to-date MEK when installing/updating")
        self.portable_checkbox = tk.Checkbutton(
            self.inner_settings2, variable=self.portable,
            text="portable install (installs to/updates the 'MEK directory' above)")
        self.partial_uninstall_checkbox = tk.Checkbutton(
            self.inner_settings3, variable=self.partial_uninstall,
            text="partial uninstall (remove only MEK related libraries and programs)")

        self.make_io_text()

        # pack everything
        self.install_dir_entry.pack(side='left', fill='x', expand=True)
        self.install_dir_browse_btn.pack(side='left', fill='both')

        self.force_reinstall_checkbox.pack(side='left', fill='both')
        self.update_programs_checkbox.pack(side='left', fill='both')
        self.portable_checkbox.pack(side='left', fill='both')
        self.partial_uninstall_checkbox.pack(side='left', fill='both')

        self.install_btn.pack(side='left', fill='x', padx=10)
        self.update_btn.pack(side='left', fill='x', padx=10)
        self.uninstall_btn.pack(side='right', fill='x', padx=10)

        self.install_dir_frame.pack(fill='x')
        self.settings_frame.pack(fill='both')
        self.actions_frame.pack(fill='both')

        self.inner_settings0.pack(fill='both')
        self.inner_settings1.pack(fill='both')
        self.inner_settings2.pack(fill='both')
        self.inner_settings3.pack(fill='both')

        self.io_frame.pack(fill='both', expand=True)
        if sys.version_info[0] < 3 or sys.version_info[1] < 3:
            messagebox.showinfo(
                "Incompatible python version",
                "The MEK requires python 3.3.0 or higher to be installed.\n" +
                ("You are currently running version %s.%s.%s\n\n" % tuple(sys.version_info[:3])) +
                "If you know you have python 3.3.0 or higher installed, then\n" +
                "the version your operating system is defaulting to when\n" +
                ("running python files is %s.%s.%s\n\n" % tuple(sys.version_info[:3]))
                )
            self.destroy()
        self.alive = True

    def destroy(self):
        sys.stdout = sys.orig_stdout
        self._running_thread = None
        tk.Tk.destroy(self)
        self.alive = False
        raise SystemExit(0)

    def make_io_text(self):
        self.io_frame = tk.Frame(self, highlightthickness=0)
        self.io_text = tk.Text(self.io_frame, state='disabled')
        self.io_scroll_y = tk.Scrollbar(self.io_frame, orient='vertical')

        self.io_scroll_y.config(command=self.io_text.yview)
        self.io_text.config(yscrollcommand=self.io_scroll_y.set)

        self.io_scroll_y.pack(fill='y', side='right')
        self.io_text.pack(fill='both', expand=True)
        sys.orig_stdout = sys.stdout
        sys.stdout = IORedirecter(self.io_text)

    def start_thread(self, func, *args, **kwargs):
        def wrapper(app=self, func_to_call=func, a=args, kw=kwargs):
            try:
                kw['app'] = app
                func_to_call(*a, **kw)
            except Exception:
                print(traceback.format_exc())

            app._running_thread = None

        new_thread = Thread(target=wrapper)
        self._running_thread = new_thread
        new_thread.daemon = True
        new_thread.start()

    def install_dir_browse(self):
        if self._running_thread is not None:
            return
        dirpath = askdirectory(initialdir=self.install_dir.get())
        if dirpath:
            self.install_dir.set(path.normpath(dirpath))

    def install(self):
        if self._running_thread is not None:
            return

        install_dir = None
        valid_dir = True
        if self.portable.get():
            install_dir = self.install_dir.get()
        return self.start_thread(install, install_dir,
                                 self.update_programs.get())

    def uninstall(self):
        if self._running_thread is not None:
            return
        if self.portable.get():
            names_str = ""
            for name in (mek_program_package_names + program_package_names +
                         mek_library_package_names + library_package_names):
                names_str = "%s%s\n" % (names_str, name)
                package_ct += 1

            package_ct = 0
            return messagebox.showinfo(
                "Uninstall not necessary",
                "Portable installations do not require you to do anything\n"
                "special to uninstall them. Just delete the folders in the\n"
                "directory you specified that start with these names:\n\n"

                "%s\nThere should be from %s to %s folders." % (
                    names_str, package_ct, 2*package_ct)
                )
        if messagebox.askyesno(
            "Uninstall warning",
            "Are you sure you want to uninstall all the libraries\n"
            "and components that the MEK depends on?"):
            return self.start_thread(uninstall, self.partial_uninstall.get())

    def update(self):
        if self._running_thread is not None:
            return
        install_dir = None
        if self.portable.get():
            install_dir = self.install_dir.get()
        return self.start_thread(update, install_dir,
                                 self.force_reinstall.get(),
                                 self.update_programs.get())

    def write_redirect(self, string):
        if not self.alive:
            print(string)
            return

        self.io_text.config(state='normal')
        self.io_text.insert('end', string)
        self.io_text.see('end')
        self.io_text.config(state='disabled')

if __name__ == "__main__":
    run()
