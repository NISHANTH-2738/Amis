# tests/test_database.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(__file__)
))

from backend.database.connection    import create_tables
from backend.services.inspection_pipeline import run_inspection
from backend.services.database_service    import get_todays_stats
from backend.services.notification_service import get_recent_alerts

print("=" * 50)
print("  FABRIGUARD — DATABASE + REDIS TEST")
print("=" * 50)

# Step 1 — Create tables in PostgreSQL
print("\n[1] Creating database tables...")
create_tables()

# Step 2 — Run 10 inspections
print("\n[2] Running 10 inspections...")
for i in range(10):
    result = run_inspection(f"test_image_{i}.jpg")
    level  = result["severity"]["level"]
    status = result["status"]
    badge  = ["","MONITOR","ALERT","ISOLATE","STOP"][level] \
             if level > 0 else "PASS"
    print(f"  [{i+1}] {status:4} | {badge:8} | "
          f"{result['machine_id']} | "
          f"{result['defects'][0]['class'] if result['defects'] else '-'}")

# Step 3 — Check stats from PostgreSQL
print("\n[3] Today's stats from PostgreSQL:")
stats = get_todays_stats()
print(f"  Inspected:   {stats['inspected_today']}")
print(f"  Defects:     {stats['defects_today']}")
print(f"  Alerts:      {stats['active_alerts']}")
print(f"  Defect rate: {stats['defect_rate']}%")

# Step 4 — Check alerts from Redis
print("\n[4] Recent alerts from Redis:")
alerts = get_recent_alerts(5)
if alerts:
    for a in alerts:
        print(f"  {a['level_name']:8} | "
              f"{a['machine_id']} | "
              f"{a['defect']} | "
              f"{a.get('root_cause','no cause')}")
else:
    print("  No alerts yet")

print("\n" + "=" * 50)
print("  ALL SYSTEMS WORKING")
print("=" * 50)