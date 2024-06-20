import os.path
import plistlib
import subprocess
import time

import apsw
from watchdog.events import FileSystemEventHandler
from watchdog.observers.kqueue import KqueueObserver

from core import LOG


class DBEventHandler(FileSystemEventHandler):
    """Handles notification DB change events"""

    def __init__(self, db, rec_ids, hook_script_path):
        super().__init__()
        self.db = db
        self.rec_ids = rec_ids
        self.hook_script_path = hook_script_path
        self.allowed_apps = [
            "com.apple.reminders",
            "com.apple.calendar",
            "com.apple.clock",
            "com.apple.iCal",
        ]

        # "com.apple.ScriptEditor2",

    # don't really care about move, create, delete events
    def on_moved(self, event):
        pass

    def on_created(self, event):
        pass

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        super().on_modified(event)
        cursor = self.db.cursor()

        # select notifications we don't know about
        sql = f"SELECT rec_id, data FROM record WHERE rec_id NOT IN ({','.join('?' * len(self.rec_ids))})"

        # query the db, and process it to a list of notif. IDs and data.
        # the db might be busy so just wait it out.
        while True:
            try:
                new_objs = [
                    (col[0], process_plist(col[1]))
                    for col in cursor.execute(sql, self.rec_ids)
                ]
                break
            except apsw.BusyError:
                time.sleep(1)

        LOG.info(f"-- NEW -- : {len(new_objs)}")

        for obj in new_objs:
            # add new IDs to known IDs
            self.rec_ids.append(obj[0])

            # run script for each new notification if in allowed apps
            LOG.debug(f"applications: {obj[1]['app']}")
            if obj[1]["app"] in self.allowed_apps:
                LOG.info(f"{obj[1]['app']} is in allowed apps")
                LOG.info("running script...")
                words = obj[1]["title"].split(".")

                app = "".join(words[2:])
                result = subprocess.run(
                    args=[
                        str(self.hook_script_path),
                        app,
                        str(obj[1]["title"]),
                        str(obj[1]["body"]),
                        str(obj[1]["time"]),
                    ],
                    capture_output=True,
                )
                LOG.info(f"Notification info: {obj[1]}")
                LOG.debug(f"stdout: {result.stdout}")
                LOG.debug(f"stderr: {result.stderr}")


# process data plist from notification center db


def process_plist(raw_plist):
    notif_plist = plistlib.loads(raw_plist, fmt=plistlib.FMT_BINARY)

    processed_notif_dict = {"app": "", "title": "", "body": "", "time": ""}

    # notifications may not have... any fields? Weird bug,
    # but better than crashing and burning
    if "app" in notif_plist:
        processed_notif_dict["app"] = notif_plist["app"]

    if "titl" in notif_plist["req"]:
        processed_notif_dict["title"] = notif_plist["req"]["titl"]

    if "date" in notif_plist:
        processed_notif_dict["time"] = notif_plist["date"] + 978307200

    # the time in the plist is in the Core Data format, convert it to a
    # unix timestamp
    if "body" in notif_plist["req"]:
        processed_notif_dict["body"] = notif_plist["req"]["body"]

    return processed_notif_dict


def start_notification_observer():
    # contains notification center db, different for each user so we need to
    # find it every time.
    # LOG.init()
    darwin_user_folder = (
        subprocess.run(["getconf", "DARWIN_USER_DIR"], capture_output=True)
        .stdout.decode("utf-8")
        .strip()
    )

    db_folder = os.path.join(darwin_user_folder, "com.apple.notificationcenter", "db2")

    # we watch the write ahead log because that actually changes with the DB update
    # but we need to query the actual db file for the changes
    db_file = os.path.join(db_folder, "db")
    watch_file = os.path.join(db_folder, "db-wal")

    db = apsw.Connection(db_file)
    rec_ids = []

    # path to script the user wants to run on a notification being sent
    hook_script_path = os.path.join(os.getcwd(), "nchook_script")

    event_handler = DBEventHandler(db, rec_ids, hook_script_path)

    # we have to use a Kqueue observer not FSEvents because FSEvents
    # doesn't send updates for files the user doesn't own for privacy stuff,
    # even though this is the user's notification database
    observer = KqueueObserver()
    observer.schedule(event_handler, watch_file)
    # observer.daemon = True
    LOG.info("Starting notification observer...")
    observer.start()

    return observer


if __name__ == "__main__":
    observer_thread = start_notification_observer()
    print("not joined yet")
    observer_thread.join()
    print("just joined")
