from .models import Customer, Coupon, StoreSettings
from .sms import sending_sms_aws
from datetime import date, datetime, timedelta
from math import floor
import kronos

### Important:
#
# This module uses django-kronos package. See the documentation in: 
# https://github.com/jgorset/django-kronos
#
# It is necessary to update the cron registry to include a new function.
# Command: python manage.py installtasks
#
# To check registred tasks.
# Command: python manage.py showtasks
#
# To test a routine manually 
# Command: python manage.py runtask <function>
#
# Note: due to the use of a virtual environment, was necessary to include in 
# the app settings.py:
# KRONOS_PREFIX = 'source ...es_mvp_env/bin/activate &&'
#
###

# Runs everiday, 3:00AM.
@kronos.register('0 3 * * *')
def coupon_expiration_task():
    """Process expired coupons."""
    today = date.today()
    # Gets all valid, unredeemed and non-expired coupons.
    valid_coupons = Coupon.objects.filter(is_valid=True, is_redeemed=False, 
            is_expired=False)
    for coupon in valid_coupons:
        # If the coupon is expired, update its status.
        if coupon.expiration_date < today:
            coupon.is_expired = True
            coupon.save()
    ## TO-DO: to implement a logging registry to this task.
    return None

# Runs everiday, 8:00AM.
@kronos.register('0 8 * * *')
def coupon_activation_task():
    """
    Handle the coupon activation cycle.
    Currently this app only supports the sending activation messages by SMS with
    the AWS SNS API. The activation cycle comprehends 4 steps, sending a 
    specific message in each step. The first three steps are function of the 
    coupon added date. And the last step are related with the coupon expiration
    date.
    """

    today = date.today()
    # Gets all valid coupons, unredeemed, non-expired and not fully activated.
    non_activated_coupons = Coupon.objects.filter(is_redeemed=False, 
            is_expired=False, is_activated=False)
    for coupon in non_activated_coupons:
        # Gets the store settings and customer data to support message building.
        settings = StoreSettings.objects.get(store=coupon.store.id)
        customer = Customer.objects.get(id=coupon.sale.customer.id)
        # Converts a datetime object in a date object:
        trigger_date = date(coupon.date_added.year,
                    coupon.date_added.month, coupon.date_added.day)
        # The SMS recipient.
        cellphone = f"+{customer.cellphone}"
        ### First activation: if the coupon was issued 2 days ago.
        if today == (trigger_date + timedelta(days=2)):
            # Important: a SMS can have 140 ASCII characters. The variable part 
            # of this message takes until 61 chars. Thus, the static part of the 
            # string, including spaces and punctuation, must have 79 characters
            # or less.
            message = (f"You receive {settings.currency}" + 
                    f"{floor(coupon.discount_value)} of cashback " + 
                    f"on {settings.title}. Expires on " + 
                    f"{format(coupon.expiration_date.day,'02d')}" +
                    f".{format(coupon.expiration_date.month,'02d')}. Max " + 
                    f"discount {coupon.discount_limit_rate}%, not cumulative. " +
                    f"{coupon.campaign.url}")
            sending_sms_aws(cellphone, message)
            # Makes the coupon applicable.
            coupon.is_valid = True
            coupon.save()
        ### Second activation: if the coupon was issued 7 days ago.
        elif today == (trigger_date + timedelta(days=7)):
            # The static part of the string must be 79 characters or less.
            message = (f"You have {settings.currency}" + 
                    f"{floor(coupon.discount_value)} cashback to purchases on" +
                    f"{settings.title}. Expires on " + 
                    f"{format(coupon.expiration_date.day,'02d')}" +
                    f".{format(coupon.expiration_date.month,'02d')}. Max " + 
                    f"discount {coupon.discount_limit_rate}%, not cumulative. " +
                    f"{coupon.campaign.url}")
            sending_sms_aws(cellphone, message)
        ### Third activation: if the coupon was issued 27 days ago.
        elif today == (trigger_date + timedelta(days=27)):
            # The static part of the  string must be 79 characters or less.
            message = (f"Don't let cashback expire {settings.currency}" + 
                    f"{floor(coupon.discount_value)} for purchases on" +
                    f"{settings.title}. Expires on " + 
                    f"{format(coupon.expiration_date.day,'02d')}" +
                    f".{format(coupon.expiration_date.month,'02d')}. Max " + 
                    f"discount {coupon.discount_limit_rate}%, not cumulative. " +
                    f"{coupon.campaign.url}")
            sending_sms_aws(cellphone, message)
        ### Last activation: if the coupon has an expiration lifetime greater 
        ### than 35 days and there are only 3 days left before its expiration.
        elif (coupon.campaign.coupon_lifetime > 35) and (
                today == (coupon.expiration_date - timedelta(days=3))):
            # The static part of the  string must be 79 characters or less.
            message = (f"Expires in 3 days! Your cashback of {settings.currency}" + 
                    f"{floor(coupon.discount_value)} to use " + 
                    f"on {settings.title} expires in " + 
                    f"{format(coupon.expiration_date.day,'02d')}" +
                    f".{format(coupon.expiration_date.month,'02d')}. Max " + 
                    f"discount {coupon.discount_limit_rate}%, not cumulative. " +
                    f"{coupon.campaign.url}")
            sending_sms_aws(cellphone, message)
            # At the end, update the coupon status.
            coupon.is_activated = True
            coupon.save()
    ## TO-DO: to implement a logging registry to this task.
    return None
