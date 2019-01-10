#!/usr/bin/env python
#-*-coding:utf-8 -*-
import MySQLdb

def select_sql(sql):
	db = MySQLdb.connect("10.144.24.130","test","test","autoTest",charset='utf8')
	# 使用cursor()方法获取操作游标 
	cursor = db.cursor()
	# 使用execute方法执行SQL语句
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_client=utf8")
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_results=utf8")
	cursor.execute("set character_set_server=utf8")
	cursor.execute('SET NAMES UTF8') 
	cursor.execute(sql)
	# 使用 fetchone() 方法获取一条数据
	data = cursor.fetchall()
	# 关闭数据库连接
	db.close()
	return data
def insert_sql(sql):
	db = MySQLdb.connect('10.144.24.130','test','test','autoTest',charset='utf8')
	cursor = db.cursor()
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_client=utf8")
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_results=utf8")
	cursor.execute("set character_set_server=utf8")
	cursor.execute('SET NAMES UTF8') 
	try:
		cursor.execute(sql)
		db.commit()
		return "True"
	except Exception as e:
		db.rollback()
		return str(e)
	db.close()
def update_sql(sql):
	db = MySQLdb.connect('10.144.24.130', 'test', 'test', 'autoTest', charset='utf8')
	cursor = db.cursor()
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_client=utf8")
	cursor.execute("set character_set_connection=utf8")
	cursor.execute("set character_set_results=utf8")
	cursor.execute("set character_set_server=utf8")
	cursor.execute('SET NAMES UTF8')
	try:
		cursor.execute(sql)
		db.commit()
		return "True"
	except Exception as e:
		db.rollback()
		return str(e)
	db.close()
if __name__ == "__main__":
	#s = """insert into behave_config values('Given 操作浏览器','拖动元素至')"""
	tupledate = insert_sql(s)
	#print tupledate
	#print insert_sql(s)


