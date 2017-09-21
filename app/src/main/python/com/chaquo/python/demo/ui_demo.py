from __future__ import absolute_import, division, print_function

from java import *

from android.app import AlertDialog
from android.content import Context, DialogInterface
from android.graphics.drawable import ColorDrawable
from android.os import Bundle
from android.support.v4.app import DialogFragment
from android.support.v7.app import AppCompatActivity
from android.support.v7.preference import Preference, PreferenceFragmentCompat
from android.view import Menu, MenuItem, View
from java.lang import String

from com.chaquo.python.demo import R
from demo_app import view_source


class UIDemoActivity(static_proxy(AppCompatActivity)):
    @Override(jvoid, [Bundle])
    def onCreate(self, state):
        AppCompatActivity.onCreate(self, state)
        if state is None:
            state = Bundle()
        self.setContentView(R.layout.activity_menu)
        self.findViewById(R.id.tvCaption).setText(R.string.demo_caption)

        self.title_drawable = ColorDrawable()
        self.getSupportActionBar().setBackgroundDrawable(self.title_drawable)
        self.title_drawable.setColor(
            state.getInt("title_color", self.getResources().getColor(R.color.blue)))

        self.wvSource = self.findViewById(R.id.wvSource)
        view_source(self, self.wvSource, "ui_demo.py")
        self.wvSource.setVisibility(state.getInt("source_visibility", View.GONE))

        self.getSupportFragmentManager().beginTransaction()\
            .replace(R.id.flMenu, MenuFragment()).commit()

    @Override(jvoid, [Bundle])
    def onSaveInstanceState(self, state):
        state.putInt("source_visibility", self.wvSource.getVisibility())
        state.putInt("title_color", self.title_drawable.getColor())

    @Override(jboolean, [Menu])
    def onCreateOptionsMenu(self, menu):
        self.getMenuInflater().inflate(R.menu.view_source, menu)
        return True

    @Override(jboolean, [MenuItem])
    def onOptionsItemSelected(self, item):
        id = item.getItemId()
        if id == R.id.menu_source:
            vis = self.wvSource.getVisibility()
            new_vis = View.VISIBLE if (vis == View.GONE) else View.GONE
            self.wvSource.setVisibility(new_vis)
            return True
        else:
            return False


class MenuFragment(static_proxy(PreferenceFragmentCompat)):
    @Override(jvoid, [Bundle, String])
    def onCreatePreferences(self, state, rootKey):
        self.addPreferencesFromResource(R.xml.activity_ui_demo)

        from android.media import AudioManager, SoundPool
        self.sound_pool = SoundPool(1, AudioManager.STREAM_MUSIC, 0)
        self.sound_id = self.sound_pool.load(self.getActivity(), R.raw.sound, 1)

    @Override(jboolean, [Preference])
    def onPreferenceTreeClick(self, pref):
        activity = self.getActivity()
        keys = ["demo_dialog", "demo_notify", "demo_toast", "demo_sound",
                "demo_vibrate"]
        dispatch = {activity.getString(getattr(R.string, key)): getattr(self, key)
                    for key in keys}
        method = dispatch.get(str(pref.getTitle()))
        if method:
            method(activity)
            return True
        else:
            return False

    def demo_dialog(self, activity):
        ColorDialog().show(self.getFragmentManager(), "color")

    def demo_notify(self, activity):
        from android.app import Notification
        builder = Notification.Builder(activity)
        builder.setSmallIcon(R.drawable.ic_launcher)
        builder.setContentTitle(
            activity.getString(R.string.demo_notify_title))
        builder.setContentText(
            activity.getString(R.string.demo_notify_text))
        activity.getSystemService(Context.NOTIFICATION_SERVICE)\
            .notify(0, builder.build())

    def demo_toast(self, activity):
        from android.widget import Toast
        Toast.makeText(activity, R.string.demo_toast_text,
                       Toast.LENGTH_SHORT).show()

    def demo_sound(self, activity):
        self.sound_pool.play(self.sound_id, 1, 1, 0, 0, 1)

    def demo_vibrate(self, activity):
        activity.getSystemService(Context.VIBRATOR_SERVICE)\
            .vibrate(200)


class ColorDialog(static_proxy(DialogFragment)):
    @Override(AlertDialog, [Bundle])
    def onCreateDialog(self, state):
        activity = self.getActivity()
        builder = AlertDialog.Builder(activity)
        builder.setTitle(R.string.demo_dialog_title)
        builder.setMessage(R.string.demo_dialog_text)

        class Listener(dynamic_proxy(DialogInterface.OnClickListener)):
            def __init__(self, color_res):
                super(Listener, self).__init__()
                self.color = activity.getResources().getColor(color_res)

            def onClick(self, dialog, which):
                activity.title_drawable.setColor(self.color)

        builder.setNegativeButton(R.string.red, Listener(R.color.red))
        builder.setNeutralButton(R.string.green, Listener(R.color.green))
        builder.setPositiveButton(R.string.blue, Listener(R.color.blue))
        return builder.create()
