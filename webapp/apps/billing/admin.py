from django.contrib import admin

from .models import Customer, Product, Plan, Subscription, SubscriptionItem, Event

# Register your models here.
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Plan)
admin.site.register(Subscription)
admin.site.register(SubscriptionItem)
admin.site.register(Event)
