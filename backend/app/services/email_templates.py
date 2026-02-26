"""
HTML-E-Mail-Templates für Benachrichtigungen (deutsche Sprache).

Jede Funktion gibt ein (subject, html_body)-Tupel zurück.
"""

STATUS_LABELS: dict[str, str] = {
    "submitted": "Eingereicht",
    "in_review": "In Prüfung",
    "changes_needed": "Änderungen erforderlich",
    "scheduled": "Geplant",
    "approved": "Freigegeben",
    "rejected": "Abgelehnt",
    "sent": "Versendet",
}

_BASE_STYLE = """\
<style>
  body { font-family: Arial, Helvetica, sans-serif; color: #333; line-height: 1.6; }
  .container { max-width: 600px; margin: 0 auto; padding: 20px; }
  .header { background-color: #003366; color: white; padding: 15px 20px;
            border-radius: 4px 4px 0 0; }
  .header h1 { margin: 0; font-size: 18px; }
  .content { background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd;
             border-top: none; border-radius: 0 0 4px 4px; }
  .button { display: inline-block; background-color: #003366; color: white;
            padding: 10px 20px; text-decoration: none; border-radius: 4px;
            margin-top: 15px; }
  .footer { font-size: 12px; color: #999; margin-top: 20px; text-align: center; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 3px;
           background-color: #e0e0e0; font-weight: bold; }
  td { padding: 4px 0; }
  td:first-child { padding-right: 15px; }
</style>"""


def _wrap(title: str, body_html: str, campaign_url: str = "") -> str:
    link = ""
    if campaign_url:
        link = f'<a href="{campaign_url}" class="button">Kampagne ansehen</a>'
    return (
        f"<!DOCTYPE html>"
        f'<html><head><meta charset="utf-8">{_BASE_STYLE}</head>'
        f"<body><div class=\"container\">"
        f'<div class="header"><h1>{title}</h1></div>'
        f'<div class="content">{body_html}{link}</div>'
        f'<div class="footer">Diese Nachricht wurde automatisch von BVMW SendHub generiert.</div>'
        f"</div></body></html>"
    )


def render_status_change(
    campaign_title: str,
    campaign_id: int,
    old_status: str,
    new_status: str,
    actor_name: str,
    reason: str | None,
    base_url: str,
) -> tuple[str, str]:
    old_label = STATUS_LABELS.get(old_status, old_status)
    new_label = STATUS_LABELS.get(new_status, new_status)
    subject = f'Kampagne \u201e{campaign_title}\u201c \u2014 Status: {new_label}'

    reason_html = ""
    if reason:
        reason_html = f"<p><strong>Begr\u00fcndung:</strong> {reason}</p>"

    body = (
        "<p>Guten Tag,</p>"
        "<p>der Status einer Kampagne wurde ge\u00e4ndert:</p>"
        "<table>"
        f"<tr><td><strong>Kampagne:</strong></td><td>{campaign_title}</td></tr>"
        f'<tr><td><strong>Alter Status:</strong></td><td><span class="badge">{old_label}</span></td></tr>'
        f'<tr><td><strong>Neuer Status:</strong></td><td><span class="badge">{new_label}</span></td></tr>'
        f"<tr><td><strong>Ge\u00e4ndert von:</strong></td><td>{actor_name}</td></tr>"
        f"</table>{reason_html}"
    )
    url = f"{base_url}/campaigns/{campaign_id}"
    return subject, _wrap("Status\u00e4nderung", body, url)


def render_new_comment(
    campaign_title: str,
    campaign_id: int,
    comment_text: str,
    author_name: str,
    base_url: str,
) -> tuple[str, str]:
    subject = f'Neuer Kommentar zu \u201e{campaign_title}\u201c'

    body = (
        "<p>Guten Tag,</p>"
        f"<p>es gibt einen neuen Kommentar zur Kampagne <strong>{campaign_title}</strong>:</p>"
        f'<blockquote style="border-left: 3px solid #003366; padding-left: 15px;'
        f' margin: 15px 0; color: #555;">{comment_text}</blockquote>'
        f"<p><strong>Verfasser:</strong> {author_name}</p>"
    )
    url = f"{base_url}/campaigns/{campaign_id}"
    return subject, _wrap("Neuer Kommentar", body, url)


def render_new_campaign(
    campaign_title: str,
    campaign_id: int,
    creator_name: str,
    department_name: str,
    send_at_str: str,
    base_url: str,
) -> tuple[str, str]:
    subject = f'Neue Kampagne eingereicht: \u201e{campaign_title}\u201c'

    body = (
        "<p>Guten Tag,</p>"
        "<p>eine neue Kampagne wurde eingereicht und wartet auf Pr\u00fcfung:</p>"
        "<table>"
        f"<tr><td><strong>Kampagne:</strong></td><td>{campaign_title}</td></tr>"
        f"<tr><td><strong>Erstellt von:</strong></td><td>{creator_name}</td></tr>"
        f"<tr><td><strong>Abteilung:</strong></td><td>{department_name}</td></tr>"
        f"<tr><td><strong>Geplanter Versand:</strong></td><td>{send_at_str}</td></tr>"
        "</table>"
    )
    url = f"{base_url}/campaigns/{campaign_id}"
    return subject, _wrap("Neue Kampagne", body, url)
