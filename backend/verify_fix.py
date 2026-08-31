import sys
sys.path.insert(0, "/home/claude/cloud_comm-main/backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, ScreeningRecord
from app.services.registry_service import check_duplicate_identity

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Simulate first screening: passport X1234567, DOB 1990-05-12
rec1 = ScreeningRecord(
    document_type="passport",
    document_number="X1234567",
    holder_name="JOHN DOE",
    date_of_birth="1990-05-12",
    risk_score=5.0,
    risk_label="LOW",
)
db.add(rec1)
db.commit()

# Simulate second screening: SAME doc number, SAME name, DIFFERENT DOB (the exact bug scenario)
result = check_duplicate_identity(
    document_number="X1234567",
    holder_name="JOHN DOE",
    image_hash=None,
    db=db,
    date_of_birth="1985-11-03",  # different DOB
)

print("=== Result ===")
print("is_duplicate:", result["is_duplicate"])
for f in result["flags"]:
    print(" FLAG:", f)

assert result["is_duplicate"] is True, "FAILED: DOB mismatch was not detected"
assert any("DOB MISMATCH" in f for f in result["flags"]), "FAILED: no DOB mismatch flag present"
print("\nPASS: same document number + conflicting DOB is now correctly flagged.")

# Sanity check: identical DOB should NOT be flagged (no false positive)
result2 = check_duplicate_identity(
    document_number="X1234567",
    holder_name="JOHN DOE",
    image_hash=None,
    db=db,
    date_of_birth="1990-05-12",  # same DOB as rec1
)
assert result2["is_duplicate"] is False, "FAILED: false positive on matching DOB"
print("PASS: identical record (same doc, name, DOB) correctly NOT flagged.")