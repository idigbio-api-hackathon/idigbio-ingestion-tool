#!/usr/bin/env python
# Running this script will build an exe if executed on Windows, and an
# application bundle (.app) if executed on Mac OS X
# Note that icons should be built before running this script. (We don't do this
# automatically because the icon-building script wouldn't work on Windows)

import sys
import os.path

SCRIPT_PATH = os.path.abspath("..")
SCRIPT = "main.py"
LIB_PATH = os.path.join(SCRIPT_PATH, "lib")
APP_NAME = "iDigBio Ingestion Tool"
RESOURCES = [(os.path.join("..", p), p) for p in ["www", "etc"]]
sys.path += [SCRIPT_PATH, LIB_PATH]

if sys.platform == "darwin": # Mac OS X
    print("Building for Mac OS X using py2app")
    sys.argv[1:1] = ["py2app"]
    
    from setuptools	import setup
    import shutil
    import subprocess
    import sys
    
    options = {
        "py2app":{
            "includes": ["cherrypy.wsgiserver",
                         "cherrypy.wsgiserver.wsgiserver3"],
            "iconfile": os.path.join("icons", "osx_icon", "icon.icns"),
            "site_packages": True,
            "resources": RESOURCES
        }
    }
    setup(app=[SCRIPT], setup_requires=["py2app"], options=options)
    print("Patching app file to open terminal window")
    app_path = "dist/hworld_server.app/Contents/MacOS/"
    shutil.move(app_path + "main",
                app_path + "base_exec")
    shutil.copy("osx_bin", app_path + "main")
    subprocess.check_call(["chmod", "+x", app_path + "main"])
    
elif sys.platform.startswith("win"): # Windows
    print("Building for Windows using cx_Freeze")
    sys.argv[1:1] = ["build"]
    
    from cx_Freeze import Executable, setup
    
    options = {
        "build_exe": {
            "compressed": True,
            "includes": ["cherrypy.wsgiserver",
                         "cherrypy.wsgiserver.wsgiserver3", "webbrowser"],
            "packages": ["sqlite3", "sqlalchemy.dialects.sqlite"],
            "excludes": ["tkinter", "Tkinter", "ttk", "Tix"],
            "icon": os.path.join("icons", "win_icon", "icon.ico"),
            "include_files": RESOURCES
        }
    }
    executable = Executable(os.path.join(SCRIPT_PATH, SCRIPT), compress=True,
                            targetName=APP_NAME + ".exe")
    setup(options=options, executables=[executable])
else:
    raise Exception("Unsupported Platform '%s'." % sys.platform)
