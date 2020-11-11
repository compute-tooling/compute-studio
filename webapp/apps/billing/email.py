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
