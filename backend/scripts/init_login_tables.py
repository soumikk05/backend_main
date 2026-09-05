"""
Initialize user_login_sessions and admin_login_sessions tables in screening_v2.db
and populate them with realistic, government-grade audit session records.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import init_db, SessionLocal
from app.models.database import User, UserLoginSession, AdminLoginSession

def populate_login_sessions():
    init_db()
    db = SessionLocal()
    try:
        # Check users
        admin = db.query(User).filter(User.username == "admin_bureau").first()
        sharma = db.query(User).filter(User.username == "officer_sharma").first()
        verma = db.query(User).filter(User.username == "officer_verma").first()

        now = datetime.utcnow()

        # Seed admin_login_sessions if empty
        if db.query(AdminLoginSession).count() == 0:
            print("[+] Seeding admin_login_sessions...")
            admin_sessions = [
                AdminLoginSession(
                    admin_id=admin.id if admin else "adm-dir-001",
                    username="admin_bureau",
                    full_name="Director S. K. Mukherjee",
                    role="admin",
                    badge_number="DIR-001",
                    login_timestamp=now - timedelta(hours=2, minutes=15),
                    terminal_ip="10.0.4.12 (Bureau HQ Secure Network)",
                    security_clearance="LEVEL_5_DIRECTORATE",
                    mfa_status="VERIFIED_PKI_HARDWARE_KEY (YubiKey 5 FIPS)",
                    authorized_actions="USER_MGMT, AUDIT_INSPECTION, KEY_ROTATION, BLACKLIST_OVERRIDE",
                    auth_method="SALTED_BCRYPT_JWT_MFA",
                    session_status="ACTIVE",
                    token_preview="eyJhbGciOiJIUzI1Ni...Xv8M09Lk",
                ),
                AdminLoginSession(
                    admin_id=admin.id if admin else "adm-dir-001",
                    username="admin_bureau",
                    full_name="Director S. K. Mukherjee",
                    role="admin",
                    badge_number="DIR-001",
                    login_timestamp=now - timedelta(days=1, hours=4),
                    terminal_ip="10.0.4.12 (Bureau HQ Secure Network)",
                    security_clearance="LEVEL_5_DIRECTORATE",
                    mfa_status="VERIFIED_PKI_HARDWARE_KEY (YubiKey 5 FIPS)",
                    authorized_actions="MODEL_DEPLOYMENT, LOG_ARCHIVE_VERIFY",
                    auth_method="SALTED_BCRYPT_JWT_MFA",
                    session_status="TERMINATED_NORMAL",
                    token_preview="eyJhbGciOiJIUzI1Ni...P9wB12Zq",
                ),
            ]
            db.add_all(admin_sessions)

        # Seed user_login_sessions if empty
        if db.query(UserLoginSession).count() == 0:
            print("[+] Seeding user_login_sessions...")
            user_sessions = [
                UserLoginSession(
                    user_id=sharma.id if sharma else "usr-inv-002",
                    username="officer_sharma",
                    full_name="Sr. Inspector R. Sharma",
                    role="investigator",
                    badge_number="IND-7842",
                    login_timestamp=now - timedelta(minutes=45),
                    terminal_ip="192.168.1.104 (Terminal #4)",
                    terminal_device="Immigration Checkpoint Terminal #4 (Win64)",
                    auth_method="SALTED_BCRYPT_JWT",
                    session_status="ACTIVE",
                    screenings_conducted=14,
                    token_preview="eyJhbGciOiJIUzI1Ni...7Lp9Wq2A",
                ),
                UserLoginSession(
                    user_id=verma.id if verma else "usr-off-003",
                    username="officer_verma",
                    full_name="Officer A. Verma",
                    role="officer",
                    badge_number="BDR-1094",
                    login_timestamp=now - timedelta(hours=1, minutes=10),
                    terminal_ip="192.168.1.102 (Terminal #2)",
                    terminal_device="Border Security Gate #2 Scanner (Win64)",
                    auth_method="SALTED_BCRYPT_JWT",
                    session_status="ACTIVE",
                    screenings_conducted=28,
                    token_preview="eyJhbGciOiJIUzI1Ni...2Km8Xz7Q",
                ),
                UserLoginSession(
                    user_id=sharma.id if sharma else "usr-inv-002",
                    username="officer_sharma",
                    full_name="Sr. Inspector R. Sharma",
                    role="investigator",
                    badge_number="IND-7842",
                    login_timestamp=now - timedelta(days=1, hours=2),
                    terminal_ip="192.168.1.104 (Terminal #4)",
                    terminal_device="Immigration Checkpoint Terminal #4 (Win64)",
                    auth_method="SALTED_BCRYPT_JWT",
                    session_status="TERMINATED_NORMAL",
                    screenings_conducted=42,
                    token_preview="eyJhbGciOiJIUzI1Ni...1Vx9Ab4C",
                ),
            ]
            db.add_all(user_sessions)

        db.commit()
        print("[OK] Login session records successfully committed to dataset/screening_v2.db")
    finally:
        db.close()

    # Synchronize database to root screening_v2.db for easy viewing in sqliteviewer.app
    src_db = BASE_DIR / "dataset" / "screening_v2.db"
    dst_db = BASE_DIR / "screening_v2.db"
    shutil.copy2(src_db, dst_db)
    print(f"[OK] Synchronized: {src_db} -> {dst_db}")

if __name__ == "__main__":
    populate_login_sessions()
