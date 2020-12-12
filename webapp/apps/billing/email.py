from datetime import datetime

from django.core.mail import EmailMessage

from webapp.settings import DEBUG


def send_subscribe_to_plan_email(user, new_plan):
    email_msg = EmailMessage(
        subject=f"You are now subscribed to {new_plan.nickname}",
        body=(
            f"Thanks for subscribing to {new_plan.nickname}! "
            "Please write back to this email if you have any questions or feedback.\n\n"
            "Best,\n"
            "The Compute Studio Team"
        ),
        from_email="notifications@compute.studio",
        to=[user.email],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e


def send_sub_canceled_email(user, period_end: datetime):
    email_msg = EmailMessage(
        subject=f"Your C/S subscription will be cancelled on {period_end.date()}",
        body=(
            "We are sorry to see you go. If you have a moment, please let us know why "
            "you have cancelled your subscription and what we can do to win you back "
            "in the future.\n\nBest,\nThe C/S Team"
        ),
        from_email="notifications@compute.studio",
        to=[user.email],
        cc=["hank@compute.studio"],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e
