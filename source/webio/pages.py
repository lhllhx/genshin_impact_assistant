import asyncio
import json
import os
import threading

from pywebio import *

from source import listening, util, webio
from source.webio.page_manager import Page


def to_main_page():
    webio.manager.load_page('Main')


def to_setting_page():
    webio.manager.load_page('Setting')


class MainPage(Page):
    def __init__(self):
        super().__init__()

    def _on_load(self):
        self._load()
        t = threading.Thread(target=self._load_async, daemon=False)
        session.register_thread(t)

        t.start()

    def _load_async(self):
        asyncio.run(self._main_pin_change_thread())

    async def _main_pin_change_thread(self):
        while self.loaded:
            if pin.pin['FlowMode'] != listening.current_flow:
                listening.current_flow = pin.pin['FlowMode']
            await asyncio.sleep(0.1)

    def _load(self):
        # 主scope
        output.put_scope('Main')
        # 标题
        output.put_markdown('# Main', scope='Main')
        output.put_row([
            output.put_button(label='Main', onclick=to_main_page),
            output.put_button(label='setting', onclick=to_setting_page)
        ], scope='Main')
        output.put_row([  # 横列
            output.put_column([  # 左竖列
                output.put_markdown('## Options'),  # 左竖列标题

                output.put_row([  # FlowMode
                    output.put_text('FlowMode'),
                    pin.put_select('FlowMode', [
                        {'label': 'Idle', 'value': listening.FLOW_IDLE},
                        {'label': 'AutoCombat', 'value': listening.FLOW_COMBAT},
                        {'label': 'AutoDomain', 'value': listening.FLOW_DOMAIN}
                    ])]),

                output.put_row([output.put_text('PickUp'), output.put_scope('Button_PickUp')])

            ]), None,
            output.put_scope('Log')

        ], scope='Main')
        # Button
        output.put_button(label=str(listening.FEAT_PICKUP), onclick=self.on_click_pickup, scope='Button_PickUp')
        # Log
        output.put_markdown('## Log', scope='Log')
        output.put_scrollable(output.put_scope('LogArea'), height=300, keep_bottom=True, scope='Log')
        '''self.main_pin_change_thread = threading.Thread(target=self._main_pin_change_thread, daemon=False)
        self.main_pin_change_thread.start()'''

    def on_click_pickup(self):

        output.clear('Button_PickUp')
        listening.FEAT_PICKUP = not listening.FEAT_PICKUP
        print(listening.FEAT_PICKUP)
        output.put_button(label=str(listening.FEAT_PICKUP), onclick=self.on_click_pickup, scope='Button_PickUp')

    def logout(self, text: str, color='black'):
        if self.loaded:
            output.put_text(text, scope='LogArea').style(f'color: {color}')

    def _on_unload(self):
        output.remove('Main')


class SettingPage(Page):
    def __init__(self):
        super().__init__()
        self.last_file = None
        self.file_name = ''

        self.config_files = []
        self.config_files_name = []
        for root, dirs, files in os.walk('config'):
            for f in files:
                self.config_files.append({"label": f, "value": os.path.join(root, f)})
        self.can_remove_last_scope = False

    def _load(self):
        output.put_scope('Setting')
        output.put_markdown('# Setting', scope='Setting')
        output.put_row([
            output.put_button(label='Main', onclick=to_main_page),
            output.put_button(label='Setting', onclick=to_setting_page)
        ], scope='Setting')
        output.put_markdown('## config:', scope='Setting')
        pin.put_select('file', self.config_files, scope='Setting')

    def _on_load(self):
        self._load()
        t = threading.Thread(target=self._load_async, daemon=False)
        session.register_thread(t)
        # session.get_current_session()

        t.start()

    def _load_async(self):
        asyncio.run(self._main_pin_change_thread())

    async def _main_pin_change_thread(self):
        while self.loaded:
            if pin.pin['file'] != self.last_file:
                self.last_file = pin.pin['file']
                if self.can_remove_last_scope:
                    output.remove('now')
                else:
                    self.can_remove_last_scope = True
                output.put_scope('now', scope='Setting')

                self.put_setting(pin.pin['file'])
            await asyncio.sleep(0.1)

    def put_setting(self, name=''):
        self.file_name = name
        output.put_markdown('## {}'.format(name), scope='now')
        j = json.load(open(name, 'r', encoding='utf8'))
        self.put_json(j, 'now', level=3)
        output.put_button('save', scope='now', onclick=self.save)

    def save(self):

        j = json.load(open(self.file_name, 'r', encoding='utf8'))

        json.dump(self.get_json(j), open(self.file_name, 'w', encoding='utf8'))
        # output.put_text('saved!', scope='now')
        output.toast('saved!')

    def get_json(self, j: dict, add_name=''):
        rt_json = {}
        for k in j:

            v = j[k]
            if type(v) == dict:
                rt_json[k] = self.get_json(v, add_name='{}-{}'.format(add_name, k))

            elif type(v) == list:
                rt_json[k] = util.list_text2list(pin.pin['{}-{}'.format(add_name, k)])
            else:
                rt_json[k] = pin.pin['{}-{}'.format(add_name, k)]

        return rt_json

    def _on_unload(self):

        # is_json_equal(self.get_json())
        output.remove('Setting')

    def put_json(self, j: dict, scope_name, add_name='', level=1):
        for k in j:
            v = j[k]
            if type(v) == str or v is None:
                pin.put_input('{}-{}'.format(add_name, k), label=k, value=v, scope=scope_name)
            elif type(v) == bool:
                pin.put_select('{}-{}'.format(add_name, k),
                               [{"label": 'True', "value": True}, {"label": 'False', "value": False}], value=v, label=k,
                               scope=scope_name)
            elif type(v) == dict:
                output.put_scope('{}-{}'.format(add_name, k), scope=scope_name)
                output.put_markdown('#' * level + ' ' + k, scope='{}-{}'.format(add_name, k))
                self.put_json(v, '{}-{}'.format(add_name, k), add_name='{}-{}'.format(add_name, k), level=level + 1)
            elif type(v) == list:
                pin.put_textarea('{}-{}'.format(add_name, k), label=k, value=util.list2format_list_text(v),
                                 scope=scope_name)
            elif type(v) == int:
                pin.put_input('{}-{}'.format(add_name, k), label=k, value=v, scope=scope_name, type='number')
            elif type(v) == float:
                pin.put_input('{}-{}'.format(add_name, k), label=k, value=v, scope=scope_name, type='float')