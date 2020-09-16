def has_payment_method(user):
    return hasattr(user, "customer") and user.customer is not None
