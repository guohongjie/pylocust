# -*- coding: utf-8 -*-

import csv
import json
import logging
import os.path
from collections import defaultdict
from itertools import chain
from time import time,sleep,strftime
from sql import select_sql,insert_sql
import six
from flask import Flask, make_response, render_template, request,redirect,url_for,jsonify
from gevent import pywsgi

from locust import __version__ as version
from six.moves import StringIO, xrange

from . import runners
from .runners import MasterLocustRunner
from .stats import distribution_csv, median_from_dict, requests_csv, sort_stats
from .util.cache import memoize
from pyecharts import Line,option,Bar,EffectScatter
import datetime
from pyecharts import Page
from pyecharts.constants import DEFAULT_HOST
logger = logging.getLogger(__name__)

DEFAULT_CACHE_TIME = 2.0

app = Flask(__name__)
app.debug = True
app.root_path = os.path.dirname(os.path.abspath(__file__))


@app.route('/')
def index():
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        slave_count = runners.locust_runner.slave_count
    else:
        slave_count = 0

    if runners.locust_runner.host:
        host = runners.locust_runner.host
    elif len(runners.locust_runner.locust_classes) > 0:
        host = runners.locust_runner.locust_classes[0].host
    else:
        host = None
    delete_total = """truncate table effect_total;"""
    delete_stats = """truncate table effect_stats;"""
    select_sql(delete_total)
    select_sql(delete_stats)
    total_sql = """insert into effect_total 
    (errors,current_response_time_percentile_50,
    current_response_time_percentile_95,state,total_rps,fail_ratio,user_count,timestap)
    values ('start','0','0','ready','0','0','0','0')"""
    insert_sql(total_sql)
    return render_template("index.html",
        state=runners.locust_runner.state,
        is_distributed=is_distributed,
        slave_count=slave_count,
        user_count=runners.locust_runner.user_count,
        version=version,
        host=host
    )

@app.route('/swarm', methods=["POST"])
def swarm():
    assert request.method == "POST"

    locust_count = int(request.form["locust_count"])
    hatch_rate = float(request.form["hatch_rate"])
    runners.locust_runner.start_hatching(locust_count, hatch_rate)
    response = make_response(json.dumps({'success':True, 'message': 'Swarming started'}))
    response.headers["Content-type"] = "application/json"
    return response

@app.route('/stop')
def stop():
    runners.locust_runner.stop()
    response = make_response(json.dumps({'success':True, 'message': 'Test stopped'}))
    response.headers["Content-type"] = "application/json"
    return response
@app.route('/time_stop')
def time_stop():
    """增加等待时间，待时间执行后，跳转STOP"""
    stay_time = request.args.get('stop_time')
    sleep(int(stay_time))
    redirect(url_for('stop'))
    msg = {'success':'stop'}
    res = make_response(jsonify(msg))
    return res
@app.route("/stats/reset")
def reset_stats():
    runners.locust_runner.stats.reset_all()
    return "ok"
    
@app.route("/stats/requests/csv")
def request_stats_csv():
    response = make_response(requests_csv())
    file_name = "requests_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route("/stats/distribution/csv")
def distribution_stats_csv():
    response = make_response(distribution_csv())
    file_name = "distribution_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

@app.route('/stats/requests')
@memoize(timeout=DEFAULT_CACHE_TIME, dynamic_timeout=True)
def request_stats():
    stats = []
    
    for s in chain(sort_stats(runners.locust_runner.request_stats), [runners.locust_runner.stats.total]):
        stats.append({
            "method": s.method,
            "name": s.name,
            "num_requests": s.num_requests,
            "num_failures": s.num_failures,
            "avg_response_time": s.avg_response_time,
            "min_response_time": s.min_response_time or 0,
            "max_response_time": s.max_response_time,
            "current_rps": s.current_rps,
            "median_response_time": s.median_response_time,
            "avg_content_length": s.avg_content_length,
        })

    errors = [e.to_dict() for e in six.itervalues(runners.locust_runner.errors)]

    # Truncate the total number of stats and errors displayed since a large number of rows will cause the app
    # to render extremely slowly. Aggregate stats should be preserved.
    report = {"stats": stats[:500], "errors": errors[:500]}

    if stats:
        report["total_rps"] = stats[len(stats)-1]["current_rps"]
        report["fail_ratio"] = runners.locust_runner.stats.total.fail_ratio
        report["current_response_time_percentile_95"] = runners.locust_runner.stats.total.get_current_response_time_percentile(0.95)
        report["current_response_time_percentile_50"] = runners.locust_runner.stats.total.get_current_response_time_percentile(0.5)
    
    is_distributed = isinstance(runners.locust_runner, MasterLocustRunner)
    if is_distributed:
        report["slave_count"] = runners.locust_runner.slave_count
    
    report["state"] = runners.locust_runner.state
    report["user_count"] = runners.locust_runner.user_count
    with open(r'E:\wc.log','a+') as f:
        f.write(str(report['stats'])+'\n')
    if report["state"] != "stopped" and report["state"] != "ready":
        t = strftime("%Y%m%d%H%M%S")
        insert_total(report,t)
        insert_stat(report['stats'],t)
    return json.dumps(report)

def insert_total(report,t):
    #增加insert 数据方法
    errors = '.'.join(map(lambda x:str(x) ,report['errors'] if report['errors'] else '')) or 'no errors'
    crtp_50 = str(report['current_response_time_percentile_50'])
    crtp_90 = str(report['current_response_time_percentile_95'])
    state = report["state"]
    total_rps = str(report["total_rps"])
    fail_ratio = str(report["fail_ratio"])
    user_count = str(report["user_count"])
    timestap = t
    total_sql = """insert into effect_total 
(errors,current_response_time_percentile_50,
current_response_time_percentile_95,state,total_rps,fail_ratio,user_count,timestap)
values ('%s','%s','%s','%s','%s','%s','%s','%s'
)"""%(errors,crtp_50,crtp_90,state,total_rps,fail_ratio,user_count,timestap)
    insert_stat = insert_sql(total_sql)
    return insert_stat
def insert_stat(list,t):
    stat_list = list
    timestap = t
    for sing_dict in stat_list:
        medirt,minrt,cur_rps = str(sing_dict['median_response_time']),str(sing_dict['min_response_time']),str(sing_dict['current_rps'])
        name,num_f = str(sing_dict['name']),str(sing_dict['num_failures'])
        max_rt,avg_cl,avg_rt =str(sing_dict['max_response_time']),str(sing_dict['avg_content_length']),str(sing_dict['avg_response_time'])
        method,num_requests = str(sing_dict["method"]),str(sing_dict["num_requests"])
        stats_sql = """insert into effect_stats (median_response_time,min_response_time,current_rps,
name,num_failures,max_response_time,avg_content_length,avg_response_time,method,num_requests,timestap) values(
'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s',
'%s');"""%(medirt,minrt,cur_rps,name,num_f,max_rt,avg_cl,avg_rt,method,num_requests,timestap)
        insert_stats = insert_sql(stats_sql)
        # with open(r'G:\sql.log','a+') as f:
        #     f.write(stats_sql)


@app.route("/exceptions")
def exceptions():
    response = make_response(json.dumps({
        'exceptions': [
            {
                "count": row["count"], 
                "msg": row["msg"], 
                "traceback": row["traceback"], 
                "nodes" : ", ".join(row["nodes"])
            } for row in six.itervalues(runners.locust_runner.exceptions)
        ]
    }))
    response.headers["Content-type"] = "application/json"
    return response

@app.route("/exceptions/csv")
def exceptions_csv():
    data = StringIO()
    writer = csv.writer(data)
    writer.writerow(["Count", "Message", "Traceback", "Nodes"])
    for exc in six.itervalues(runners.locust_runner.exceptions):
        nodes = ", ".join(exc["nodes"])
        writer.writerow([exc["count"], exc["msg"], exc["traceback"], nodes])
    
    data.seek(0)
    response = make_response(data.read())
    file_name = "exceptions_{0}.csv".format(time())
    disposition = "attachment;filename={0}".format(file_name)
    response.headers["Content-type"] = "text/csv"
    response.headers["Content-disposition"] = disposition
    return response

def start(locust, options):
    pywsgi.WSGIServer((options.web_host, options.port),
                      app, log=None).serve_forever()


@app.route('/report')
def report():
    line_report = user_page()
    return render_template('report.html',
                           myechart=line_report.render_embed(),
                           host=DEFAULT_HOST,
                           script_list=line_report.get_js_dependencies())
def user_page():
    page = Page()  # 导入page容器
    line = total_user_rps()
    page.add(line)
    bar = single_user_rpst()
    page.add(bar)
    avg_tcl = single_user_acl()
    page.add(avg_tcl)
    num_requests = single_user_request()
    page.add(num_requests)
    return page
def total_user_rps():
    total_sql = """select user_count,timestap,total_rps,fail_ratio,current_response_time_percentile_50,current_response_time_percentile_95 from effect_total order by TID"""
    user_counts = select_sql(total_sql)
    users = [m[0] for m in user_counts]
    timestap_list = map(lambda x:str(x[0:2]+':'+x[2:4]+':'+x[4:6]),[m[1][8:] for m in user_counts])
    canvas_width, xaxis_interval = 1240,0
    line = Line('Total Count','Count',width=canvas_width)
    line.add('User_count',timestap_list,users,mark_point=["max", "min"],
             is_fill=True,line_opacity=0.2, area_opacity=0.4,datazoom_range=[10, 25],
             xaxis_name='Run Time',xaxis_name_pos='end',
             xaxis_interval=int(xaxis_interval),is_datazoom_show=True,
             is_yaxis_boundarygap=True,
             is_xaxislabel_align=True,is_xaxis_boundarygap=False)
    total_rps = [m[2] for m in user_counts]
    line.add('Total_RPS', timestap_list, total_rps, mark_point=["max", "min"],datazoom_range=[10, 25],
             is_fill=True, line_opacity=0.2, area_opacity=0.4,
             xaxis_name='Run Time', xaxis_name_pos='end',
             xaxis_interval=int(xaxis_interval),
              is_yaxis_boundarygap=True,is_datazoom_show=True,
             is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    fail_ratio = [m[3] for m in user_counts]
    line.add('Fail_ratio', timestap_list, fail_ratio, mark_point=["max", "min"],
             is_fill=True, line_opacity=0.2, area_opacity=0.4,
             xaxis_name='Run Time', xaxis_name_pos='end',is_datazoom_show=True,datazoom_range=[10, 25],
             xaxis_interval=int(xaxis_interval),
             xaxis_rotate=-90, is_yaxis_boundarygap=True,
             is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    cur_50_Rsp_time = [m[4] for m in user_counts]
    line.add('50%_Rps_Time', timestap_list, cur_50_Rsp_time, mark_point=["max", "min"],
             is_fill=True, line_opacity=0.2, area_opacity=0.4,
             xaxis_name='Run Time', xaxis_name_pos='end',is_datazoom_show=True,datazoom_range=[10, 25],
             xaxis_interval=int(xaxis_interval),
              is_yaxis_boundarygap=True,
             is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    cur_90_Rsp_time = [m[5] for m in user_counts]
    line.add('95%_Rps_Time', timestap_list, cur_90_Rsp_time, mark_point=["max", "min"],
             is_fill=True, line_opacity=0.2, area_opacity=0.4,
             xaxis_name='Run Time', xaxis_name_pos='end',is_datazoom_show=True,datazoom_range=[10, 25],
             xaxis_interval=int(xaxis_interval),
              is_yaxis_boundarygap=True,
             is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    return line
def single_user_rpst():
    canvas_width, xaxis_interval = 1240, 0
    name_sql = """select distinct(name) from effect_stats;"""
    interface_names = select_sql(name_sql)
    interface_name = [m[0] for m in interface_names]
    bar = Line("avg_resp_time","avg_response_time", width=canvas_width)
    for single_interface in interface_name:
        stats_sql = """select avg_response_time,timestap from effect_stats where name='%s';"""%(single_interface)
        avg_response_time = select_sql(stats_sql)
        avg_time = [str(m[0][:4]) for m in avg_response_time]
        timestap_list = map(lambda x: str(x[0:2] + ':' + x[2:4] + ':' + x[4:6]), [m[1][8:] for m in avg_response_time])
        bar.add("%s"%(single_interface),timestap_list, avg_time, mark_point=["max", "min"],
                 is_fill=True,
                line_opacity=0.2, area_opacity=0.4,
                 xaxis_name='Run Time', xaxis_name_pos='end',is_datazoom_show=True,datazoom_range=[10, 25],
                 xaxis_interval=int(xaxis_interval),
                  is_yaxis_boundarygap=True,
                 is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    return bar
def single_user_acl():
    canvas_width, xaxis_interval = 1240, 0
    name_sql = """select distinct(name) from effect_stats;"""
    interface_names = select_sql(name_sql)
    interface_name = [m[0] for m in interface_names]
    bar = Line("avg_cont_length","avg_content_length", width=canvas_width)
    for single_interface in interface_name:
        stats_sql = """select avg_content_length,timestap from effect_stats where name='%s';""" % (single_interface)
        avg_content_length = select_sql(stats_sql)
        content_lengt = [str(m[0][:4]) for m in avg_content_length]
        timestap_list = map(lambda x: str(x[0:2] + ':' + x[2:4] + ':' + x[4:6]), [m[1][8:] for m in avg_content_length])
        bar.add("%s" % (single_interface), timestap_list, content_lengt, mark_point=["max", "min"],
                is_fill=True,
                line_opacity=0.2, area_opacity=0.4,
                xaxis_name='Run Time', xaxis_name_pos='end', is_datazoom_show=True, datazoom_range=[10, 25],
                xaxis_interval=int(xaxis_interval),
                is_yaxis_boundarygap=True,
                is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    return bar
def single_user_request():
    canvas_width, xaxis_interval = 1240, 0
    name_sql = """select distinct(name) from effect_stats;"""
    interface_names = select_sql(name_sql)
    interface_name = [m[0] for m in interface_names]
    bar = Line("num_requests", "num_requests", width=canvas_width)
    for single_interface in interface_name:
        stats_sql = """select num_requests,timestap from effect_stats where name='%s';""" % (single_interface)
        num_requests = select_sql(stats_sql)
        requests = [str(m[0][:4]) for m in num_requests]
        timestap_list = map(lambda x: str(x[0:2] + ':' + x[2:4] + ':' + x[4:6]), [m[1][8:] for m in num_requests])
        bar.add("%s" % (single_interface), timestap_list, requests, mark_point=["max", "min"],
                is_fill=True,
                line_opacity=0.2, area_opacity=0.4,
                xaxis_name='Run Time', xaxis_name_pos='end', is_datazoom_show=True, datazoom_range=[10, 25],
                xaxis_interval=int(xaxis_interval),
                is_yaxis_boundarygap=True,
                is_xaxislabel_align=True, is_xaxis_boundarygap=False)
    return bar
