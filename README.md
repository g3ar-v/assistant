# Assistant Project

## Overview

The Assistant project is a sophisticated voice assistant application that leverages real-time speech-to-text (STT) and text-to-speech (TTS) technologies. It is designed to provide seamless voice interaction capabilities, including wake word detection, voice activity detection, and real-time transcription while also leverage the scripting actions of mac operating systems.

## Features

- **Voice Activity Detection (VAD):** Automatically starts/stops recording based on the presence of speech.
- **Wake Word Detection:** Initiates recording when a specific wake word is detected.
- **Real-Time Transcription:** Provides immediate transcription of spoken words using the faster_whisper library.
- **Event Callbacks:** Customizable callbacks for various events such as recording start/stop, transcription updates, and wake word detection.
- **Integration with Spotify:** Controls Spotify playback, including play, pause, and volume adjustments.

## Components

### Core

- **OpenInterpreter** This is the brain of the system. Implemented [here](https://github.com/OpenInterpreter/open-interpreter.git).
- **Configuration Management:** Handles loading and storing configuration settings.
- **Logging:** Provides logging utilities for debugging and monitoring.

### Utilities

- **Console Utilities:** Functions for printing markdown and clearing the console.
- **Audio Utilities:** Functions for finding input devices and handling audio processing.
- **Process Utilities:** Functions for creating daemon processes.

### Audio Recorder

- **AudioToTextRecorder:** Main class for handling audio recording, VAD, wake word detection, and transcription.
- **Transcription:** Uses faster_whisper for converting audio to text.
- **Callbacks:** Supports various callbacks for handling different states and events during recording and transcription.

> [!important] The AudioToTextRecorder class and its functionalities in `audio_recorder.py` are implemented by [Kolja Beigel](https://github.com/KoljaB/RealtimeSTT.git). Just small modifications were made to support my requirements.

### Server

- **FastAPI Server:** Provides endpoints for receiving text and speech commands.
- **WebSocket Listener:** Handles real-time communication with the client.
- **Push-to-Talk Listener:** Listens for a specific key press to start/stop recording.

### Notification Interceptor

- **DBEventHandler:** Monitors changes in the notification database and triggers scripts based on specific events.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/g3ar-v/assistant.git
   ```
2. Install dependencies:
   ```sh
   poetry install
   ```

## Configuration

Configuration settings are managed through a combination of default and user-specific configuration files. The main configuration file is `device.conf`, which can be found in the configuration directory. The

## Usage

Run the server:

```sh
assistant
```

or
run the development loop:

```sh
assistant dev
```

## License

This project is licensed under the Apache License, Version 2.0. See the LICENSE file for more details.

## Contact

For any inquiries or support, please contact the me at [vfranktor@gmail.com](mailto:vfranktor@gmail.com)
