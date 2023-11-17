from django.db import models
from django.contrib.auth.models import User
from django.db.models import CheckConstraint, Q, F
from django.core.validators import MinValueValidator, URLValidator
from .validators import validate_sale_date
from datetime import date, timedelta


### ES Minimum Viable Product App
#
# This app models a sale incentive program that rewards customers that 
# originated a recent sale with a cashback coupon, redeemable on a new sale. The
# goal is to make 1 in 10 customers return (before the average repurchase 
# period) to generate a new sale with a value close the original purchase.
#
# The ordinary app user is a "store". It is a flexible concept that can 
# represent a single store, an autonomous salesperson, a retail chain with many
# stores or even an e-commerce. A store owns (and only sees and manages) its 
# sales, customers, campaigns and respective coupons.
#
# Therefore a sale is the trigger to bonify customers. Each new registered sale 
# can issue (if eligible) a single new coupon to be redeemed at the same store 
# as the original purchase. 
#
# A coupon has an expiration date, a face value and its specific redemption 
# conditions. Although is possible for a customer to accumulate many coupons for
# the same store, only one coupon can be redeemed in a future new sale.
#
# The eligibility and usage conditions for coupons are defined by campaigns. A 
# store can have more than one campaign active at a given time, but only the one
# that is applicable and has the highest cashback rate – is considered when 
# issuing the coupon.
#
###


class Customer(models.Model):
    """
    Model a customer. 
    """
    store = models.ForeignKey(User, on_delete=models.PROTECT)
    # The customer's complete cellphone number (ex. 55119999999), including the
    # country and long distance codes.
    cellphone = models.CharField(max_length=16)
    is_verified = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        To display customer objects in the admin panel or the Django shell.
        """
        customer = (f"Store: {self.store.storesettings.title} -- " + 
                    f"Cellphone: {self.cellphone} -- " + 
                    f"Verified: {self.is_verified}")       
        return customer


class Sale(models.Model):
    """
    Model a sale event.
    """
    # Note: this project adopts the built-in 'User' model from Django Framework. 
    store = models.ForeignKey(User, on_delete=models.PROTECT)
    # The related customer.
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    # Initial sale value provided from the POS (Point-of-Sale appliance).
    initial_value = models.FloatField(validators=[MinValueValidator(0.0)])
    # Effective discount earned by a coupon redemption. Note, it is different 
    # from the coupon face value ('coupon.discount_value'), because the coupon 
    # can have a maximum discount limit.
    effective_discount = models.FloatField(validators=[MinValueValidator(0.0)])
    # Final value of the sale after applying the cashback.
    # Is calculated by: 'pos_initial_value' - 'discount_value'.
    final_value = models.FloatField(validators=[MinValueValidator(0.0)])
    # A optional redeemed coupon.
    # Note: (i) The class name is provided as a string because Coupon class not 
    # yet been defined; (ii) It is necessary to declare a "related name" 
    # parameter to resolve the reverse relationship with the Coupon class and
    # avoid a conflit with 'Coupon.sale' attribute.
    redeemed_coupon = models.OneToOneField("Coupon", on_delete=models.PROTECT,
            blank=True, null=True, related_name='redeemed_coupon')
    # A sale identifier provided from POS. Can be a invoice number or any sale 
    # control id from the POS. The purpose of this field is avoid possible fraud
    # by coupon issuance without a corresponding original sale.
    identifier = models.CharField(max_length=12, blank=True)
    # Each new sale is initaly recorded as "not evaluated" for the coupon 
    # issuance. Immediately after its registration, the sale eligibility for any
    # active campaign is tested and, if applicable, a new coupon is issued. 
    # Thus, the status changes to "evaluated".
    is_evaluated = models.BooleanField(default=False)
    # Date of sale transaction. It determines the lifetime of an issued coupon.
    date = models.DateField(validators=[validate_sale_date])
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            # For checking and maintain the DB integrity.
            CheckConstraint(
                check=Q(initial_value__gte=0.0),
                        name='sale_initial_value_min'),
            CheckConstraint(
                check=Q(effective_discount__gte=0.0),
                        name='sale_effective_discount_min'),
            CheckConstraint(
                check=Q(final_value__gte=0.0),
                        name='sale_final_value_min'),
            CheckConstraint(
                check=Q(final_value__exact=(
                        F("initial_value") - F("effective_discount"))),
                        name='sale_final_value_conciliation',
                violation_error_message=('Final value must be equal to ' + 
                        'the sales value minus the discount applied.')),
            # For fraud control, only is possible to record sales with a 
            # transaction date from 15 days ago to one day ahead, considering 
            # the registration date of the sale.
            CheckConstraint(
                check=Q(date__gte=(F("date_added") - timedelta(days=15))),
                        name='sale_date_limit_min'),
            CheckConstraint(
                check=Q(date__lte=(F("date_added") + timedelta(days=1))),
                        name='sale_date_limit_max'),
        )

    def __str__(self):
        """
        To display sale objects in the admin panel or the Django shell.
        """
        sale = (f"Store: {self.store} -- " +
                f"Customer: {self.customer.cellphone} -- " +
                f"Sale ID: {self.identifier} -- " + 
                f"Date: {self.date} -- " + 
                f"Value: {self.final_value} -- " + 
                f"Evaluated: {self.is_evaluated}" 
                )        
        return sale


class Campaign(models.Model):
    """
    Model an incentive campaign.
    """
    store = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=60)
    ### Eligibility conditions to new sale evaluation. 
    # This rules are applied to the final sale value.
    min_sale_value = models.FloatField(validators=[MinValueValidator(0.0)])
    max_sale_value = models.FloatField(validators=[MinValueValidator(0.0)])
    ### Definitions to coupon issuance.
    # An URl to include in activation messages.
    url = models.CharField(max_length=20, blank=True, 
            validators=[URLValidator()])
    # Note: all percentage rates are stored as a integer and will be divided by 
    # 100 when used in calculations.
    bonus_rate = models.IntegerField(validators=[MinValueValidator(0)])
    # A percentage discount limit to be applied at the coupon redemption to
    # incentive a new sale's final value close to the value of the last recent 
    # purchase.
    discount_limit_rate = models.IntegerField(validators=[MinValueValidator(0)])
    # A coupon lifetime in days. The minimum lifetime is 5 days.
    coupon_lifetime = models.IntegerField(validators=[MinValueValidator(5)])
    ### Campaign status.
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            # For checking and maintain the DB integrity.
            CheckConstraint(
                check=Q(min_sale_value__gte=0.0),
                name='campaign_min_sale_value_min'),
            CheckConstraint(
                check=Q(max_sale_value__gte=0.0),
                name='campaign_max_sale_value_min'),
            # Checks if min_sale_value < max_sale_value.
            CheckConstraint(
                check=Q(max_sale_value__gte=F("min_sale_value")),
                name='campaign_max_min_sale_value_test',
                violation_error_message=('Maximum purchase amount must be ' + 
                        'greater than minimum purchase amount.')),
            CheckConstraint(
                check=Q(bonus_rate__gte=0),
                name='campaign_bonus_rate_min'),
            CheckConstraint(
                check=Q(discount_limit_rate__gte=0),
                name='campaign_discount_limit_rate_min'),
            # The minimum lifetime is 5 days.
            CheckConstraint(
                check=Q(coupon_lifetime__gte=5),
                name='campaign_coupon_lifetime_min'),
        )

    def __str__(self):
        """
        To display campaign objects in the admin panel or the Django shell.
        """
        campaign = (f"Store: {self.store.storesettings.title} -- " +
                f"Title: {self.title[:20]} -- " + 
                f"Bonus %: {self.bonus_rate} -- " + 
                f"Active: {self.is_active}"
                )   
        return campaign


class Coupon(models.Model):
    """
    Model a bonus coupon.
    """
    store = models.ForeignKey(User, on_delete=models.PROTECT)
    # The sale that originated this coupon.
    sale = models.OneToOneField(Sale, on_delete=models.PROTECT)
    # The campaign that define this coupon conditions.
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT)
    # The customer that initiates the sale. This FK is useful for looking for 
    # coupons for a specific customer.
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    # A random alphanumeric code with 6 characters to identify coupons in human-
    # oriented interfaces.
    identifier = models.CharField(max_length=6)
    ### Specifications defined by the campaign rules.
    # The 'Coupon.discount_value' is rounded up to a "integer" float number (ex: 
    # $233.33 will be $234) for better usability and is calculated by: 
    # ceil('sale.final_value' * 'campaign.bonus_rate')
    discount_value = models.FloatField()
    # Note: all percentage rates are stored as a integer and will be divided by 
    # 100 when used in calculations.
    discount_limit_rate = models.IntegerField()
    # Expiration is calculated by:
    # 'Sale.added_date' + timedelta(Campaign.coupon_lifetime)
    expiration_date = models.DateField()
    # To control if coupon was redeemed.
    is_redeemed = models.BooleanField(default=False)
    # To control if coupon was expired.
    is_expired = models.BooleanField(default=False)
    # To control if coupon activated cycle was completed (that is, if all 
    # activation message was sent).
    is_activated = models.BooleanField(default=False)
    # To control if coupon is valid (the same as applicable). A coupon becomes 
    # valid from the first activation message delivery (~2 days from the 
    # added_date).
    is_valid = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        To display coupon objects in the admin panel or the Django shell.
        """
        if self.is_redeemed:
            coupon_status = "redeemed"
        elif self.is_expired:
            coupon_status = "expired"
        elif self.is_valid:
            coupon_status = "valid"
        else:
            coupon_status = "invalid"
        coupon = (f"Store: {self.store.storesettings.title} -- " +
                f"Sale: {self.sale.identifier} -- " +
                f"Customer: {self.customer.cellphone} -- " +
                f"ID: {self.identifier} -- " +
                f"Value: {self.discount_value} -- " + 
                f"Expiration: {self.expiration_date} -- " + 
                f"Status: {coupon_status}"
                )
        return coupon


class StoreSettings(models.Model):
    """
    Model the store settings. This is an extension of the User (store) model.
    """
    store = models.OneToOneField(User, on_delete=models.PROTECT)
    # A short title to refer to a store. The strict characters limit is due its 
    # applying in the activation messages.
    title = models.CharField(max_length=25, blank=True)
    # A standard currency definition for the entire application.
    currency = models.CharField(max_length=3)
    ### Default customer cellphone info to pre-fill the 'new sale' form.
    country_code = models.CharField(max_length=3)
    long_distance_code = models.CharField(max_length=3)
    ### Default campaign data to pre-fill the 'new campaign' form.
    url = models.CharField(max_length=20, blank=True, 
            validators=[URLValidator()])
    # Note: all percentage rates are stored as a integer and will be divided by 
    # 100 when used in calculations.
    bonus_rate = models.IntegerField(validators=[MinValueValidator(0)])
    discount_limit_rate = models.IntegerField(
            validators=[MinValueValidator(0)])
    # Default coupon lifetime in days.
    coupon_lifetime = models.IntegerField(validators=[MinValueValidator(5)])
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta: 
        verbose_name_plural = 'store settings'
        constraints = (
            # For checking and maintain the DB integrity.
            CheckConstraint(
                check=Q(bonus_rate__gte=0),
                name='store_settings_bonus_rate_min'),
            CheckConstraint(
                check=Q(discount_limit_rate__gte=0),
                name='store_settings_discount_limit_rate_min'),
            # The minimum lifetime is 5 days.
            CheckConstraint(
                check=Q(coupon_lifetime__gte=5),
                name='store_settings_coupon_lifetime_min'),
        )

    def __str__(self):
        """
        To display store settings objects in the admin panel or Django shell.
        """
        store_settings = (f"Owner: {self.owner} --  Added: {self.date_added}")       
        return store_settings

 