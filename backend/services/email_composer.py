"""
Email Composer — builds the daily operator briefing HTML email.

Reads the current state of the database (tasks, leads, briefing, market gaps,
content drafts, GitHub activity) and builds a mobile-friendly HTML email.
"""
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from db.database import (
    Task, Goal, NewsBriefing, MarketGap, ContentDraft,
    GithubRepo, Lead, AISuggestion,
)


def _esc(s: str | None) -> str:
    """Minimal HTML escape."""
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _stage_label(db: Session) -> tuple[int, str]:
    """Return (stage_number, stage_name) for the founder's current stage."""
    from agents.stage import get_stage, stage_name
    s = get_stage(db)
    return s, stage_name(s)


def compose_daily_briefing(db: Session) -> tuple[str, str, str]:
    """
    Build the full daily briefing email.

    Returns (subject, html, text).
    """
    today = date.today()
    today_label = today.strftime("%A, %B %d")
    stage_num, stage_nm = _stage_label(db)

    # --- Fetch all data ---
    tasks = (
        db.query(Task)
        .filter(Task.status == "pending")
        .order_by(Task.priority_score.desc())
        .limit(10)
        .all()
    )
    completed_today = db.query(Task).filter(Task.status == "done").count()

    briefing_items = (
        db.query(NewsBriefing)
        .filter(NewsBriefing.dismissed == False)
        .order_by(NewsBriefing.created_at.desc())
        .limit(5)
        .all()
    )
    gaps = (
        db.query(MarketGap)
        .filter(MarketGap.status == "new")
        .order_by(MarketGap.opportunity_score.desc())
        .limit(5)
        .all()
    )
    drafts = (
        db.query(ContentDraft)
        .filter(ContentDraft.status == "draft")
        .order_by(ContentDraft.created_at.desc())
        .limit(4)
        .all()
    )
    suggestions = (
        db.query(AISuggestion)
        .filter(AISuggestion.dismissed == False)
        .order_by(AISuggestion.created_at.desc())
        .limit(5)
        .all()
    )

    # Leads — Tier 1 and 2 only, new status
    hot_leads = (
        db.query(Lead)
        .filter(Lead.status == "new", Lead.tier != None, Lead.tier <= 2)
        .order_by(Lead.tier.asc(), Lead.created_at.desc())
        .limit(10)
        .all()
    )
    tier1_count = db.query(Lead).filter(Lead.tier == 1, Lead.status == "new").count()
    tier2_count = db.query(Lead).filter(Lead.tier == 2, Lead.status == "new").count()
    tier3_new = db.query(Lead).filter(Lead.tier == 3, Lead.status == "new").count()
    contacted_count = db.query(Lead).filter(Lead.status == "contacted").count()

    # Outreach stats — today, week, all-time
    start_today = datetime.combine(date.today(), datetime.min.time())
    start_week = datetime.utcnow() - timedelta(days=7)
    sent_today = db.query(Lead).filter(Lead.contacted_at != None, Lead.contacted_at >= start_today).count()
    sent_week = db.query(Lead).filter(Lead.contacted_at != None, Lead.contacted_at >= start_week).count()
    sent_all = db.query(Lead).filter(Lead.contacted_at != None).count()
    responded_week = db.query(Lead).filter(
        Lead.responded_at != None, Lead.responded_at >= start_week
    ).count()
    responded_all = db.query(Lead).filter(Lead.responded_at != None).count()
    interested_week = db.query(Lead).filter(
        Lead.status == "interested", Lead.updated_at != None, Lead.updated_at >= start_week
    ).count() if hasattr(Lead, "updated_at") else 0
    interested_all = db.query(Lead).filter(Lead.status == "interested").count()
    beta_all = db.query(Lead).filter(Lead.status == "beta_user").count()

    # Follow-ups due
    cutoff = datetime.utcnow() - timedelta(days=4)
    follow_ups = (
        db.query(Lead)
        .filter(
            Lead.status == "contacted",
            Lead.contacted_at != None,
            Lead.contacted_at < cutoff,
            Lead.follow_up_sent == False,
        )
        .all()
    )

    # GitHub activity (last 24h)
    repos = db.query(GithubRepo).all()
    recent_commits = []
    for r in repos:
        if r.last_commit_at and r.last_commit_message:
            try:
                t = r.last_commit_at if not isinstance(r.last_commit_at, str) else datetime.fromisoformat(str(r.last_commit_at).replace("Z", "+00:00"))
                hours_ago = (datetime.utcnow() - t.replace(tzinfo=None)).total_seconds() / 3600
                if hours_ago < 36:
                    recent_commits.append({
                        "repo": r.name,
                        "message": r.last_commit_message[:80],
                        "hours": round(hours_ago, 1),
                    })
            except Exception:
                pass
    recent_commits.sort(key=lambda c: c["hours"])

    # --- Build subject ---
    subject = (
        f"ParameshAI — Stage {stage_num}: {stage_nm} · {len(tasks)} tasks · "
        f"{len(hot_leads)} hot leads · {today_label}"
    )

    # --- Build HTML ---
    # Inline styles only (no <style> block) for maximum mobile compatibility
    S_CARD = "background:#0f0f11;border:1px solid #1f1f22;border-radius:12px;padding:16px;margin-bottom:12px;"
    S_LABEL = "font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#9ca3af;margin:0 0 8px 0;"
    S_TITLE = "font-size:15px;font-weight:600;color:#ffffff;margin:0 0 4px 0;"
    S_BODY = "font-size:13px;color:#d1d5db;margin:0;line-height:1.45;"
    S_MUTED = "font-size:12px;color:#9ca3af;margin:4px 0 0 0;"
    S_LINK = "color:#a855f7;text-decoration:none;"

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#ffffff;">
<div style="max-width:640px;margin:0 auto;padding:24px 16px;">
<div style="margin-bottom:24px;">
<h1 style="font-size:22px;font-weight:700;color:#ffffff;margin:0 0 4px 0;">ParameshAI Daily Briefing</h1>
<p style="font-size:13px;color:#9ca3af;margin:0;">{_esc(today_label)} &middot; Stage {stage_num} of 4: {_esc(stage_nm)}</p>
</div>""")

    # --- Outreach stats block (matches spec) ---
    parts.append(f"""<div style="{S_CARD}">
<p style="{S_LABEL}">📊 Outreach Stats</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;color:#d1d5db;">
<tr><td style="padding:3px 0;"><strong>Today:</strong></td><td style="padding:3px 0;text-align:right;"><span style="color:#ffffff;font-weight:600;">{sent_today}</span> sent <span style="color:#6b7280;">(target: 30)</span></td></tr>
<tr><td style="padding:3px 0;"><strong>This week:</strong></td><td style="padding:3px 0;text-align:right;"><span style="color:#ffffff;font-weight:600;">{sent_week}</span> sent &middot; <span style="color:#67e8f9;">{responded_week}</span> responses &middot; <span style="color:#34d399;">{interested_week}</span> interested</td></tr>
<tr><td style="padding:3px 0;"><strong>All time:</strong></td><td style="padding:3px 0;text-align:right;"><span style="color:#ffffff;font-weight:600;">{sent_all}</span> sent &middot; <span style="color:#67e8f9;">{responded_all}</span> responses &middot; <span style="color:#34d399;">{interested_all}</span> interested &middot; <span style="color:#c084fc;">{beta_all}</span> beta</td></tr>
<tr><td style="padding:3px 0;"><strong>Follow-ups due:</strong></td><td style="padding:3px 0;text-align:right;color:{('#fbbf24' if len(follow_ups) > 0 else '#6b7280')};font-weight:600;">{len(follow_ups)}</td></tr>
<tr><td style="padding:3px 0;"><strong>New leads:</strong></td><td style="padding:3px 0;text-align:right;color:#ffffff;font-weight:600;">{tier1_count + tier2_count + tier3_new} <span style="color:#6b7280;font-weight:400;">({tier1_count} T1, {tier2_count} T2, {tier3_new} T3)</span></td></tr>
</table>
</div>""")

    # --- Today's Tasks ---
    parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">Today\'s Tasks ({len(tasks)})</p>')
    if not tasks:
        parts.append(f'<p style="{S_BODY}">No tasks. Hit AI Generate on the dashboard.</p>')
    else:
        for t in tasks:
            score_color = "#fbbf24" if t.priority_score >= 8 else "#a855f7" if t.priority_score >= 6 else "#9ca3af"
            parts.append(f"""<div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #1f1f22;">
<div style="display:inline-block;background:{score_color};color:#000;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;margin-right:8px;">{t.priority_score:.0f}</div>
<span style="font-size:13px;color:#ffffff;">{_esc(t.title)}</span>
<div style="font-size:11px;color:#9ca3af;margin-top:3px;">{t.estimated_minutes}m &middot; {_esc(t.project_tag or 'general')}</div>
</div>""")
    parts.append("</div>")

    # --- Hot Leads (Tier 1 + 2) — full spec format ---
    if hot_leads:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">New Leads ({len(hot_leads)})</p>')
        parts.append('<p style="font-size:11px;color:#6b7280;margin:0 0 12px 0;">Reply to this email with status codes like <code style="background:#1f1f22;padding:1px 4px;border-radius:3px;color:#c084fc;">#L142 contacted</code> to update leads.</p>')

        for lead in hot_leads:
            tier_color = "#fbbf24" if lead.tier == 1 else "#60a5fa" if lead.tier == 2 else "#6b7280"
            tier_emoji = "🟡" if lead.tier == 1 else "🔵" if lead.tier == 2 else "⚪"
            tier_label = f"TIER {lead.tier}" if lead.tier else "TIER ?"
            platform = _esc(lead.platform.replace("reddit_", "r/").replace("_", " "))
            post_url = lead.post_url or lead.source_url or "#"

            # Time ago
            time_ago = ""
            if lead.post_date:
                try:
                    dt = lead.post_date if isinstance(lead.post_date, datetime) else datetime.fromisoformat(str(lead.post_date).replace("Z", "+00:00"))
                    hours = (datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds() / 3600
                    if hours < 1:
                        time_ago = "just now"
                    elif hours < 24:
                        time_ago = f"{int(hours)} hours ago"
                    else:
                        time_ago = f"{int(hours/24)} days ago"
                except Exception:
                    pass

            parts.append(f"""<div style="border:2px solid {tier_color};border-radius:12px;padding:14px;margin-bottom:16px;">

<div style="font-size:11px;font-weight:700;color:{tier_color};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid {tier_color}33;">
{tier_emoji} {tier_label} &nbsp;|&nbsp; {platform} &nbsp;|&nbsp; @{_esc(lead.username)}{f' &nbsp;|&nbsp; {time_ago}' if time_ago else ''}
</div>

<div style="margin-bottom:10px;">
<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">POST</div>
<p style="font-size:13px;color:#e5e7eb;margin:0;line-height:1.5;white-space:pre-wrap;">{_esc((lead.post_text or lead.message or '')[:600])}{'...' if lead.post_text and len(lead.post_text) > 600 else ''}</p>
</div>

<p style="margin:0 0 10px 0;font-size:12px;"><a href="{_esc(post_url)}" style="{S_LINK}">🔗 {_esc(post_url)}</a></p>""")

            # Account summary
            if lead.account_summary:
                parts.append(f"""<div style="margin-bottom:10px;">
<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">ABOUT THIS PERSON</div>
<p style="font-size:12px;color:#d1d5db;margin:0;line-height:1.6;white-space:pre-wrap;">{_esc(lead.account_summary)}</p>
</div>""")

            # Demo video recommendation
            if lead.include_demo_video:
                demo_is_yes = lead.include_demo_video.lower().strip().startswith("yes")
                demo_color = "#34d399" if demo_is_yes else "#9ca3af"
                demo_bg = "#064e3b" if demo_is_yes else "#1f1f22"
                parts.append(f"""<div style="background:{demo_bg};border-left:3px solid {demo_color};padding:8px 10px;margin-bottom:10px;border-radius:0 6px 6px 0;">
<div style="font-size:10px;color:{demo_color};font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">📹 INCLUDE DEMO VIDEO</div>
<p style="font-size:12px;color:#d1d5db;margin:0;line-height:1.4;">{_esc(lead.include_demo_video)}</p>
</div>""")

            # Draft DM
            if lead.draft_dm:
                parts.append(f"""<div style="background:#1a0b2e;border:1px solid #4c1d95;border-radius:8px;padding:12px;margin-bottom:10px;">
<div style="font-size:10px;color:#c084fc;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">DRAFT DM (copy and send on {platform})</div>
<p style="font-size:13px;color:#e9d5ff;margin:0;line-height:1.5;white-space:pre-wrap;font-family:ui-monospace,'SF Mono',Menlo,monospace;">{_esc(lead.draft_dm)}</p>
</div>""")

            # Draft public reply
            if lead.draft_public_reply:
                parts.append(f"""<div style="background:#0c2a2e;border:1px solid #155e75;border-radius:8px;padding:12px;margin-bottom:10px;">
<div style="font-size:10px;color:#67e8f9;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">DRAFT PUBLIC REPLY (post as a comment)</div>
<p style="font-size:13px;color:#cffafe;margin:0;line-height:1.5;white-space:pre-wrap;font-family:ui-monospace,'SF Mono',Menlo,monospace;">{_esc(lead.draft_public_reply)}</p>
</div>""")

            # Reply codes
            parts.append(f"""<div style="font-size:11px;color:#6b7280;line-height:1.7;margin-top:10px;padding-top:10px;border-top:1px solid #1f1f22;">
&rarr; Reply with: <code style="background:#1f1f22;padding:1px 5px;border-radius:3px;color:#86efac;">#L{lead.id} contacted</code> (after you DM them)<br>
&rarr; Reply with: <code style="background:#1f1f22;padding:1px 5px;border-radius:3px;color:#fca5a5;">#L{lead.id} skip</code> (if not worth reaching out)<br>
&rarr; Reply with: <code style="background:#1f1f22;padding:1px 5px;border-radius:3px;color:#fcd34d;">#L{lead.id} interested</code> (if they say they'd try it)
</div>""")

            parts.append("</div>")  # close lead card
        parts.append("</div>")  # close leads section

    # --- Follow-ups due — full spec format ---
    if follow_ups:
        from services.message_drafter import draft_follow_up
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">📬 Follow-up Queue ({len(follow_ups)})</p>')
        parts.append('<p style="font-size:11px;color:#6b7280;margin:0 0 12px 0;">Contacted 4+ days ago with no response.</p>')

        for lead in follow_ups:
            days_ago = (datetime.utcnow() - lead.contacted_at).days if lead.contacted_at else 0
            platform = _esc(lead.platform.replace("reddit_", "r/").replace("_", " "))
            post_url = lead.post_url or lead.source_url or "#"

            # Generate follow-up draft on the fly (cached per-lead would be better, but this works)
            try:
                fu_text = draft_follow_up({
                    "username": lead.username,
                    "platform": lead.platform,
                    "post_text": lead.post_text or lead.message or "",
                })
            except Exception:
                fu_text = "Hey, just bumping this in case it got buried. No worries if it's not relevant."

            parts.append(f"""<div style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #1f1f22;">
<p style="font-size:13px;color:#ffffff;margin:0 0 4px 0;font-weight:600;">@{_esc(lead.username)} <span style="color:#9ca3af;font-weight:400;">({platform})</span> &mdash; contacted {days_ago} days ago</p>
<p style="margin:0 0 8px 0;font-size:12px;"><a href="{_esc(post_url)}" style="{S_LINK}">🔗 {_esc(post_url)}</a></p>
<div style="background:#2d1a07;border:1px solid #92400e;border-radius:8px;padding:10px;margin-bottom:8px;">
<div style="font-size:10px;color:#fbbf24;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">FOLLOW-UP DRAFT</div>
<p style="font-size:13px;color:#fef3c7;margin:0;line-height:1.5;white-space:pre-wrap;font-family:ui-monospace,'SF Mono',Menlo,monospace;">{_esc(fu_text)}</p>
</div>
<div style="font-size:11px;color:#6b7280;">
&rarr; Reply: <code style="background:#1f1f22;padding:1px 5px;border-radius:3px;color:#86efac;">#L{lead.id} followed_up</code> &nbsp;|&nbsp; <code style="background:#1f1f22;padding:1px 5px;border-radius:3px;color:#9ca3af;">#L{lead.id} no_response</code>
</div>
</div>""")
        parts.append("</div>")

    # --- Briefing ---
    if briefing_items:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">Intel Briefing</p>')
        for b in briefing_items:
            parts.append(f"""<div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #1f1f22;">
<p style="{S_TITLE}">[{_esc(b.category or 'news')}] {_esc(b.headline)}</p>
<p style="{S_BODY}">{_esc(b.summary or '')}</p>
{f'<p style="{S_MUTED}"><strong>Action:</strong> {_esc(b.suggested_action)}</p>' if b.suggested_action else ''}
</div>""")
        parts.append("</div>")

    # --- Market gaps ---
    if gaps:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">Growth Opportunities</p>')
        for g in gaps:
            parts.append(f"""<div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #1f1f22;">
<p style="{S_BODY}">[{_esc(g.source or 'source')}] {_esc(g.description)}</p>
{f'<p style="{S_MUTED}"><strong>Action:</strong> {_esc(g.suggested_action)}</p>' if g.suggested_action else ''}
{f'<p style="margin:4px 0 0 0;"><a href="{_esc(g.source_url)}" style="{S_LINK}">&rarr; Source</a></p>' if g.source_url else ''}
</div>""")
        parts.append("</div>")

    # --- Content Drafts ---
    if drafts:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">Content Drafts</p>')
        for d in drafts:
            parts.append(f"""<div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #1f1f22;">
<p style="{S_TITLE}">[{_esc(d.platform)}] {_esc(d.title)}</p>
<p style="{S_BODY}">{_esc((d.hook or d.body or '')[:200])}{'...' if d.body and len(d.body) > 200 else ''}</p>
</div>""")
        parts.append("</div>")

    # --- GitHub activity ---
    if recent_commits:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">Recent Code</p>')
        for c in recent_commits[:6]:
            parts.append(f'<p style="{S_BODY}"><strong>{_esc(c["repo"])}</strong> &middot; {_esc(c["message"])} <span style="color:#6b7280;">({c["hours"]}h ago)</span></p>')
        parts.append("</div>")

    # --- Suggestions ---
    if suggestions:
        parts.append(f'<div style="{S_CARD}"><p style="{S_LABEL}">AI Suggestions</p>')
        for s in suggestions:
            parts.append(f'<p style="{S_BODY}">[{_esc(s.category or "general")}] {_esc(s.body)}</p>')
        parts.append("</div>")

    # Footer
    parts.append(f"""<div style="margin-top:24px;padding-top:16px;border-top:1px solid #1f1f22;text-align:center;">
<a href="https://dragonoperator.com/outreach" style="{S_LINK}">Open Outreach Dashboard</a>
</div>
</div></body></html>""")

    html = "\n".join(parts)

    # --- Plain text fallback ---
    text_parts = [
        f"ParameshAI Daily Briefing — {today_label}",
        f"Stage {stage_num} of 4: {stage_nm}",
        "",
        f"STATUS: {len(tasks)} tasks, {tier1_count} T1 / {tier2_count} T2 leads, "
        f"{contacted_count} contacted, {len(follow_ups)} follow-ups",
        "",
        "TASKS:",
    ]
    for t in tasks:
        text_parts.append(f"  [{t.priority_score:.0f}] {t.title} ({t.estimated_minutes}m)")

    if hot_leads:
        text_parts.extend(["", "HOT LEADS:"])
        for l in hot_leads:
            text_parts.append(f"  [T{l.tier}] @{l.username} on {l.platform}")
            text_parts.append(f"    {(l.post_text or '')[:120]}")
            if l.draft_dm:
                text_parts.append(f"    DM: {l.draft_dm[:200]}")
            text_parts.append(f"    {l.post_url or l.source_url or ''}")

    if briefing_items:
        text_parts.extend(["", "BRIEFING:"])
        for b in briefing_items:
            text_parts.append(f"  [{b.category}] {b.headline}")

    text = "\n".join(text_parts)
    return subject, html, text
