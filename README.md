# pylocust
locust使用教程：  
    https://www.locust.io/  
    https://github.com/locustio/locust/blob/4bde2ca90f28bde649ff4ce2c86e36a6e6260856/docs/index.rst  
源码引用pyecharts模块  
    pip install pyecharts  
源码引用pymysql模块（请自行安装，并配置文件夹内sql.py文件）  
    CREATE TABLE `effect_stats` (
      `median_response_time` varchar(255) DEFAULT NULL,
      `min_response_time` varchar(255) DEFAULT NULL,
      `current_rps` varchar(255) DEFAULT NULL,
      `name` varchar(255) DEFAULT NULL,
      `num_failures` varchar(255) DEFAULT NULL,
      `max_response_time` varchar(255) DEFAULT NULL,
      `avg_content_length` varchar(255) DEFAULT NULL,
      `avg_response_time` varchar(255) DEFAULT NULL,
      `method` varchar(255) DEFAULT NULL,
      `num_requests` varchar(255) DEFAULT NULL,
      `timestap` varchar(255) DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;  
二次开发增加：  
    stop按钮 --停止功能（压测执行后，页面右侧显示）  
    timer --计时器（首页输入项，可为空）  
    测试数据数据库写入（每个线程执行情况，存储至数据表）  
额外增加：  
    测试报告优化（原报告数据项过少,数据项细化）  
    增加Total Count、avg_response_time、avg_content_length、num_requests  
