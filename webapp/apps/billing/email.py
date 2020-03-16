from django.core.mail import EmailMessage

from webapp.settings import DEBUG


def send_teams_interest_mail(user):
    email_msg = EmailMessage(
        subject="Thank you for your interest in Compute Studio Teams",
        body=(
            "Hi,\n\n"
            "Thanks for getting in touch about a Team account.\n\n"
            "Are you open to scheduling a call to discuss what you need?\n\n"
            "Best,\n"
            "Matt"
        ),
        from_email="matt@compute.studio",
        to=[user.email],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e


def send_unsubscribe_email(user):
    email_msg = EmailMessage(
        subject="Thank you for using Compute Studio",
        body=(
            "Hi,\n\n"
            "We are sorry to hear that you are leaving Compute Studio.\n\n"
            "Are you open to scheduling a call to discuss how we could improve?\n\n"
            "Best,\n"
            "Matt"
        ),
        from_email="matt@compute.studio",
        to=[user.email],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e


def send_subscribe_to_plan_email(user, new_plan):
    email_msg = EmailMessage(
        subject=f"You are now subscribed to {new_plan.nickname}",
        body=(
            f"Thanks for subscribing to {new_plan.nickname}! "
            "Please write back to this email if you have any questions or feedback.\n\n"
            "Best,\n"
            "Matt"
        ),
        from_email="Matt Jensen <matt@compute.studio>",
        to=[user.email],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e
