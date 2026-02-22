#!/usr/bin/env python3
"""
Seed script – creates demo data for local development.

Usage:
    cd backend
    python seed.py
"""
import base64
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
            # Minimal valid 1×1 pixel images encoded as base64.
            # PNG: 1×1 red pixel (RGBA)
            PNG_1X1 = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQ"
                "AABjkB6QAAAABJRU5ErkJggg=="
            )
            # JPEG: 1×1 grey pixel
            JPEG_1X1 = base64.b64decode(
                "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkS"
                "Ew8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAARC"
                "AABAAEDASIAAREBASIAAREB/8QAFgABAQEAAAAAAAAAAAAAAAAABgUEB"
                "AQFBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
                "AQEBAf/aAAwDAQACEQMRAD8Amk2rbWUgPSTRRRVJ//Z"
            )

            for fname, mime, raw in [
                ("header_bild.png", "image/png", PNG_1X1),
                ("sponsor_logo.jpeg", "image/jpeg", JPEG_1X1),
            ]:
                asset = CampaignAsset(
                    campaign_id=campaign.id,
                    original_filename=fname,
                    sanitized_filename=fname,
                    storage_path="",
                    mime_type=mime,
                    file_size=len(raw),
                    is_deleted=False,
                    uploaded_by_id=requester.id,
                    uploaded_at=datetime.now(timezone.utc),
                )
                db.add(asset)
                db.flush()

                asset_path = f"campaigns/{campaign.id}/assets/{asset.id}-{fname}"
                storage.save(asset_path, io.BytesIO(raw))
                asset.storage_path = asset_path
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
