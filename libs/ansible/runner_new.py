# -*- coding: utf-8 -*-
import json
import os
import re
from tempfile import TemporaryDirectory

import ansible_runner

from libs.ansible.callback_new import ResultsCollectorWebSocket
from utils.logger import logger


class ANSRunner:
    def __init__(self,
                 hosts=None,
                 module_name=None,
                 module_args=None,
                 forks=None,
                 timeout=None,
                 pattern="all",
                 remote_user=None,
                 module_path=None,
                 connection_type="smart",
                 become=True,
                 become_method='sudo',
                 become_user='root',
                 check=False,
                 passwords=None,
                 extra_vars=None,
                 private_key_file=None,
                 listtags=False,
                 listtasks=False,
                 listhosts=False,
                 ssh_common_args=None,
                 ssh_extra_args=None,
                 sftp_extra_args=None,
                 scp_extra_args=None,
                 verbosity=None,
                 syntax=False,
                 websocket=None,
                 background=None):
        self.hosts = hosts
        self.extra_vars = extra_vars
        self.results_raw = {}
        self.pattern = pattern
        self.module_name = module_name
        self.module_args = module_args
        self.gather_facts = 'no'
        self.websocket = websocket
        self.background = background
        self.passwords = passwords or {}
        self.runner = None
        self.callback = ResultsCollectorWebSocket(websocket)

    def run_model(self, host_list, module_name, module_args):

        inventory = self._format_host()
        try:
            with TemporaryDirectory() as d:
                self.runner = ansible_runner.run(
                    private_data_dir=d,
                    host_pattern=self.pattern,
                    inventory=inventory,
                    module=module_name,
                    module_args=module_args,
                    extravars=self.extra_vars,
                    event_handler=self.event_handler(),
                    cancel_callback=self.cancel_callback(),
                    finished_callback=self.finished_callback(),
                    status_handler=self.status_handler()
                    )

                pass
        except Exception as err:
            logger.error(msg=f"run model failed: {str(err)}")

    def run_playbook(self, host_list, playbook_path, extra_vars):
        inventory = self._format_host()
        try:
            dir_path = os.path.dirname(playbook_path)
            file_name = os.path.basename(playbook_path)
            self.runner = ansible_runner.run(private_data_dir=dir_path,
                                             playbook=file_name,
                                             inventory=inventory,
                                             extravars=extra_vars,
                                             event_handler=self.event_handler(),
                                             cancel_callback=self.cancel_callback(),
                                             finished_callback=self.finished_callback(),
                                             status_handler=self.status_handler()
                                             )
            logger.info(f'执行结果: {self.runner.status}')
        except Exception as err:
            logger.error(msg="run playbook failed: {err}".format(err=str(err)))
            if self.websocket:
                self.websocket.send(str(err))
            return False

    def event_handler(self):
        def _event_handler(event):
            self.callback.format_event(event)

        return _event_handler

    def cancel_callback(self):
        def _cancel_callback():
            pass

        return _cancel_callback

    def finished_callback(self):
        def _finished_callback(result):
            logger.info(result)
            logger.info("finished.")

        return _finished_callback

    def status_handler(self):
        def _status_handler(status, runner_config):
            pass

        return _status_handler

    def _format_host(self):
        pattern = 'module'
        inventory = f'[{pattern}]\n'
        for host in self.hosts:
            inventory += f'{host["ip"]} ansible_ssh_user={host["username"]} ansible_ssh_pass={host["password"]}\n'
        return inventory
    def get_model_result(self):
        pass

    def handle_cmdb_data(self, data):
        """处理setup返回结果方法"""
        data_list = []
        for k, v in json.loads(data).items():
            if k == "success":
                for x, y in v.items():
                    cmdb_data = {}
                    data = y.get('ansible_facts')
                    disk_size = 0
                    cpu = data['ansible_processor'][-1]
                    for k, v in data['ansible_devices'].items():
                        if k[0:2] in ['sd', 'hd', 'ss', 'vd']:
                            disk = int((int(v.get('sectors')) * int(v.get('sectorsize'))) / 1024 / 1024 / 1024)
                            disk_size = disk_size + disk
                    cmdb_data['serial'] = data['ansible_product_serial'].split()[0]
                    cmdb_data['ip'] = x
                    cmdb_data['cpu'] = cpu.replace('@', '')
                    cmdb_data['ram_total'] = int(data['ansible_memtotal_mb']) / 1000
                    cmdb_data['disk_total'] = int(disk_size)
                    cmdb_data['system'] = data['ansible_distribution'] + ' ' + data[
                        'ansible_distribution_version'] + ' ' + data['ansible_userspace_bits']
                    cmdb_data['model'] = data['ansible_product_name'].split(':')[0]
                    cmdb_data['cpu_number'] = data['ansible_processor_count']
                    cmdb_data['vcpu_number'] = data['ansible_processor_vcpus']
                    cmdb_data['cpu_core'] = data['ansible_processor_cores']
                    cmdb_data['hostname'] = data['ansible_hostname']
                    cmdb_data['kernel'] = str(data['ansible_kernel'])
                    cmdb_data['manufacturer'] = data['ansible_system_vendor']
                    if data['ansible_selinux']:
                        cmdb_data['selinux'] = data['ansible_selinux'].get('status')
                    else:
                        cmdb_data['selinux'] = 'disabled'
                    cmdb_data['swap'] = int(data['ansible_swaptotal_mb']) / 1000
                    # 获取网卡资源
                    nks = []
                    for nk in data.keys():
                        if re.match(r"^ansible_(eth|bind|eno|ens|em)\d+?", nk):
                            device = data.get(nk).get('device')
                            try:
                                address = data.get(nk).get('ipv4').get('address')
                            except:
                                address = 'unkown'
                            macaddress = data.get(nk).get('macaddress')
                            module = data.get(nk).get('module')
                            mtu = data.get(nk).get('mtu')
                            if data.get(nk).get('active'):
                                active = 1
                            else:
                                active = 0
                            nks.append(
                                {"device": device, "address": address, "macaddress": macaddress, "module": module,
                                 "mtu": mtu, "active": active})
                    cmdb_data['status'] = 0
                    cmdb_data['nks'] = nks
                    data_list.append(cmdb_data)
            elif k == "unreachable":
                for x, y in v.items():
                    cmdb_data = {}
                    cmdb_data['status'] = 1
                    cmdb_data['ip'] = x
                    data_list.append(cmdb_data)
        return data_list

    def handle_cmdb_crawHw_data(self, data):
        data_list = []
        for k, v in json.loads(data).items():
            if k == "success":
                for x, y in v.items():
                    cmdb_data = {}
                    cmdb_data['ip'] = x
                    data = y.get('ansible_facts')
                    cmdb_data['mem_info'] = data.get('ansible_mem_detailed_info')
                    cmdb_data['disk_info'] = data.get('ansible_disk_detailed_info')
                    data_list.append(cmdb_data)
        return data_list


if __name__ == '__main__':
    ans_runner = ANSRunner()
    ans_runner.run_model(['127.0.0.1', '172.17.32.6'], "shell", 'whoami')
