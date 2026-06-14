"""
性能测试脚本 — 绕过 Django 版本检查，直接使用 MySQLdb

用法：
    .venv/Scripts/python calendar_app/management/commands/perf_test.py
"""

import time
import random
import MySQLdb
from datetime import datetime, timedelta

DB_CONFIG = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    passwd="Xiaotong2018",
    db="dbms",
    charset="utf8mb4",
)

THRESHOLD = {
    "insert_enrollments": 1.0,
    "insert_notifications": 1.0,
    "query_notifications": 2.0,
    "query_assignments": 2.0,
    "delete_enrollments": 2.0,
    "query_events": 2.0,
}

results = []


def connect():
    return MySQLdb.connect(**DB_CONFIG)


def fmt(ok, elapsed, threshold):
    status = "✅ 达标" if elapsed < threshold else "❌ 超时"
    return f"{elapsed:.4f}s  (限{threshold}s)  {status}"


# ================================================================
# Step 0: 预备 — 确保有足量数据
# ================================================================
print("=" * 60)
print("Step 0: 检查 / 补充测试数据")
print("=" * 60)

conn = connect()
cur = conn.cursor()

cur.execute("SELECT id FROM calendar_app_user ORDER BY id")
all_uids = [r[0] for r in cur.fetchall()]
uid = all_uids[0]

cur.execute("SELECT COUNT(*) FROM notifications")
notif_count = cur.fetchone()[0]
print(f"  当前 notifications 行数: {notif_count:,}")

TARGET = 900_000
if notif_count < TARGET:
    to_insert = TARGET - notif_count
    print(f"  需要插入 {to_insert:,} 条通知，请稍候…")
    batch = 10_000
    inserted = 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_uids = len(all_uids)
    while inserted < to_insert:
        chunk = min(batch, to_insert - inserted)
        rows = []
        for i in range(chunk):
            uid_pick = all_uids[(inserted + i) % n_uids]
            rows.append(
                f"({uid_pick}, 'Perf Test {inserted+i}', 'content', 'system', NULL, 0, '{ts}')"
            )
        sql = (
            "INSERT INTO notifications (user_id, title, content, type, related_id, is_read, created_at) VALUES "
            + ",".join(rows)
        )
        cur.execute(sql)
        conn.commit()
        inserted += chunk
        if inserted % 100_000 == 0:
            print(f"    已插入 {inserted:,} / {to_insert:,}")
    print(f"  ✅ notifications 数据补充完毕，当前共 {TARGET:,} 条")
else:
    print(f"  ✅ 数据已充足 ({notif_count:,} 条)")

cur.execute("SELECT COUNT(*) FROM notifications")
notif_count = cur.fetchone()[0]
print(f"  实际 notifications 行数: {notif_count:,}")

# 准备辅助 ID
cur.execute("SELECT id FROM students LIMIT 1")
row = cur.fetchone()
student_id = row[0] if row else None

cur.execute("SELECT id FROM courses LIMIT 1")
row = cur.fetchone()
course_id = row[0] if row else None

cur.close()
conn.close()

print()
print("=" * 60)
print("Step 1: 性能测试")
print("=" * 60)


# ----------------------------------------------------------------
# Test 1: INSERT enrollments
# ----------------------------------------------------------------
print("\n[1] enrollments INSERT")
conn = connect()
cur = conn.cursor()

# 先找一个不在 enrollments 里的 (student_id, course_id) 组合
cur.execute("SELECT id FROM courses ORDER BY id DESC LIMIT 20")
all_cids = [r[0] for r in cur.fetchall()]
cur.execute("SELECT course_id FROM enrollments WHERE student_id = %s", (student_id,))
existing_cids = {r[0] for r in cur.fetchall()}
free_cid = next((c for c in all_cids if c not in existing_cids), None)

if free_cid is None:
    # 插入一门新课来腾出位置
    cur.execute(
        "INSERT INTO courses (code, name, description, credit, schedule, faculty, max_students, semester_id) "
        "SELECT CONCAT('PERFTEST', UNIX_TIMESTAMP()), 'Perf Test Course', '', 3, 'Mon', 'FST', 50, semester_id "
        "FROM courses LIMIT 1"
    )
    conn.commit()
    free_cid = cur.lastrowid

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
t0 = time.perf_counter()
cur.execute(
    "INSERT INTO enrollments (student_id, course_id, enrolled_at, status) VALUES (%s, %s, %s, 'active')",
    (student_id, free_cid, now_str),
)
conn.commit()
t1 = time.perf_counter()
elapsed_ins_enroll = t1 - t0
insert_enroll_id = cur.lastrowid

print(
    f"  {fmt(elapsed_ins_enroll < THRESHOLD['insert_enrollments'], elapsed_ins_enroll, THRESHOLD['insert_enrollments'])}"
)
results.append(
    ("enrollments", "INSERT", elapsed_ins_enroll, THRESHOLD["insert_enrollments"])
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 2: INSERT notifications
# ----------------------------------------------------------------
print("\n[2] notifications INSERT")
conn = connect()
cur = conn.cursor()

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
t0 = time.perf_counter()
cur.execute(
    "INSERT INTO notifications (user_id, title, content, type, related_id, is_read, created_at) "
    "VALUES (%s, %s, '', 'system', NULL, 0, %s)",
    (uid, "Perf Insert Test", now_str),
)
conn.commit()
t1 = time.perf_counter()
elapsed_ins_notif = t1 - t0
insert_notif_id = cur.lastrowid

print(
    f"  {fmt(elapsed_ins_notif < THRESHOLD['insert_notifications'], elapsed_ins_notif, THRESHOLD['insert_notifications'])}"
)
results.append(
    ("notifications", "INSERT", elapsed_ins_notif, THRESHOLD["insert_notifications"])
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 3: SELECT notifications WHERE user_id + is_read (有索引)
# ----------------------------------------------------------------
print("\n[3] notifications SELECT (user_id + is_read)")
conn = connect()
cur = conn.cursor()

t0 = time.perf_counter()
cur.execute(
    "SELECT id, title, created_at FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY created_at DESC LIMIT 50",
    (uid,),
)
rows = cur.fetchall()
t1 = time.perf_counter()
elapsed_qry_notif = t1 - t0

print(f"  返回 {len(rows)} 行")
print(
    f"  {fmt(elapsed_qry_notif < THRESHOLD['query_notifications'], elapsed_qry_notif, THRESHOLD['query_notifications'])}"
)
results.append(
    (
        "notifications",
        "SELECT (user_id+is_read)",
        elapsed_qry_notif,
        THRESHOLD["query_notifications"],
    )
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 4: SELECT assignments WHERE course_id + deadline 范围
# ----------------------------------------------------------------
print("\n[4] assignments SELECT (course_id + deadline 范围)")
conn = connect()
cur = conn.cursor()

deadline_from = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
deadline_to = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")

t0 = time.perf_counter()
cur.execute(
    "SELECT id, title, deadline FROM assignments "
    "WHERE course_id = %s AND deadline BETWEEN %s AND %s ORDER BY deadline",
    (course_id, deadline_from, deadline_to),
)
rows = cur.fetchall()
t1 = time.perf_counter()
elapsed_qry_assign = t1 - t0

print(f"  返回 {len(rows)} 行")
print(
    f"  {fmt(elapsed_qry_assign < THRESHOLD['query_assignments'], elapsed_qry_assign, THRESHOLD['query_assignments'])}"
)
results.append(
    (
        "assignments",
        "SELECT (course_id+deadline范围)",
        elapsed_qry_assign,
        THRESHOLD["query_assignments"],
    )
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 5: DELETE enrollments
# ----------------------------------------------------------------
print("\n[5] enrollments DELETE")
conn = connect()
cur = conn.cursor()

t0 = time.perf_counter()
cur.execute("DELETE FROM enrollments WHERE id = %s", (insert_enroll_id,))
conn.commit()
t1 = time.perf_counter()
elapsed_del_enroll = t1 - t0

print(
    f"  {fmt(elapsed_del_enroll < THRESHOLD['delete_enrollments'], elapsed_del_enroll, THRESHOLD['delete_enrollments'])}"
)
results.append(
    ("enrollments", "DELETE", elapsed_del_enroll, THRESHOLD["delete_enrollments"])
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 6: SELECT events WHERE start_time 范围
# ----------------------------------------------------------------
print("\n[6] events SELECT (start_time 范围)")
conn = connect()
cur = conn.cursor()

start_from = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
start_to = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")

t0 = time.perf_counter()
cur.execute(
    "SELECT id, title, start_time, end_time FROM events "
    "WHERE start_time BETWEEN %s AND %s ORDER BY start_time",
    (start_from, start_to),
)
rows = cur.fetchall()
t1 = time.perf_counter()
elapsed_qry_events = t1 - t0

print(f"  返回 {len(rows)} 行")
print(
    f"  {fmt(elapsed_qry_events < THRESHOLD['query_events'], elapsed_qry_events, THRESHOLD['query_events'])}"
)
results.append(
    ("events", "SELECT (start_time范围)", elapsed_qry_events, THRESHOLD["query_events"])
)

cur.close()
conn.close()


# ----------------------------------------------------------------
# Test 7: EXPLAIN notifications 典型查询
# ----------------------------------------------------------------
print("\n[7] EXPLAIN notifications (90万条，典型查询)")
conn = connect()
cur = conn.cursor()

cur.execute(
    "EXPLAIN SELECT id, title, created_at FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY created_at DESC LIMIT 50",
    (uid,),
)
explain_rows = cur.fetchall()
col_names = [d[0] for d in cur.description]
cur.close()
conn.close()

print(f"  {'  |  '.join(col_names)}")
print(f"  {'-'*100}")
for r in explain_rows:
    row_str = "  |  ".join(str(v) if v is not None else "NULL" for v in r)
    print(f"  {row_str}")


# ================================================================
# 汇总输出
# ================================================================
print()
print("=" * 70)
print("性能测试汇总")
print("=" * 70)
print(f"{'表名':<20} {'操作':<30} {'耗时':>10} {'是否达标':>8}")
print("-" * 70)
for tbl, op, elapsed, threshold in results:
    status = "✅ 达标" if elapsed < threshold else "❌ 超时"
    print(f"{tbl:<20} {op:<30} {elapsed:>9.4f}s {status:>8}")
print("=" * 70)

# 清理测试插入的 notification
conn = connect()
cur = conn.cursor()
cur.execute("DELETE FROM notifications WHERE id = %s", (insert_notif_id,))
conn.commit()
cur.close()
conn.close()
