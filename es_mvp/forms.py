from django import forms
from .models import Sale, Campaign, StoreSettings


### Sale form

class SaleForm(forms.ModelForm):

    ### Extra model fields

    # New customer registration (if applicable) always occurs simultaneously 
    # with sales registration. To avoid human errors when entering data, the 
    # form divides the customer's cell phone data into three fields.
    customer_country_code = forms.CharField(max_length=3, 
            label="Country code (only numbers)")
    customer_long_distance_code = forms.CharField(max_length=3, 
            label="Long distance code (only numbers)")
    customer_cellphone = forms.CharField(max_length=10, 
            label="Mobile phone (only numbers)")
    # Supports the customer validation.
    customer_verified = forms.BooleanField(
            required=False,
            label=("First time registered customer." + 
                    " It is necessary to validate the customer's cell phone!"))
    # A hidden field to supports the 'new sale' function flow.
    ns_control_flag = forms.BooleanField(widget=forms.HiddenInput())

    class Meta:
        model = Sale
        # Note:  some model fields are not included.
        fields = [
                'initial_value',
                'date',
                'redeemed_coupon',
                'identifier',
                ]
        labels = {
                'initial_value' : 'Sale value',
                'date' : 'Sale date',
                'redeemed_coupon' : 'Choose a coupon to redeem',
                'identifier' : 'Sale ID',
                }
        widgets = {
                'redeemed_coupon': forms.RadioSelect(),
                }
                

### Campaign form

class CampaignForm(forms.ModelForm):
  class Meta:
        model = Campaign
        fields = [
                'title',
                'url',
                'min_sale_value',
                'max_sale_value',
                'bonus_rate',
                'discount_limit_rate',
                'coupon_lifetime',
                'is_active',
                ]
        labels = {
                'title' : 'Title',
                'min_sale_value' : 'Minimum sale value (greater than or equal to)',
                'max_sale_value' : 'Maximum sale value (less than or equal to)',
                'url' : 'Shortened link to include in the coupon',
                'bonus_rate' : 'Cashback rate (on %)',
                'discount_limit_rate' : 
                        'Maximum discount on coupon redemption (on %)',
                'coupon_lifetime' : 
                        'Coupon expiration (in days from issuance)',
                'is_active' : 'Keep active',
                }


### Store settings form

class StoreSettingsForm(forms.ModelForm):
  class Meta:
        model = StoreSettings
        fields = [
                'title',
                'country_code',
                'long_distance_code',
                'currency',
                'url',
                'bonus_rate',
                'discount_limit_rate',
                'coupon_lifetime',
                ]
        labels = {
                'title' : 'Store name',
                'country_code' : 'Country code (only numbers)',
                'long_distance_code' : 'Long distance code (only numbers)',
                'currency' : 'Currency',
                'url' : 'Link to SMS message',
                'bonus_rate' : 'Standard cashback rate (on %)',
                'discount_limit_rate' : 'Standard maximum discount (on %)',
                'coupon_lifetime' : 
                    'Standard coupon expiration (in days from issuance)',
                }
                
