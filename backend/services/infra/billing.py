"""
Stripe billing service — reusable across any SaaS app.

Plans:
  - local: free, self-hosted (no Stripe)
  - starter: $9/mo — shared VPS, 1 project
  - pro: $29/mo — dedicated VPS, unlimited projects

Setup:
  1. Create a Stripe account at https://stripe.com
  2. Create two Products with monthly prices in the Stripe dashboard
  3. Set STRIPE_SECRET_KEY, STRIPE_STARTER_PRICE_ID, STRIPE_PRO_PRICE_ID in .env
  4. Set STRIPE_WEBHOOK_SECRET after configuring the webhook endpoint
"""
import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

PLANS = {
    "starter": {
        "name": "Starter",
        "price": "$9/mo",
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID", ""),
        "features": [
            "Cloud-hosted dashboard",
            "AI Generate (50 calls/mo)",
            "Email briefing",
            "1 project",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": "$29/mo",
        "price_id": os.getenv("STRIPE_PRO_PRICE_ID", ""),
        "features": [
            "Dedicated VPS",
            "Unlimited AI Generate",
            "Email + WhatsApp briefing",
            "Unlimited projects",
            "Custom domain",
            "Priority support",
        ],
    },
}

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def create_customer(email: str, username: str) -> str:
    """Create a Stripe customer. Returns customer ID."""
    customer = stripe.Customer.create(
        email=email,
        metadata={"username": username},
    )
    return customer.id


def create_checkout_session(
    customer_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session. Returns the checkout URL."""
    plan_config = PLANS.get(plan)
    if not plan_config or not plan_config["price_id"]:
        raise ValueError(f"Invalid plan or price ID not configured: {plan}")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": plan_config["price_id"],
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan": plan},
    )
    return session.url


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session for managing subscription."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def parse_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify and parse a Stripe webhook event."""
    event = stripe.Webhook.construct_event(
        payload, sig_header, WEBHOOK_SECRET
    )
    return event


def cancel_subscription(subscription_id: str):
    """Cancel a subscription at period end."""
    stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True,
    )


def get_subscription(subscription_id: str) -> dict:
    """Get subscription details."""
    return stripe.Subscription.retrieve(subscription_id)
