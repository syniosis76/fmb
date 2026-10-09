from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.graphics.fbo import Fbo
from kivy.graphics import opengl as gl
from kivy.logger import Logger
from kivy.metrics import Metrics
from kivy.properties import (BooleanProperty, NumericProperty, OptionProperty,
                             StringProperty)
from kivy.uix.widget import Widget

from utilities import libmpv_loader

libmpv_loader.load_libmpv()

import mpv  # pylint: disable=wrong-import-position,import-error


class MpvVideo(Widget):
    """A Kivy widget that plays video through libmpv's OpenGL render API.

    It mirrors the small part of the Kivy ``Video`` widget interface that the
    rest of the application relies on (``source``, ``state``, ``position``,
    ``duration``, ``loaded`` and ``seek``).
    """

    source = StringProperty(None, allownone=True)
    state = OptionProperty('stop', options=['play', 'pause', 'stop'])
    position = NumericProperty(0)
    duration = NumericProperty(0)
    loaded = BooleanProperty(False)
    volume = NumericProperty(1.0)
    speed = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._initialised = False
        self._closed = False
        self._render_ctx = None
        self._fbo = None
        self._proc_address_fn = None
        self._redraw_scheduled = False
        self._suppress_state_command = False
        self._position_pending = False
        self._pending_position = 0.0
        self._ended = False

        with self.canvas:
            Color(1, 1, 1, 1)
            self._rectangle = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rectangle)
        self.bind(size=self._update_rectangle)

        self._create_player()

        self.bind(source=self._on_source)
        self.bind(state=self._on_state)
        self.bind(volume=self._on_volume)
        self.bind(speed=self._on_speed)

        self._initialised = True

    # ------------------------------------------------------------------ setup

    def _create_player(self):
        self._mpv = mpv.MPV(
            vo='libmpv',
            terminal=False,
            osc=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
            keep_open='yes',
            hwdec='auto-safe',
        )

        self._mpv.observe_property('time-pos', self._on_mpv_time_pos)
        self._mpv.observe_property('duration', self._on_mpv_duration)
        self._mpv.observe_property('pause', self._on_mpv_pause)
        self._mpv.observe_property('eof-reached', self._on_mpv_eof)

        self._mpv.event_callback('file-loaded')(self._on_file_loaded)

        def get_proc_address(_ctx, name):
            return libmpv_loader.gl_get_proc_address(name)

        self._proc_address_fn = mpv.MpvGlGetProcAddressFn(get_proc_address)

        self._render_ctx = mpv.MpvRenderContext(
            self._mpv,
            'opengl',
            opengl_init_params={'get_proc_address': self._proc_address_fn},
        )
        self._render_ctx.update_cb = self._on_mpv_update

    # --------------------------------------------------------------- playback

    def load(self, path):
        if self._mpv is None:
            return

        Logger.info(f'MpvVideo: load {path}')

        self.loaded = False
        self._ended = False
        self.position = 0
        self.duration = 0

        try:
            self._mpv.play(path)
        except Exception:  # pylint: disable=broad-exception-caught
            Logger.exception('MpvVideo: error loading file')

    def unload(self):
        if self._mpv is not None:
            try:
                self._mpv.command('stop')
            except Exception:  # pylint: disable=broad-exception-caught
                pass
        self.loaded = False

    def seek(self, fraction, precise=False):
        if self._mpv is None:
            return

        precision = 'exact' if precise else 'keyframes'
        try:
            self._mpv.command('seek', fraction * 100.0, 'absolute-percent', precision)
        except Exception:  # pylint: disable=broad-exception-caught
            Logger.exception('MpvVideo: seek failed')

    def frame_step(self):
        if self._mpv is not None:
            try:
                self._mpv.command('frame-step')
            except Exception:  # pylint: disable=broad-exception-caught
                Logger.exception('MpvVideo: frame-step failed')

    # ------------------------------------------------------------ mpv events

    def _on_file_loaded(self, _event):
        Clock.schedule_once(self._apply_loaded, 0)

    def _apply_loaded(self, _dt):
        self.loaded = True

    def _on_mpv_time_pos(self, _name, value):
        if value is None:
            return
        self._pending_position = value
        if not self._position_pending:
            self._position_pending = True
            Clock.schedule_once(self._apply_position, 0)

    def _apply_position(self, _dt):
        self._position_pending = False
        self.position = self._pending_position

    def _on_mpv_duration(self, _name, value):
        if value is None:
            return
        Clock.schedule_once(lambda dt: self._apply_duration(value), 0)

    def _apply_duration(self, value):
        self.duration = value

    def _on_mpv_pause(self, _name, value):
        if value is None:
            return
        Clock.schedule_once(lambda dt: self._apply_pause(value), 0)

    def _apply_pause(self, value):
        if self._ended:
            return
        if value:
            self._set_state_from_mpv('pause')
        else:
            self._set_state_from_mpv('play')

    def _on_mpv_eof(self, _name, value):
        if value:
            Clock.schedule_once(lambda dt: self._on_reached_end(), 0)

    def _on_reached_end(self):
        self._ended = True
        self._set_state_from_mpv('stop')

    def _set_state_from_mpv(self, value):
        self._suppress_state_command = True
        try:
            self.state = value
        finally:
            self._suppress_state_command = False

    # ----------------------------------------------------------- properties

    def _on_source(self, _instance, value):
        if value:
            self.load(value)

    def _on_state(self, _instance, value):
        if not self._initialised or self._mpv is None or self._suppress_state_command:
            return

        try:
            if value == 'play':
                if self._ended:
                    self._ended = False
                    self._mpv.command('seek', 0, 'absolute')
                self._mpv.pause = False
            elif value == 'pause':
                self._mpv.pause = True
            elif value == 'stop':
                self._mpv.command('stop')
        except Exception:  # pylint: disable=broad-exception-caught
            Logger.exception('MpvVideo: state change failed')

    def _on_volume(self, _instance, value):
        if self._initialised and self._mpv is not None:
            try:
                self._mpv.volume = max(0.0, min(100.0, value * 100.0))
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    def _on_speed(self, _instance, value):
        if self._initialised and self._mpv is not None:
            try:
                self._mpv.speed = value
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # -------------------------------------------------------------- rendering

    def _on_mpv_update(self):
        if self._closed or self._redraw_scheduled:
            return
        self._redraw_scheduled = True
        Clock.schedule_once(self._redraw, 0)

    def _redraw(self, _dt):
        self._redraw_scheduled = False

        if self._closed or self._render_ctx is None:
            return

        if self.width < 2 or self.height < 2:
            return

        if not self._ensure_fbo():
            return

        if not self._render_ctx.update():
            return

        self._render_frame()

    def _ensure_fbo(self):
        width = int(round(self.width * Metrics.density))
        height = int(round(self.height * Metrics.density))

        if width < 2 or height < 2:
            return False

        if self._fbo is None:
            self._fbo = Fbo(size=(width, height), clear_color=(0, 0, 0, 1))
            self._rectangle.texture = self._fbo.texture
        elif self._fbo.size != (width, height):
            self._fbo.size = (width, height)
            self._rectangle.texture = self._fbo.texture

        return True

    def _render_frame(self):
        fbo = self._fbo
        width, height = fbo.size

        # libmpv's hardware-decoded render path corrupts frames when GL
        # blending is enabled while it renders, so disable it for the render.
        gl.glDisable(gl.GL_BLEND)

        fbo.bind()
        try:
            fbo_id = gl.glGetIntegerv(gl.GL_FRAMEBUFFER_BINDING)[0]
            self._render_ctx.render(
                flip_y=True,
                opengl_fbo={'w': int(width), 'h': int(height), 'fbo': int(fbo_id)},
            )
        finally:
            fbo.release()

        # libmpv's render API disables blending and does not restore it. Kivy
        # otherwise re-applies its own program/textures/buffers while drawing,
        # so only the blend state has to be put back. This must not query the
        # GL state: those calls stall libmpv's hardware decoding pipeline.
        gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA,
                               gl.GL_ONE, gl.GL_ONE)
        gl.glEnable(gl.GL_BLEND)

        self.canvas.ask_update()

    def _update_rectangle(self, _instance, _value):
        self._rectangle.pos = self.pos
        self._rectangle.size = self.size

    # ---------------------------------------------------------------- cleanup

    def on_parent(self, widget, parent):
        if getattr(self, '_initialised', False) and parent is None:
            self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True

        if self._render_ctx is not None:
            try:
                self._render_ctx.update_cb = None
                self._render_ctx.free()
            except Exception:  # pylint: disable=broad-exception-caught
                Logger.exception('MpvVideo: error freeing render context')
            self._render_ctx = None

        if self._mpv is not None:
            try:
                self._mpv.terminate()
            except Exception:  # pylint: disable=broad-exception-caught
                Logger.exception('MpvVideo: error terminating player')
            self._mpv = None
