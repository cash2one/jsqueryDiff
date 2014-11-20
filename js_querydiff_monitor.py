# -*- coding: UTF-8 -*-
#######################################################################
#author - zhongzhiwei@baidu.com
#######################################################################

import MySQLdb
import sys
import os
import re
import rpyc
import random
import time
import json
import subprocess
import string

from UbfPlatform.settings import DATABASES
import html


class DatabaseMonitor(object):
    """
    DatabaseMonitor    This is used to monitor the database, and do the js querydiff by using the remote js tools.
    """
    def __init__(self):
        try:
            self.db_conn = MySQLdb.connect(host='localhost', user=DATABASES['default']['USER'], 
                    passwd=DATABASES['default']['PASSWORD'], db=DATABASES['default']['NAME'])
        except Exception, e:
            print 'database is not connected.'
            sys.exit(-1)
        self.cursor = self.db_conn.cursor()

    def parse_result(self, result_file):
        """
        parse_result    Parse the diff log file and generate a html report. //目前只提取了新旧投放脚本都有的参数，
                        忽略了一些新旧脚本中不存在的参数
        Args:
            result_file:The diff log file.
        Returns:
            return the report name
        """
        fd = open(result_file, 'r')
        result = {}
        for line in fd.readlines():
            if 'CRITICAL' in line:
                url_tu = line[line.index('[diff_query]') + len('[diff_query]'):]
            elif 'INFO' in line:
                tmp_dict = {}
                res = re.findall('src key:(\w+)', line)
                if len(res) > 0:
                    key_value = res[0]
                    """
                if 'does not exists' in line:
                    tmp_dict[key_value] = 'does not exists in old js file'
                    result.setdefault(url_tu, []).append(tmp_dict)
                """
                if 'is not equal' in line:
                    diff_value = []
                    res1 = re.findall(r'->(\S+) .* dst value (\S+)', line)
                    if len(res1[0]) == 2:
                        new_value = res1[0][0]
                        old_value = res1[0][1]
                    diff_value.append(new_value)
                    diff_value.append(old_value)
                    tmp_dict[key_value] = diff_value
                    result.setdefault(url_tu, []).append(tmp_dict)
        report_name = self.generate_report(result)
        return report_name

    def generate_report(self,result):
        """
        generate_report    生成js querydiff web报告
        Args:
            result:diff信息的字典
        Returns:
            It will return the report file name.
        """
        report_name = "/home/bfp/UbfPlatform/js_querydiff/diff_report/diff_report_" + ''.join(random.sample(string.digits * (6 / 10 + 1), 6)) + ".html"
        f = open(report_name, 'w')
        for urltu_key in result:
            report_table = html.XtsHtmlTable()
            table_title = "<caption> <b> <center>" + urltu_key + "</b></center></caption>"
            report_table.add_head('参数名', '新js', '旧js')
            #diff 列表
            for key_diff in result[urltu_key]:
                #diff的字典
                for key in key_diff:
                    report_table.add_body_line(key, key_diff[key][0], key_diff[key][1])
            f.write(str(table_title))
            f.write(str(report_table))
            f.write(str('<br />'))
        f.close()
        return report_name

    def test_process(self, task_id):
        """
        test_process    Remote call the querydiff tool.
        Args:
            task_id: The id of the querydiff task.
        """
        self.db_conn.ping(True)
        self.cursor = self.db_conn.cursor()
        self.cursor.execute('''select id, js_url from js_querydiff_task where id = %d''' %(task_id))
        js_url_list = self.cursor.fetchall()
        self.db_conn.commit()
    
        for js_url in js_url_list:
            (task_id, js_url) = js_url
            #clear the log file in the nginx server.
            os.system("ssh zhongzhiwei01@cp01-testing-ecom636.cp01.baidu.com \
                    '> /home/users/zhongzhiwei01/nginx_cm/logs/access.log'")
            #set the online js file
            remote_proxy_conn = rpyc.classic.connect("10.46.189.32", 18812)
            remote_proxy_conn.modules.os.system("/home/tools/tools/python/2.7.2/64/bin/python \
                    /home/users/guoan/tools/jsquerydiff_zhongzhiwei/edit_conf.py \
                    http://cpro.baidustatic.com/cpro/ui/cm.js")
            #connect to the remote machine and call bat script.
            remote_win_conn = rpyc.classic.connect("10.94.25.60", 18812)
            remote_win_conn.modules.os.system("E:\js_querydiff\surf_url.bat")
            p1 = subprocess.Popen(['scp', 
                    'zhongzhiwei01@cp01-testing-ecom636.cp01.baidu.com:/home/users/zhongzhiwei01/nginx_cm/logs/access.log',
                    './js_querydiff/diff_log/nginx_access.log.old'], stdout = subprocess.PIPE)
            p1.wait()
            #modify the proxy 
            if js_url:
                remote_proxy_conn.modules.os.system("/home/tools/tools/python/2.7.2/64/bin/python \
                        /home/users/guoan/tools/jsquerydiff_zhongzhiwei/edit_conf.py " + js_url)
            else:
                remote_proxy_conn.modules.os.system("/home/tools/tools/python/2.7.2/64/bin/python \
                        /home/users/guoan/tools/jsquerydiff_zhongzhiwei/edit_conf.py \
                        http://cpro.baidustatic.com/cpro/ui/cm.js")

            #clear the log file in the nginx server.
            os.system("ssh zhongzhiwei01@cp01-testing-ecom636.cp01.baidu.com \
                    '> /home/users/zhongzhiwei01/nginx_cm/logs/access.log'")
            #surf the webpage using new js file
            remote_win_conn.modules.os.system("E:\js_querydiff\surf_url.bat")
            p2 = subprocess.Popen(['scp', 
                    'zhongzhiwei01@cp01-testing-ecom636.cp01.baidu.com:/home/users/zhongzhiwei01/nginx_cm/logs/access.log',
                    './js_querydiff/diff_log/nginx_access.log.new'], stdout = subprocess.PIPE)
            p2.wait()
            #do the querydiff
            os.system("python ./js_querydiff/url_diff.py \
                    -a ./js_querydiff/diff_log/nginx_access.log.old \
                    -b ./js_querydiff/diff_log/nginx_access.log.new &> ./js_querydiff/diff_result/out.log")
            #parse the diff log
            report_name = self.parse_result('./js_querydiff/diff_result/out.log')
            #将报告传输到远程nginx服务器上
            p3 = subprocess.Popen(['scp', '-r', '/home/bfp/UbfPlatform/js_querydiff/diff_report/',
                    'zhongzhiwei01@cp01-testing-ecom636.cp01.baidu.com:/home/users/zhongzhiwei01/nginx_pb/html/'], stdout = subprocess.PIPE)
            p3.wait()
            report_url = "http://cp01-testing-ecom636.cp01.baidu.com:8045/diff_report/" + report_name[report_name.index('diff_report_'):]
            #add result info to the result tables.
            self.cursor.execute('''insert into js_querydiff_result (task_id, result_url) values (%d, "%s")'''
                    %(task_id, report_url))
            self.db_conn.commit()
            
            
            #更新task表
            self.cursor.execute('''update js_querydiff_task set test_status="finish" where id = %d''' %(task_id))
            self.db_conn.commit()

    def run(self):
        """
        task_monitor    Monitor the new task in the js_querydiff_task, run the querydiff when new task is added.
        """
        while True:
            self.db_conn.ping(True)
            query_cmd = '''select js_querydiff_task.id from js_querydiff_task 
                where js_querydiff_task.test_status="%s"''' % 'waiting'
            self.cursor.execute(query_cmd)
            tasks = self.cursor.fetchall()
            self.db_conn.commit()
            for task in tasks:
                task_id = int(task[0])
                self.test_process(task_id)
            time.sleep(20) 
            

if __name__ == '__main__': 
    task_monitor = DatabaseMonitor()
    task_monitor.run()

    
