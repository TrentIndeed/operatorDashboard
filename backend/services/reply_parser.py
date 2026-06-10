"""
Reply Parser — parses email replies containing status codes like "#L142 contacted"
and updates lead records accordingly.

Supported codes (case-insensitive, flexible formatting):
  #L142 contacted       — sent them a DM
  #L142 responded       — they replied
  #L142 interested      — they said they'd try it
  #L142 beta            — added to beta list
  #L142 paying          — converted to paid
  #L142 not_interested  — declined
  #L142 skip            — not worth reaching out
  #L142 followed_up     — sent follow-up
  #L142 no_response     — archive
"""
import re
from datetime import datetime
from sqlalchemy.orm import Session

from db.database import Lead, OutreachMessage

# Matches: #L142 contacted, # L142 contacted, #142 contacted, # 142 Contacted, etc.
# Case insensitive, flexible whitespace, optional L prefix
CODE_RE = re.compile(
    r"#\s*L?\s*(\d+)\s+([a-z_]+)",
    re.IGNORECASE,
)

VALID_STATUSES = {
    "contacted": "contacted",
    "responded": "responded",
    "interested": "interested",
    "beta": "beta_user",
    "beta_user": "beta_user",
    "paying": "paying",
    "not_interested": "not_interested",
    "notinterested": "not_interested",
    "decline": "not_interested",
    "declined": "not_interested",
    "skip": "skip",
    "skipped": "skip",
    "followed_up": "contacted",  # keeps contacted status but marks follow-up
    "followedup": "contacted",
    "follow_up": "contacted",
    "followup": "contacted",
    "no_response": "no_response",
    "noresponse": "no_response",
}


def parse_reply(email_body: str, db: Session) -> dict:
    """
    Parse an email body for status codes and update matching leads.

    Returns: {
        "updates": [{"lead_id": int, "status": str, "username": str}],
        "errors": [str],
        "unparsed": [str],
    }
    """
    updates = []
    errors = []
    unparsed = []

    if not email_body:
        return {"updates": updates, "errors": errors, "unparsed": unparsed}

    # Process line by line so we can flag lines that look like codes but don't match
    for line in email_body.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("#"):
            continue

        match = CODE_RE.search(line)
        if not match:
            unparsed.append(line_stripped)
            continue

        lead_id = int(match.group(1))
        raw_status = match.group(2).lower()
        status = VALID_STATUSES.get(raw_status)

        if not status:
            errors.append(f"Unknown status '{raw_status}' for lead #L{lead_id}")
            continue

        lead = db.query(Lead).get(lead_id)
        if not lead:
            errors.append(f"Lead #L{lead_id} not found")
            continue

        now = datetime.utcnow()
        prev_status = lead.status
        lead.status = status

        # Timestamp tracking
        if status == "contacted" and not lead.contacted_at:
            lead.contacted_at = now
        elif status == "responded" and not lead.responded_at:
            lead.responded_at = now

        # Follow-up marker
        if raw_status in ("followed_up", "followedup", "follow_up", "followup"):
            lead.follow_up_sent = True
            # Save the follow-up to message history
            if lead.draft_dm or lead.message:
                msg = OutreachMessage(
                    lead_id=lead.id,
                    direction="outbound",
                    message_type="follow_up",
                    message_text=f"(follow-up sent — see email thread)",
                )
                db.add(msg)

        # Save message to history for first contact
        if status == "contacted" and prev_status == "new" and lead.draft_dm:
            msg = OutreachMessage(
                lead_id=lead.id,
                direction="outbound",
                message_type="dm",
                message_text=lead.draft_dm,
            )
            db.add(msg)

        updates.append({
            "lead_id": lead_id,
            "status": status,
            "username": lead.username,
            "prev_status": prev_status,
        })

    db.commit()
    print(f"[ReplyParser] {len(updates)} updates, {len(errors)} errors, {len(unparsed)} unparsed")
    return {"updates": updates, "errors": errors, "unparsed": unparsed}
