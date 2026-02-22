#!/usr/bin/env python3
"""
Seed script – creates demo data for local development.

Usage:
    cd backend
    python seed.py
"""
import io
import os
import sys
from datetime import datetime, timezone, timedelta

# Allow running from project root or backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.department import Department
from app.models.user import User, UserRole
from app.models.settings import AppSettings
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_file import CampaignFile
from app.models.campaign_asset import CampaignAsset
from app.storage import storage


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Seeding database...")

        # ---------- Settings ----------
        if not db.query(AppSettings).first():
            db.add(AppSettings(id=1, min_gap_days=2))
            db.commit()
            print("  [+] AppSettings created (min_gap_days=2)")
        else:
            print("  [~] AppSettings already exist, skipping")

        # ---------- Departments ----------
        dept_names = [
            "Vorstand",
            "Kommunikation",
            "Mitgliederbetreuung",
            "Veranstaltungen",
            "Bildung & Qualifizierung",
        ]
        depts = {}
        for name in dept_names:
            dept = db.query(Department).filter(Department.name == name).first()
            if not dept:
                dept = Department(name=name, is_active=True)
                db.add(dept)
                db.commit()
                db.refresh(dept)
                print(f"  [+] Department: {name}")
            else:
                print(f"  [~] Department '{name}' exists, skipping")
            depts[name] = dept

        # ---------- Users ----------
        requester_email = "requester@bvmw.example"
        marketing_email = "marketing@bvmw.example"

        requester = db.query(User).filter(User.email == requester_email).first()
        if not requester:
            requester = User(
                email=requester_email,
                name="Anna Müller",
                role=UserRole.requester,
                department_id=depts["Kommunikation"].id,
            )
            db.add(requester)
            db.commit()
            db.refresh(requester)
            print(f"  [+] User (requester): {requester_email}")
        else:
            print(f"  [~] User '{requester_email}' exists, skipping")

        marketer = db.query(User).filter(User.email == marketing_email).first()
        if not marketer:
            marketer = User(
                email=marketing_email,
                name="Bernd Schmidt",
                role=UserRole.marketing,
                department_id=None,
            )
            db.add(marketer)
            db.commit()
            db.refresh(marketer)
            print(f"  [+] User (marketing): {marketing_email}")
        else:
            print(f"  [~] User '{marketing_email}' exists, skipping")

        # ---------- Example Campaign ----------
        existing = db.query(Campaign).filter(Campaign.title == "Demo Newsletter April 2025").first()
        if not existing:
            send_at = datetime.now(timezone.utc) + timedelta(days=5)
            send_at = send_at.replace(hour=9, minute=0, second=0, microsecond=0)

            campaign = Campaign(
                title="Demo Newsletter April 2025",
                channel="email",
                department_id=depts["Kommunikation"].id,
                status=CampaignStatus.submitted,
                send_at=send_at,
                created_by_id=requester.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(campaign)
            db.flush()  # get campaign.id

            # --- PDF ---
            pdf_content = b"%PDF-1.4 Demo Newsletter\n% Dummy PDF for seeding"
            pdf_path = f"campaigns/{campaign.id}/pdf/v1.pdf"
            storage.save(pdf_path, io.BytesIO(pdf_content))

            cf = CampaignFile(
                campaign_id=campaign.id,
                version=1,
                original_filename="newsletter_april_2025.pdf",
                storage_path=pdf_path,
                file_size=len(pdf_content),
                uploaded_by_id=requester.id,
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(cf)
            db.flush()

            # --- Assets (2 dummy images) ---
            for i, (fname, mime) in enumerate([
                ("header_bild.png", "image/png"),
                ("sponsor_logo.jpeg", "image/jpeg"),
            ], start=1):
                # Minimal valid 1×1 pixel images
                if mime == "image/png":
                    # 1x1 transparent PNG
                    raw = bytes.fromhex(
                        "89504e470d0a1a0a0000000d494844520000000100000001"
                        "0806000000 1f15c4890000000a4944415478016360000000020001"
                        "e221bc330000000049454e44ae426082"
                        .replace(" ", "")
                    )
                else:
                    # Minimal JPEG
                    raw = bytes.fromhex(
                        "ffd8ffe000104a46494600010100000100010000"
                        "ffdb004300080606070605080707070909080a0c"
                        "140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20"
                        "242e2720222c231c1c2837292c30313434341f27"
                        "39 3d38 3232 3c4l 3c4b 4e50"
                        "5050 3021 5555 5557 595c 5e5e 5e3b 4667"
                        "6b68 6667 6c67 6768 7075 79 7a 79 766f 7778"
                        "70 6f 7778 7072 72 73 73 73 74 74 7475"
                        "ffc00011080001000103012200021101031101"
                        "ffc4001f0000010501010101010100000000000000"
                        "00010203040506070809 0a0b"
                        "ffc40 0b51100020102040403040705040400010277"
                        "00 01020311040521124131 0613516107 2232 8114"
                        "42 9191 a108 2342 b1 c115 52 d1 f009 3334 6272"
                        "0a 0925 4316 1718 19 2627 2829 2a3435 36373839"
                        "3a 4344 4546 47484 94a 5354 5556 5758 595a6364"
                        "6566 6768 696a 7374 7576 7778 797a 8384 85 8687"
                        "8889 8a92 9394 9596 9798 999a a2a3 a4a5 a6a7"
                        "a8a9 aab2 b3b4 b5b6 b7b8 b9ba c2c3 c4c5c6c7c8"
                        "c9ca d2d3 d4d5 d6d7 d8d9 da e1e2 e3e4 e5e6e7e8"
                        "e9ea f1f2 f3f4 f5f6 f7f8 f9fa"
                        "ffda000c03010002110311003f00"
                        "ffd9"
                        .replace(" ", "")
                    )

                # Use simple placeholder bytes if decode fails
                placeholder = b"\x00" * 64

                asset = CampaignAsset(
                    campaign_id=campaign.id,
                    original_filename=fname,
                    sanitized_filename=fname,
                    storage_path="",
                    mime_type=mime,
                    file_size=len(placeholder),
                    is_deleted=False,
                    uploaded_by_id=requester.id,
                    uploaded_at=datetime.now(timezone.utc),
                )
                db.add(asset)
                db.flush()

                asset_path = f"campaigns/{campaign.id}/assets/{asset.id}-{fname}"
                storage.save(asset_path, io.BytesIO(placeholder))
                asset.storage_path = asset_path
                asset.file_size = len(placeholder)
                db.flush()
                print(f"  [+] Asset: {fname}")

            db.commit()
            print(f"  [+] Campaign: 'Demo Newsletter April 2025' (id={campaign.id})")

        else:
            print("  [~] Demo campaign exists, skipping")

        print("\nSeed complete!")
        print(f"  Requester login: X-User: {requester_email}")
        print(f"  Marketing login: X-User: {marketing_email}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
