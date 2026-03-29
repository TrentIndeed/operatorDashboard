"""
Billing API routes — Stripe checkout, webhooks, subscription management.
Triggers VPS provisioning on successful payment.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from db.database import get_db, User
from services.infra.billing import (
    PLANS,
    create_customer,
    create_checkout_session,
    create_portal_session,
    parse_webhook,
)
from services.infra.provisioning import create_server, wait_for_running
from services.infra.deploy import deploy_to_server

router = APIRouter(prefix="/billing", tags=["billing"])

APP_URL = os.getenv("APP_URL", "http://localhost:3000")


@router.get("/plans")
def get_plans():
    """Get available plans with features and pricing."""
    return {
        "local": {
            "name": "Local",
            "price": "Free",
            "features": [
                "Self-hosted on your machine",
                "Unlimited AI Generate",
                "Full source code access",
                "No usage limits",
            ],
        },
        **PLANS,
    }


@router.post("/checkout")
def checkout(body: dict, db: Session = Depends(get_db)):
    """Create a Stripe checkout session for a plan upgrade."""
    user_id = body.get("user_id")
    plan = body.get("plan")

    if plan not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create Stripe customer if needed
    if not user.stripe_customer_id:
        customer_id = create_customer(user.email or f"{user.username}@local", user.username)
        user.stripe_customer_id = customer_id
        db.commit()

    url = create_checkout_session(
        customer_id=user.stripe_customer_id,
        plan=plan,
        success_url=f"{APP_URL}/dashboard?checkout=success",
        cancel_url=f"{APP_URL}/pricing?checkout=canceled",
    )

    return {"url": url}


@router.post("/portal")
def customer_portal(body: dict, db: Session = Depends(get_db)):
    """Create a Stripe Customer Portal session for managing subscription."""
    user_id = body.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")

    url = create_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=f"{APP_URL}/dashboard",
    )
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = parse_webhook(payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        background_tasks.add_task(_handle_checkout_complete, data)

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        background_tasks.add_task(_handle_subscription_change, data)

    return {"received": True}


def _handle_checkout_complete(session_data: dict):
    """After successful checkout: update user plan, provision VPS."""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        customer_id = session_data.get("customer")
        subscription_id = session_data.get("subscription")
        plan = session_data.get("metadata", {}).get("plan", "starter")

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            print(f"[Billing] No user found for customer {customer_id}")
            return

        user.plan = plan
        user.stripe_subscription_id = subscription_id
        user.subscription_status = "active"
        db.commit()

        print(f"[Billing] User {user.username} upgraded to {plan}")

        # Provision VPS for cloud plans
        if plan in ("starter", "pro"):
            _provision_user_instance(user, db)

    except Exception as e:
        print(f"[Billing] Checkout handler failed: {e}")
    finally:
        db.close()


def _handle_subscription_change(sub_data: dict):
    """Handle subscription updates (cancel, past_due, etc.)."""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        sub_id = sub_data.get("id")
        status = sub_data.get("status")  # active, past_due, canceled, unpaid

        user = db.query(User).filter(User.stripe_subscription_id == sub_id).first()
        if not user:
            return

        user.subscription_status = status
        if status == "canceled":
            user.plan = "local"
            # Don't destroy instance immediately — give grace period
            user.instance_status = "stopped"
        db.commit()

        print(f"[Billing] Subscription {sub_id} → {status} for {user.username}")
    except Exception as e:
        print(f"[Billing] Subscription handler failed: {e}")
    finally:
        db.close()


def _provision_user_instance(user, db):
    """Create a VPS and deploy the dashboard for a paying user."""
    import asyncio

    async def _do_provision():
        from db.database import SessionLocal
        db2 = SessionLocal()
        try:
            u = db2.query(User).filter(User.id == user.id).first()
            u.instance_status = "provisioning"
            db2.commit()

            # Create server
            server_type = "cx22" if u.plan == "starter" else "cx32"
            server_name = f"op-{u.username}-{u.id}"

            print(f"[Provision] Creating {server_type} for {u.username}...")
            result = await create_server(name=server_name, server_type=server_type)

            u.instance_id = result["server_id"]
            u.instance_ip = result["ip"]
            db2.commit()

            # Wait for server to be ready
            print(f"[Provision] Waiting for server {result['server_id']}...")
            ready = await wait_for_running(result["server_id"], timeout=180)
            if not ready:
                u.instance_status = "error"
                db2.commit()
                print(f"[Provision] Server failed to start for {u.username}")
                return

            # Wait for cloud-init to finish (Docker install etc.)
            await asyncio.sleep(60)

            # Deploy the dashboard
            print(f"[Provision] Deploying to {result['ip']}...")
            env_vars = {
                "DASHBOARD_USER": u.username,
                "DASHBOARD_PASS": "changeme",  # User should change this
            }

            domain = u.instance_domain or ""
            deploy_result = await deploy_to_server(
                ip=result["ip"],
                env_vars=env_vars,
                domain=domain,
            )

            if deploy_result["status"] == "ok":
                u.instance_status = "running"
                print(f"[Provision] Deployed for {u.username} at {result['ip']}")
            else:
                u.instance_status = "error"
                print(f"[Provision] Deploy failed for {u.username}: {deploy_result['message']}")

            db2.commit()

        except Exception as e:
            print(f"[Provision] Failed for user {user.id}: {e}")
            try:
                u = db2.query(User).filter(User.id == user.id).first()
                u.instance_status = "error"
                db2.commit()
            except:
                pass
        finally:
            db2.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_do_provision())
        else:
            asyncio.run(_do_provision())
    except RuntimeError:
        asyncio.run(_do_provision())
