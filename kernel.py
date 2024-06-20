import asyncio
import subprocess
import platform
import os
import shutil
import time

from core import LOG


# dmesg process created at boot time
dmesg_proc = None


def get_kernel_messages():
    """
    Is this the way to do this?
    """
    current_platform = platform.system()
    command = ["log", "show", "--last", "1m", "--info"]

    if current_platform == "Darwin":
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        output, _ = process.communicate()
        return output.decode("utf-8")
    elif current_platform == "Linux":
        log_path = get_dmesg_log_path()
        with open(log_path, "r") as file:
            return file.read()
    else:
        LOG.info("Unsupported platform.")


def get_dmesg_log_path():
    """
    Check for the existence of a readable dmesg log file and return its path.
    Create an accessible path if not found.
    """
    if os.access("/var/log/dmesg", os.F_OK | os.R_OK):
        return "/var/log/dmesg"

    global dmesg_proc
    dmesg_log_path = "/tmp/dmesg"
    if dmesg_proc:
        return dmesg_log_path

    LOG.info("Created /tmp/dmesg.")
    subprocess.run(["touch", dmesg_log_path])
    dmesg_path = shutil.which("dmesg")
    if dmesg_path:
        LOG.info(f"Writing to {dmesg_log_path} from dmesg.")
        dmesg_proc = subprocess.Popen(
            [dmesg_path, "--follow"], text=True, stdout=subprocess.PIPE
        )
        subprocess.Popen(
            ["tee", dmesg_log_path],
            text=True,
            stdin=dmesg_proc.stdout,
            stdout=subprocess.DEVNULL,
        )

    return dmesg_log_path


def custom_filter(message):
    # Check for {TO_INTERPRETER{ message here }TO_INTERPRETER} pattern
    filter_wake_message = "powerd: [com.apple.powerd:sleepWake]"
    filtered_wake_message1 = "Wake from Deep Idle [CDNVA]"

    if "{TO_INTERPRETER{" in message and "}TO_INTERPRETER}" in message:
        start = message.find("{TO_INTERPRETER{") + len("{TO_INTERPRETER{")
        end = message.find("}TO_INTERPRETER}", start)
        return message[start:end]
    # Check for USB mention
    # elif 'USB' in message:
    #     return message
    # # Check for network related keywords
    # elif any(keyword in message for keyword in ['network', 'IP', 'internet', 'LAN', 'WAN', 'router', 'switch']) and "networkStatusForFlags" not in message:

    #     return message
    elif filter_wake_message in message and filtered_wake_message1 in message:
        return message
    else:
        return None


LOG.debug("resetting last_messages")
last_messages = ""


# HACK: need to check for all edge cases for the system wake logs
def check_filtered_kernel():
    messages = get_kernel_messages()
    if messages is None:
        return ""  # Handle unsupported platform or error in fetching kernel messages

    global last_messages
    messages = messages.replace(last_messages, "")
    messages = messages.split("\n")

    filtered_messages = []
    # regarding the LID message this clears out the multi system wake log for one command execution
    for message in messages:
        if custom_filter(message):
            LOG.debug(f"Kernel message: {message}")
            # if "<SMC.OutboxNotEmpty smc.70070000 lid>" in message and any(
            #     "systemWokenByWiFi: System wake reason: <SMC.OutboxNotEmpty smc.70070000 lid>"
            #     in filtered_message
            #     for filtered_message in filtered_messages
            # ):
            #     last_messages = filtered_messages[-1] if filtered_messages else ""
            #     LOG.info("Duplicate message found. Skipping.")
            #     continue
            filtered_messages.append(custom_filter(message))
            LOG.debug(f"Filtered kernel message: {filtered_messages}")
    last_messages = "\n".join(filtered_messages)
    LOG.debug(f"last_messages: {last_messages}")
    return "\n".join(filtered_messages)


# HACK: sleeping when a log is gotten prevents other messages from being read and acted on
async def put_kernel_messages_into_queue(queue):
    # clear unique message everytime last message is equal to "",
    LOG.info("Starting kernel listener...")
    # seen = set()

    while True:
        text = check_filtered_kernel()

        if text:
            LOG.debug(f"putting kernel messages into queue: {text}")
            if isinstance(queue, asyncio.Queue):
                await queue.put({"role": "computer", "type": "console", "start": True})
                await queue.put(
                    {
                        "role": "computer",
                        "type": "console",
                        "format": "output",
                        "content": text,
                    }
                )
                await queue.put({"role": "computer", "type": "console", "end": True})
            else:
                queue.put({"role": "computer", "type": "console", "start": True})
                queue.put(
                    {
                        "role": "computer",
                        "type": "console",
                        "format": "output",
                        "content": text,
                    }
                )
                queue.put({"role": "computer", "type": "console", "end": True})
            await asyncio.sleep(70)
            continue

        await asyncio.sleep(6)
