"""
Notification-Service: Ermittelt Empfänger, baut E-Mails und versendet per SMTP.

Alle öffentlichen Funktionen sind für den Aufruf über FastAPI BackgroundTasks
gedacht. Fehler werden geloggt, aber nie an den Aufrufer weitergereicht.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models.campaign import Campaign, CampaignStatus
from app.models.user import User, UserRole
from app.services.email_templates import (
    render_new_campaign,
    render_new_comment,
    render_status_change,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# SMTP transport
# --------------------------------------------------------------------------- #
def _send_email(to: str, subject: str, html_body: str) -> None:
    """Sendet eine einzelne HTML-E-Mail. Loggt Fehler, wirft nie Exceptions."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        if settings.SMTP_USE_TLS:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to], msg.as_string())
        server.quit()
        logger.info("E-Mail gesendet an %s: %s", to, subject)
    except Exception:
        logger.exception("E-Mail-Versand fehlgeschlagen an %s: %s", to, subject)


def _send_to_many(recipients: list[str], subject: str, html_body: str) -> None:
    """Sendet dieselbe E-Mail an mehrere Empfänger (einzeln, kein CC/BCC)."""
    for addr in recipients:
        _send_email(addr, subject, html_body)


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #
def _get_marketing_emails(db: Session) -> list[str]:
    rows = db.query(User.email).filter(User.role == UserRole.marketing).all()
    return [r.email for r in rows]


def _format_send_at(campaign: Campaign) -> str:
    if campaign.send_at:
        return campaign.send_at.strftime("%d.%m.%Y %H:%M Uhr")
    return "Noch nicht festgelegt"


# --------------------------------------------------------------------------- #
# Öffentliche Benachrichtigungs-Funktionen
# --------------------------------------------------------------------------- #
def notify_status_change(
    db: Session,
    campaign: Campaign,
    old_status: CampaignStatus,
    new_status: CampaignStatus,
    actor: User,
    reason: str | None = None,
) -> None:
    """
    Benachrichtigt Ersteller + Marketing-User bei Statusänderung.
    Der Akteur selbst wird ausgeschlossen.
    """
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return

    subject, html = render_status_change(
        campaign_title=campaign.title,
        campaign_id=campaign.id,
        old_status=old_status.value if hasattr(old_status, "value") else str(old_status),
        new_status=new_status.value if hasattr(new_status, "value") else str(new_status),
        actor_name=actor.name,
        reason=reason,
        base_url=settings.APP_BASE_URL,
    )

    recipients: list[str] = []

    # Ersteller benachrichtigen (falls nicht selbst der Akteur)
    creator = campaign.creator
    if creator and creator.id != actor.id:
        recipients.append(creator.email)

    # Alle Marketing-User (außer Akteur)
    for email in _get_marketing_emails(db):
        if email != actor.email and email not in recipients:
            recipients.append(email)

    if recipients:
        _send_to_many(recipients, subject, html)


def notify_new_comment(
    db: Session,
    campaign: Campaign,
    comment_text: str,
    author: User,
) -> None:
    """
    Benachrichtigt Ersteller + Marketing-User bei neuem Kommentar.
    Der Kommentar-Autor selbst wird ausgeschlossen.
    """
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return

    subject, html = render_new_comment(
        campaign_title=campaign.title,
        campaign_id=campaign.id,
        comment_text=comment_text,
        author_name=author.name,
        base_url=settings.APP_BASE_URL,
    )

    recipients: list[str] = []

    # Ersteller (falls nicht der Autor)
    creator = campaign.creator
    if creator and creator.id != author.id:
        recipients.append(creator.email)

    # Marketing-User (außer Autor)
    for email in _get_marketing_emails(db):
        if email != author.email and email not in recipients:
            recipients.append(email)

    if recipients:
        _send_to_many(recipients, subject, html)


def notify_new_campaign(
    db: Session,
    campaign: Campaign,
    creator: User,
) -> None:
    """
    Benachrichtigt alle Marketing-User bei neuer Kampagne.
    """
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return

    dept_name = campaign.department.name if campaign.department else "Unbekannt"

    subject, html = render_new_campaign(
        campaign_title=campaign.title,
        campaign_id=campaign.id,
        creator_name=creator.name,
        department_name=dept_name,
        send_at_str=_format_send_at(campaign),
        base_url=settings.APP_BASE_URL,
    )

    recipients = _get_marketing_emails(db)
    if recipients:
        _send_to_many(recipients, subject, html)
