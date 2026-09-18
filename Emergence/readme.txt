Emergence
by Daniel Gergely 
v0.3.0
https://www.kvraudio.com/developer/daniel-gergely


Emergence occurs when an entity is observed to have properties its parts do not
have on their own, properties or behaviours which emerge only when the parts
interact in a wider whole.

This plugin is a real-time granulator. It continuously records the input signal
into a buffer. The content of the buffer is played back as many short pieces of
sound called grains. Up to 600 grains can be generated in 4 streams, each having
it's own set of parameters that control grain generation.

A single grain is not that interesting. The most exciting things happen when
hundreds of overlapping grains play together, creating anything from complex
delay patterns to strange noises to beautiful layered soundscapes.


# Features:

- Up to 600 grains (depending on your CPU).
- Four grain generation streams with independent parameters.
- Modulation system with LFOs, Macros and parameter randomization.
- High quality grain pitch transposition (+/- 24 semitones).
- Freeze buffer contents.
- Built-in help (hover over controls and see text at the bottom).
- Resizable UI.
- VST3 and AU format available.


# System Requirements

- Windows 10 / macOS 10.9 or newer
- Host with VST3 support (64-bit)
- OpenGL 3 or higher


# Installation

## Windows

Copy the Emergence directory to your VST3 directory.
The system default on windows is: `c:\Program Files\Common Files\VST3\`.


## Mac

### VST3
- Copy the Emergence.vst3 file to /Library/Audio/Plug-Ins/VST3/.
- Open Terminal and run the following command:
  sudo xattr -rd com.apple.quarantine /Library/Audio/Plug-Ins/VST3/Emergence.vst3
  (This step is necessary because the plugin is not signed and notarized. After
  doing this the system will allow your DAW to load the plugin)
- Start your DAW. You should be able to use the plugin now.

### AU
- Copy the Emergence.component file to /Library/Audio/Plug-Ins/Components/.
- Open Terminal and run the following command:
  sudo xattr -rd com.apple.quarantine /Library/Audio/Plug-Ins/Components/Emergence.component
  (This step is necessary because the plugin is not signed and notarized. After
  doing this the system will allow your DAW to load the plugin)
- Start your DAW. You should be able to use the plugin now.


# Contact

Please send your comments, suggestions, and questions to gergely.daniel1@gmail.com

If you like the plugin you can support my work here:
Patreon: https://www.patreon.com/daniel_gergely
buymeacoffee: https://buymeacoffee.com/danielgergely                

When reporting a problem please include the following information:
- Expected behaviour
- Current behaviour
- Steps to reproduce the problem
- Name and version of your DAW
- Buffer size and track configuration
- Screenshot or video (if relevant)


# Disclaimer

This software is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.


# Changelog

## v0.3.0
- Audio
  - True stereo processing: both input channels are kept for dry and buffer signals
  - Add Balance knob for each stream to control which input channel is played by the grains
- UI
  - Improve waveform drawing
  - Add buttons to quantize grain pitch
- Modulation
  - Add frequency and probability controls for random modulators
  - Add an additional random modulator

## v0.2.2
- Modulation: Generate a different random value for each randomized parameter
- UI: Editor size preference is shared among all instances of the plugin
- UI: Add button to paste stream parameters with modulation
- UI: Fix parameters not being updated when dragging knobs with the right mouse
  button
- UI: Only show active modulations when a modulator button is hovered
- VST3: Fix potential crash when right-clicking knobs

## v0.2.1
- Stability: Fix potential crash when an instance of the plugin is created
- UI: Support displays smaller than 1080 pixels in height
- UI: Add buttons to scale the GUI
- UI: Improve knob layout
- Streams: Add buttons to copy and paste stream parameters

## v0.2.0
- macOS: add AU support
- Modulation: add LFOs and Macro knobs
- Modulation: improve parameter randomization
- UI: fade out waveform/grain visualization while not processing audio
- VST3: support host-provided context menus for parameter controls

## v0.1.1
- macOS: add VST3 support
