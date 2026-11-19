#!/usr/bin/python3
"""Small playback window for the MP3 saved by speak.sh.

Usage: player.py FILE.mp3

FILE's directory holds the saved recordings; Up/Down arrows move to the
older/newer one, like shell history.

The window stays open after playback ends. When playback finishes it releases
the speak.sh queue lock (fd 9) and creates $SPEAK_DONE, if set.
Play/pause, replay and a seek slider. Falls back to headless playback when
there is no display.
"""
import os
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

Gst.init(None)

path = os.path.abspath(sys.argv[1])
records = sorted(f for f in os.listdir(os.path.dirname(path)) if f.endswith(".mp3"))
current = records.index(os.path.basename(path)) if os.path.basename(path) in records else None
if current is None:
    records.append(os.path.basename(path))
    current = len(records) - 1
folder = os.path.dirname(path)


def finished():
    """Tell speak.sh that playback is over (queued speech may start)."""
    try:
        os.close(9)
    except OSError:
        pass
    done = os.environ.get("SPEAK_DONE")
    if done:
        open(done, "w").close()


player = Gst.ElementFactory.make("playbin", "player")
player.set_property("uri", Gst.filename_to_uri(path))
player.set_property("video-sink", Gst.ElementFactory.make("fakesink", None))

try:
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, Gtk, Pango
    have_gui = Gtk.init_check()[0]
except (ValueError, ImportError):
    have_gui = False

if not have_gui:
    loop = GLib.MainLoop()
    bus = player.get_bus()
    bus.add_signal_watch()
    bus.connect("message::eos", lambda *_: (finished(), loop.quit()))
    bus.connect("message::error", lambda *_: loop.quit())
    player.set_state(Gst.State.PLAYING)
    loop.run()
    sys.exit(0)

NS = Gst.SECOND
POS_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "speak-aloud.pos")


def fmt(ns):
    s = max(0, int(ns // NS))
    return f"{s // 60}:{s % 60:02d}"


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title="Speak aloud")
        self.set_default_size(380, 1)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_border_width(10)
        self.ended = False
        self.dragging = False
        self.duration = 0

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(box)

        self.caption = Gtk.Label(xalign=0)
        self.caption.set_ellipsize(Pango.EllipsizeMode.END)
        self.caption.set_max_width_chars(48)
        box.pack_start(self.caption, False, False, 0)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.scale.set_draw_value(False)
        self.scale.connect("button-press-event", self.on_press)
        self.scale.connect("button-release-event", self.on_release)
        self.scale.connect("value-changed", self.on_changed)
        box.pack_start(self.scale, False, False, 0)

        row = Gtk.Box(spacing=6)
        box.pack_start(row, False, False, 0)
        self.time = Gtk.Label(label="0:00 / 0:00")
        row.pack_start(self.time, False, False, 0)

        replay = Gtk.Button.new_from_icon_name("media-skip-backward", Gtk.IconSize.BUTTON)
        replay.set_tooltip_text("Replay from the start")
        replay.connect("clicked", lambda *_: self.replay())
        row.pack_end(replay, False, False, 0)
        self.button = Gtk.Button.new_from_icon_name("media-playback-pause", Gtk.IconSize.BUTTON)
        self.button.set_tooltip_text("Pause / play (space)")
        self.button.connect("clicked", lambda *_: self.toggle())
        row.pack_end(self.button, False, False, 0)

        for w in (self.scale, self.button, replay):
            w.set_can_focus(False)  # keep arrow keys for record navigation
        self.show_caption()
        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key)
        bus = player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_eos)
        GLib.timeout_add(200, self.tick)
        self.show_all()
        self.place()
        self.connect("configure-event", self.on_configure)
        player.set_state(Gst.State.PLAYING)

    def place(self):
        """Reuse the position of the window this one replaces; a fresh window
        (none was open) goes to the bottom-right corner of the screen."""
        try:
            x, y = map(int, open(POS_FILE).read().split())
            self.move(x, y)
        except (OSError, ValueError):
            GLib.timeout_add(200, self.place_corner)

    def place_corner(self):
        display = Gdk.Display.get_default()
        mon = display.get_primary_monitor() or display.get_monitor(0)
        area = mon.get_workarea()
        # Real size including the title bar and any shadow.
        fe = self.get_window().get_frame_extents()
        x = area.x + area.width - fe.width - 16
        y = area.y + area.height - fe.height - 16
        ox, oy = self.get_position()
        self.move(x + ox - fe.x, y + oy - fe.y)
        return False

    def on_configure(self, *_):
        x, y = self.get_position()
        try:
            with open(POS_FILE, "w") as f:
                f.write(f"{x} {y}")
        except OSError:
            pass

    def playing(self):
        return player.get_state(0)[1] == Gst.State.PLAYING

    def set_icon(self, playing):
        self.button.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-pause" if playing else "media-playback-start", Gtk.IconSize.BUTTON))

    def toggle(self):
        if self.ended:
            return self.replay()
        playing = self.playing()
        player.set_state(Gst.State.PAUSED if playing else Gst.State.PLAYING)
        self.set_icon(not playing)

    def replay(self):
        self.ended = False
        player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, 0)
        player.set_state(Gst.State.PLAYING)
        self.set_icon(True)

    def on_eos(self, *_):
        finished()
        self.ended = True
        self.set_icon(False)
        player.set_state(Gst.State.PAUSED)

    def show_caption(self):
        name = records[current]
        try:
            text = open(os.path.join(folder, name[:-4] + ".txt")).read().strip()
        except OSError:
            text = ""
        self.caption.set_text(f"{current + 1}/{len(records)}  {text}")
        self.caption.set_tooltip_text("Up: older recording, Down: newer")

    def go(self, step):
        """Switch to an older (-1) or newer (+1) recording, like shell history."""
        global current
        new = current + step
        while 0 <= new < len(records) and not os.path.exists(os.path.join(folder, records[new])):
            del records[new]  # deleted by a newer speech
            if step < 0:
                new -= 1
        if not 0 <= new < len(records):
            return
        current = new
        self.ended = False
        self.duration = 0
        player.set_state(Gst.State.NULL)
        player.set_property("uri", Gst.filename_to_uri(os.path.join(folder, records[current])))
        player.set_state(Gst.State.PLAYING)
        self.set_icon(True)
        self.show_caption()

    def skip(self, seconds):
        """Jump forward/back by some seconds, staying inside the recording."""
        ok, pos = player.query_position(Gst.Format.TIME)
        if not ok:
            return
        if self.ended:
            pos = self.duration
        new = max(0, pos + seconds * NS)
        if self.duration:
            new = min(new, self.duration - NS // 10)
        player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, new)
        if self.ended and new < self.duration:
            self.ended = False
            player.set_state(Gst.State.PLAYING)
            self.set_icon(True)

    def on_key(self, _w, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and event.keyval in (Gdk.KEY_w, Gdk.KEY_W):
            self.destroy()
        elif event.keyval == 32:  # space
            self.toggle()
        elif event.keyval == Gdk.KEY_Up:
            self.go(-1)
        elif event.keyval == Gdk.KEY_Down:
            self.go(1)
        elif event.keyval == Gdk.KEY_Left:
            self.skip(-5)
        elif event.keyval == Gdk.KEY_Right:
            self.skip(5)
        else:
            return False
        return True

    def on_press(self, *_):
        self.dragging = True

    def on_release(self, *_):
        self.dragging = False
        if self.duration:
            self.ended = False
            pos = int(self.scale.get_value() * self.duration)
            player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, pos)

    def on_changed(self, scale):
        if self.dragging and self.duration:
            self.time.set_text(f"{fmt(scale.get_value() * self.duration)} / {fmt(self.duration)}")

    def tick(self):
        ok, dur = player.query_duration(Gst.Format.TIME)
        if ok and dur > 0:
            self.duration = dur
        if self.duration and not self.dragging:
            ok, pos = player.query_position(Gst.Format.TIME)
            if self.ended:
                pos = self.duration
            if ok:
                self.scale.set_value(min(1.0, pos / self.duration))
                self.time.set_text(f"{fmt(pos)} / {fmt(self.duration)}")
        return True

    def on_destroy(self, *_):
        finished()
        try:
            os.remove(POS_FILE)  # closed: the next window starts bottom-right
        except OSError:
            pass
        player.set_state(Gst.State.NULL)
        Gtk.main_quit()


Window()
Gtk.main()
