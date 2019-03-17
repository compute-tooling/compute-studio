# Database Schema

Warning: Some parts of this document are out of date! They will be updated soon.

Core App Schema
-------------------

This schema is inherited by all modeling projects. They are permitted to extend this schema as needed. The end goal for this schema is for it to be the ideal set-up for a COMP project. Projects that meet all COMP criteria should not have to do much custom work on this schema.

- `Simulation`: save outputs, run time/costs reporting, upstream project version
and COMP version.
  - Foreign key to `Profile`
  - Foreign key to `Project`
  - One-to-one relation with `Inputs`
- `Inputs`: save inputs data

Users App Schema
-------------------

This schema defines:
- the Django auth [`AbstractUser`][] model
  - Note: this is likely to be swapped with the [`django-allauth`] package
- Stipe models that map almost directly to the Stripe object API. The implementation of these models is based on that of [`dj-stripe`][] and [`pinax-stripe`][]
- COMP models that serve as proxies to the Stripe models and the `User` model.

**User**
- Save login information such as email, username, and password
  - Once the `django-allauth` plugin is swapped in, this will contain info to be used for linking to third party logins such as Gmail or GitHub accounts.

**Stripe**

Stripe's documentation is excellent, and thus, it will not be replicated here. The most relevant section of the documentation as it pertains to this project is the [billing walk-through][].

- `Product`: represents a project on the COMP platform
  - One-to-one relation with `Project`
- `Plan`: billing plan(s) attached to a `Product`
  - Foreign key to `Product`
  - All public models have a metered plan
- `Customer`: when a person signs up a Stripe `Customer` is created
  - One-to-one relation with user
- `Subscription`: attached to a customer when they subscribe to a plan
  - Foreign key to `Customer`
  - Many-to-many relation with `Plan`
    - a plan will have many subscriptions (everytime someone signs up they subscribe to at least one plan)
    - a subscription can be created from many plans
  - When a person signs up they are subscribed to a metered plan for each public project.
- `Subscription Item`: when a subscription is created from multiple plans a subscription item represents the subscription component for each plan
  - Foreign key to `Plan`
  - Foreign key to `Subscription`
- `UsageRecord`: created when reporting usage amounts for metered plans
  - Foreign key to `Subscription Item`
- `Event`: Stripe sends an `Event` to a [webhook][] every time we do an API call to Stripe or a billing event occurs.
  - Stripe recommends applications that utilize billing features implement webhooks for the following events:
    - invoice payment failures
    - tracking active subscriptions
    - subscription state changes
  - so far these events are handled:
    - `customer.created`
    - `payment.failure` (still needs work)
    - the remaining events will be implemented over the next week or so
  - Foreign key to Customer (coming soon)
  - Foreign key to Invoice (coming soon)
  - perhaps more
- `Invoice`: coming soon
  - One-to-one relation with `Charge`
  - Foreign key to Customer
  - Foreign key to Subscription
- `Charge`: coming soon

**COMP-related Models**

Proxy objects for storing data on projects and users.

- `Profile`: store data on users that is not directly relevant to login capabilities such as model runs and access parameters (e.g. public access granted or not)
  - One-to-one relation with `User`
- `Project`: store data on projects that is not directly relevant to Stripe `product` API such as name, server cost (subject to change dep. on metered plan implementation), project overview, etc.

[`AbstractUser`]: https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project
[`django-allauth`]: https://github.com/pennersr/django-allauth
[`dj-stripe`]: https://github.com/dj-stripe/dj-stripe
[`pinax-stripe`]: https://github.com/pinax/pinax-stripe
[billing walk-through]: https://stripe.com/docs/billing/quickstart
[webhook]: https://stripe.com/docs/billing/webhooks