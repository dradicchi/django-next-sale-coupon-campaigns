from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import Http404
from .models import Customer, Sale, Campaign, Coupon, StoreSettings
from .forms import SaleForm, CampaignForm, StoreSettingsForm
from .sms import sending_sms_aws
from datetime import date, datetime, timedelta
from math import ceil
import secrets, re



### Home view functions

def home(request):
    """The home page."""
    try:
        settings = StoreSettings.objects.get(store=request.user)
    except:
        context = {'store_summary' : False, 
                'settings' : False, 
                }
    else:
        # Summarizes only incentived sales. Returns a dict.
        cumulative_sales = Sale.objects.filter(
                store=request.user).exclude(redeemed_coupon=None).aggregate(
                Sum('final_value', default=0.00))
        # Summarizes the cashback given. Returns a dict.
        cumulative_cashback = Coupon.objects.filter(
            store=request.user, is_redeemed=True).aggregate(
            Sum('discount_value', default=0.00))
        # A store summary.
        store_summary = {
            'cumulative_sales' : cumulative_sales['final_value__sum'],
            'cumulative_cashback' : cumulative_cashback['discount_value__sum'],
            'redeemed_coupons' : 
                    Coupon.objects.filter(
                            store=request.user, is_redeemed=True).count(),
            'issued_coupons' : 
                    Coupon.objects.filter(
                            store=request.user, is_valid=True).count(),
            'expired_coupons' : 
                    Coupon.objects.filter(
                            store=request.user, is_expired=True).count(),
            }
        try:
            # Handles zero division.
            store_summary['conversion_rate'] = (
                store_summary['redeemed_coupons'] / 
                store_summary['issued_coupons'])
        except:
            store_summary['conversion_rate'] = None
        context = {'store_summary' : store_summary, 
                'settings' : settings, 
                }
    return render(request, 'es_mvp/home.html', context)


### Sale view functions

@login_required
def sales(request):
    """List all sales for a store."""
    settings = StoreSettings.objects.get(store=request.user)
    sales = Sale.objects.filter(store=request.user).order_by('-date')
    paginator = Paginator(sales, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {'sales' : sales, 'settings' : settings, 'page_obj' : page_obj}
    return render(request, 'es_mvp/sales.html', context)


@login_required
def sale(request, sale_id):
    """Show details for a sale."""
    sale = Sale.objects.get(id=sale_id)
    # Makes sure the sale belongs to the current store.
    check_content_owner(request, sale)
    settings = StoreSettings.objects.get(store=request.user)
    # If applicable, gets the coupon issued from this sale.
    # Note: Django 'get()' method needs exception handling.
    try:
        issued_coupon = Coupon.objects.get(sale=sale.id)
    except:
        issued_coupon = None
    context = {'sale' : sale, 'issued_coupon' : issued_coupon, 
            'settings' : settings}
    return render(request, 'es_mvp/sale.html', context)


@login_required
def new_sale(request):
    """
    Add a new sale.
    To deal with a 'new sale' recording, this function adopts a recursive 
    approach, repeatedly self-reloading and routing its flow through conditional 
    alternative clauses. 
    """
    # Gets default data to fill a 'new sale' form.
    settings = StoreSettings.objects.get(store=request.user)
    ### At the first call function, no POST data has been sent yet. So, it 
    # creates a form object, fills some initial data and renders a blank 'new 
    # sale' page.
    if request.method != 'POST':
        form = SaleForm(
            initial={
                'customer_country_code' : settings.country_code,
                'customer_long_distance_code' : settings.long_distance_code,
                'initial_value' : 0.00,
                'date' : date.today(),
                # Sets control flow as 'False'.
                'applicable_coupons_control' : False,
            },
            label_suffix="")
        form.fields['initial_value'].label_suffix = f" {settings.currency}"
    ### POST data was submitted. Now, the function flow handles data through 
    # three alternative branches: (1) If there is a new user; (2) If they are a 
    # previous user, with applicable coupons; (3) If they are a previous user, 
    # without applicable coupons. At the end, all entries are processed in a 
    # last common branch. 
    else:
        form = SaleForm(data=request.POST)
        ### Gets the customer (if exists).
        c_country_code = form['customer_country_code'].value()
        c_long_distance_code = form['customer_long_distance_code'].value()
        c_cellphone = form['customer_cellphone'].value()
        customer_cellphone = clean_phone_number(c_country_code + 
            c_long_distance_code + c_cellphone)
        # Note: Django 'get()' method needs exception handling.
        try:
            customer = Customer.objects.get(cellphone=customer_cellphone)
        except:
            customer = None
        ### First alternative branch: If there is a new customer, thus validates
        # their data and registers them.
        if not customer:
            # Validates the customer cellphone. This sub-branch will be called 
            # recursively until the data was validated
            if not form['customer_verified'].value():
                form = SaleForm(
                    initial={
                    'customer_country_code' : 
                            form['customer_country_code'].value(),
                    'customer_long_distance_code' : 
                            form['customer_long_distance_code'].value(),
                    'customer_cellphone' : form['customer_cellphone'].value(),
                    'initial_value' : form['initial_value'].value(),
                    'date' : form['date'].value(),
                    },
                    label_suffix="")
                form.fields['initial_value'].label_suffix = f" {settings.currency}"
                # Sends a validation code to the customer.
                validation_code = cellphone_code_validation(customer_cellphone)
                # Reloads new sale page with all new data. The 'new sale' form 
                # will display the validation code and asks the user to confirm 
                # this with the customer.
                context = {'form': form, 'validation_code' : validation_code}
                return render(request, 'es_mvp/new_sale.html', context)  
            # When data customer was validated.
            else:
                # The 'ns_control_flag' hidden field permits that function flow 
                # reaches the last common branch and concludes the new sale 
                # processing. To update the status of 'ns_control_flag', it is 
                # necessary to reinstantiate the all form.
                form = SaleForm(
                    initial={
                    'customer_country_code' : 
                            form['customer_country_code'].value(),
                    'customer_long_distance_code' : 
                            form['customer_long_distance_code'].value(),
                    'customer_cellphone' : form['customer_cellphone'].value(),
                    'initial_value' : form['initial_value'].value(),
                    'date' : form['date'].value(),
                    'ns_control_flag' : True
                    },
                    label_suffix="")
                form.fields['initial_value'].label_suffix = f" {settings.currency}"
                # Creates and saves a new customer.
                customer = Customer.objects.create(
                    store=request.user, cellphone=customer_cellphone, 
                    is_verified=True)
                # Reloads new sale page with all new data. The 'new sale' form 
                # will ask about the 'new_sale.identifier' and, when submitted, 
                # will conclude the new sale processing.
                context = {'form': form}
                return render(request, 'es_mvp/new_sale.html', context)  
        # If they are a previous user but coupons availability was not checked.
        elif customer and not form['ns_control_flag'].value():
            # Searches for all valid, unredeemed, and non-expired coupons for the 
            # customer. If there are applicable coupons, sort them in descending
            # order.
            applicable_coupons = Coupon.objects.filter(store=request.user, 
                    customer=customer, is_redeemed=False, is_expired=False, 
                    is_valid=True).order_by('-discount_value') 
            ### Second alternative branch: The previous user has applicable 
            # coupons. Thus, handles with a possible (optional) coupon 
            # redemption.
            if applicable_coupons:
                # The 'ns_control_flag' hidden field permits that function flow 
                # reaches the last common branch and concludes the new sale 
                # processing. To update the status of 'ns_control_flag', it is 
                # necessary to reinstantiate the all form.
                form = SaleForm(
                    initial={
                    'customer_country_code' : 
                            form['customer_country_code'].value(),
                    'customer_long_distance_code' : 
                            form['customer_long_distance_code'].value(),
                    'customer_cellphone' : form['customer_cellphone'].value(),
                    'initial_value' : form['initial_value'].value(),
                    'date' : form['date'].value(),
                    'ns_control_flag' : True,
                    },
                    label_suffix="")
                form.fields['initial_value'].label_suffix = f" {settings.currency}"
                ### Builds an applicable coupons choice list for a RadioSelect 
                # fieldset. The first item on the list is 'None', a scenario 
                # where no coupons are redeemed.
                coupon_choices = [(None,"Não resgatar cupom para esta compra")]
                # Each option contains useful information for choosing a coupon.
                for coupon in applicable_coupons:
                    # Calculates the effective discount.
                    discount = sale_effective_discount(
                            float(form['initial_value'].value()), 
                            coupon.discount_value, 
                            coupon.discount_limit_rate)
                    # Calculates the final discounted value.
                    final_value = (float(form['initial_value'].value()) - 
                            discount)
                    # Builds the choice item.
                    choice = (coupon.id, (
                        f"Cupom ID: {coupon.identifier} --- " + 
                        f"Cashback: {settings.currency} {discount} --- " + 
                        f"Valor final: {settings.currency} {final_value}"
                        ))
                    coupon_choices.append(choice)
                form.fields['redeemed_coupon'].choices = coupon_choices
                # Reload the new sales page with all new data. The 'new sale' 
                # form displays all applicable coupons and will ask about an 
                # optional coupon redemption. When submitted, it will complete 
                # the processing of the new sale.
                context = {'form': form, 
                        'applicable_coupons' : applicable_coupons}
                return render(request, 'es_mvp/new_sale.html', context)
            ### Third alternative branch: The previous user does not have any
            # applicable coupons.
            else:
                # The 'ns_control_flag' hidden field permits that function flow 
                # reaches the last common branch and concludes the new sale 
                # processing. To update the status of 'ns_control_flag', it is 
                # necessary to reinstantiate the all form.
                form = SaleForm(
                    initial={
                    'customer_country_code' : 
                            form['customer_country_code'].value(),
                    'customer_long_distance_code' : 
                            form['customer_long_distance_code'].value(),
                    'customer_cellphone' : form['customer_cellphone'].value(),
                    'initial_value' : form['initial_value'].value(),
                    'date' : form['date'].value(),
                    'ns_control_flag' : True,
                    },
                    label_suffix="")
                form.fields['initial_value'].label_suffix = f" {settings.currency}"
                # To displays a "there are not applicable coupons" message.
                not_applicable_coupons = True
                # Reloads new sale page with all new data. The 'new sale' 
                # form displays a "there are not applicable coupons" message. 
                # When submitted, it will complete the processing of the 
                # new sale.
                context = {'form': form, 
                        'not_applicable_coupons' : not_applicable_coupons}
                return render(request, 'es_mvp/new_sale.html', context)  
        ### The final common branch. Here, there are three important steps: (A)
        # tests all data entries; (B) Handles an optional redeemed coupon; (C) 
        # Registry the proper new sale; and (D) If new sale is eligible, issues 
        # a new related coupon.
        else:
            ### (A) Tests all data entries;
            if form.is_valid():
                # Saves a "raw" version from the form.
                new_sale = form.save(commit=False)
                ### (B.1) If applicable, handles the redeemed coupon.
                try:
                    redeemed_coupon = Coupon.objects.get(
                            id=form['redeemed_coupon'].value())
                except:
                    redeemed_coupon = None
                # Calculates 'effective_discount' and the 'final_value'.
                if not redeemed_coupon:
                    effective_discount = 0.00
                    final_value = form['initial_value'].value()
                else: 
                    effective_discount = sale_effective_discount(
                        float(form['initial_value'].value()), 
                        redeemed_coupon.discount_value, 
                        redeemed_coupon.discount_limit_rate)
                    final_value = (float(form['initial_value'].value()) - 
                            effective_discount)
                ### (C) Completes and saves the new sale.
                new_sale.store = request.user
                new_sale.customer = customer
                new_sale.effective_discount = effective_discount
                new_sale.final_value = final_value
                new_sale.redeemed_coupon = redeemed_coupon
                new_sale.save()
                ### (B.2) Updates the status of the redemeed coupon.
                if redeemed_coupon:
                    redeemed_coupon.is_redeemed = True
                    redeemed_coupon.save()
                ### (D) Evaluates the sale eligibility and, case positive, 
                # issues a new coupon.
                evaluate_for_coupon(new_sale.id)
                # At the final, redirects to new sale detail page.
                messages.success(request, "Venda registrada com sucesso.", 
                    extra_tags='alert alert-success alert-dismissible fade show')
                return redirect('es_mvp:sale', new_sale.id)
    # Note, this 'return' can be output to two alternative flows: (1) A first 
    # call to this view function, without a POST submission; or (2) A POST 
    # submission that failed the 'is_valid()' test. 
    context = {'form': form}
    return render(request, 'es_mvp/new_sale.html', context)


### Campaign view functions

@login_required
def campaigns(request):
    """List all campaigns for a store."""
    settings = StoreSettings.objects.get(store=request.user)
    campaigns = Campaign.objects.filter(
            store=request.user).order_by('-date_added')
    paginator = Paginator(campaigns, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {'campaigns' : campaigns, 'settings' : settings, 
            'page_obj' : page_obj}
    return render(request, 'es_mvp/campaigns.html', context)


@login_required
def campaign(request, campaign_id):
    """Show details for a campaign."""
    campaign = Campaign.objects.get(id=campaign_id)
    # Makes sure the campaign belongs to the current store.
    check_content_owner(request, campaign)
    settings = StoreSettings.objects.get(store=request.user)
    ### Summarizes only incentived sales. 
    # Gets campaign's redeemed coupons.
    c_redeemed_coupons =  Coupon.objects.filter(
            campaign=campaign.id, is_redeemed=True)
    # Gets all incentived sales.
    incentived_sales = Sale.objects.filter(
            store=request.user).exclude(redeemed_coupon=None)
    campaign_incentived_sales = []
    for sale in incentived_sales:
        for coupon in c_redeemed_coupons:
            if sale.redeemed_coupon.id == coupon.id:
                campaign_incentived_sales.append(sale.final_value)
    cumulative_sales = sum(campaign_incentived_sales)
    # Summarizes the cashback given. Returns a dict.
    cumulative_cashback = Coupon.objects.filter(
        campaign=campaign.id, is_redeemed=True).aggregate(
        Sum('discount_value', default=0.00))

    campaign_summary = {
        'cumulative_sales' : cumulative_sales,
        'cumulative_cashback' : cumulative_cashback['discount_value__sum'],
        'redeemed_coupons' : 
                Coupon.objects.filter(
                        campaign=campaign.id, is_redeemed=True).count(),
        'issued_coupons' : 
                Coupon.objects.filter(
                        campaign=campaign.id, is_valid=True).count(),
        'expired_coupons' : 
                Coupon.objects.filter(
                        campaign=campaign.id, is_expired=True).count(),
        }
    try:
        # Handles zero division.
        campaign_summary['conversion_rate'] = (
            campaign_summary['redeemed_coupons'] / 
            campaign_summary['issued_coupons'])
    except:
        campaign_summary['conversion_rate'] = None
    context = {'campaign' : campaign, 'campaign_summary' : campaign_summary,
            'settings' : settings}
    return render(request, 'es_mvp/campaign.html', context)


@login_required
def new_campaign(request):
    """Add a new campaign."""
    # Gets default data to build a campaign.
    settings = StoreSettings.objects.get(store=request.user)
    if request.method != 'POST':
        # No data submitted; Creates a blank form with some initial data.
        form = CampaignForm(
            initial={
                'url' : settings.url,
                'min_sale_value' : 0.00,
                # To ensure campaign-sale matching.
                'max_sale_value' : 100000.00,
                'bonus_rate' : settings.bonus_rate,
                'discount_limit_rate' : settings.discount_limit_rate,
                'coupon_lifetime' : settings.coupon_lifetime,
            })
    else:
        # POST request submitted; Deals with its data.
        form = CampaignForm(data=request.POST)
        if form.is_valid():
            new_campaign = form.save(commit=False)
            # Assigns the store owner and save.
            new_campaign.store = request.user
            new_campaign.save()
            # After saving the submitted data, redirects to the campaign list.
            messages.success(request, "Campanha criada com sucesso.", 
                    extra_tags='alert alert-success alert-dismissible fade show')
            return redirect('es_mvp:campaigns')
    # Displays a blank or invalid form.
    context = {'form': form}
    return render(request, 'es_mvp/new_campaign.html', context)


@login_required
def edit_campaign(request, campaign_id):
    """Edit a campaign."""
    
    campaign = Campaign.objects.get(id=campaign_id)
    # Makes sure the campaign belongs to the current store.
    check_content_owner(request, campaign)   
    settings = StoreSettings.objects.get(store=request.user)
    if request.method != 'POST':
        # Initial request; Pre-fills form with the current campaign.
        form = CampaignForm(instance=campaign)
        form.fields['min_sale_value'].label_suffix = f" {settings.currency}:"
        form.fields['max_sale_value'].label_suffix = f" {settings.currency}:"
    else:
        # POST request submitted; Deals with its data.
        form = CampaignForm(instance=campaign, data=request.POST)
        if form.is_valid():
            form.save()
            # Saves the updated data, and redirects to the campaign detail page.
            messages.success(request, "Campanha editada com sucesso.", 
                    extra_tags='alert alert-success alert-dismissible fade show')
            return redirect('es_mvp:campaign', campaign_id)
    # Displays a filled (current data) or invalid form.
    context = {'form': form, 'campaign' : campaign}
    return render(request, 'es_mvp/edit_campaign.html', context)


### Coupon view functions

@login_required
def coupons(request):
    """List all coupons for a store."""
    settings = StoreSettings.objects.get(store=request.user)
    # Gets the paramters to filter.
    customer_id = request.GET.get('customer_id', None)
    if customer_id:
        coupons = Coupon.objects.filter(
                store=request.user, customer=customer_id).order_by(
                '-date_added')
    else:
        coupons = Coupon.objects.filter(
                store=request.user).order_by('-date_added')
    paginator = Paginator(coupons, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {'coupons' : coupons, 'settings' : settings, 
            'page_obj' : page_obj}
    return render(request, 'es_mvp/coupons.html', context)


@login_required
def coupon(request, coupon_id):
    """Show details for a coupon."""
    coupon = Coupon.objects.get(id=coupon_id)
    # Makes sure the coupon belongs to the current store.
    check_content_owner(request, coupon)
    settings = StoreSettings.objects.get(store=request.user)
    # Gets the sale that originated the coupon issuance.
    origination_sale = Sale.objects.get(id=coupon.sale.id)
    # If applicable, gets the sale where this coupon was redeemed.
    # Note: Django 'get()' method needs exception handling.
    try:
        bonified_sale = Sale.objects.get(redeemed_coupon=coupon.id)
    except:
        bonified_sale = None
    context = {'coupon' : coupon,
            'origination_sale' : origination_sale,
            'bonified_sale' : bonified_sale,
            'settings' : settings}
    return render(request, 'es_mvp/coupon.html', context)


### Store settings view functions

@login_required
def edit_store_settings(request):
    """
    Edit the default store settings. 
    Note that StoreSettings model extends the User model in an one-to-one 
    relationship, so each store (the user object) is related to only one store
    settings record.
    """
    # Retrieves the store settings.
    store_settings = StoreSettings.objects.get(store=request.user)
    if request.method != 'POST':
        # It is initial request; Pre-fills the form with the current store 
        # settings data.
        form = StoreSettingsForm(instance=store_settings)
    else:
        # POST request submitted; Deals with its data.
        # Fill all new data in the form and complete the remaining fields with
        # the current data.
        form = StoreSettingsForm(instance=store_settings, data=request.POST)
        if form.is_valid():
            form.save()
            # After saving data, redirects to home.
            messages.success(request, 
                    "Configurações da loja atualizadas com sucesso.", 
                    extra_tags='alert alert-success alert-dismissible fade show')
            return redirect('es_mvp:edit_store_settings')
    # Displays a filled (current data) or invalid form.
    context = {'form': form, 'store_settings' : store_settings}
    return render(request, 'es_mvp/edit_store_settings.html', context)


### Backoffice functions

### Note: the handling of expired coupons, as well as the activation message
### sending service are implemented as cronjob tasks. See 'es_mvp/cron.py.

def evaluate_for_coupon(sale_id):
    """
    Evaluate a new sale object and issue a coupon if eligible.
    The coupon issuance is a concomitant process with new sale registration. 
    This backoffice function checks whether a sale matches the conditions of an 
    active campaign and, if so, uses this campaign's settings to issue a new 
    coupon.
    """
    # Gets the new sale.
    new_sale = Sale.objects.get(id=sale_id)
    # Sorts campaigns by the highest bonus rate. Thus, if there is more than one
    # campaign that matches the sale, choose the one with the highest bonus 
    # rate.
    active_campaigns = Campaign.objects.filter(
            store=new_sale.store.id, is_active=True).order_by('-bonus_rate')
    # Checks if there are active campaigns.
    if active_campaigns:
        for campaign in active_campaigns:
            # If new sale matches with the campaign. Currently, the campaign 
            # instances has only eligibilty criteria associated with the range 
            # of sale final value.
            if ((new_sale.final_value >= campaign.min_sale_value) and
                    (new_sale.final_value <= campaign.max_sale_value)):
                # Thus, creates and saves a new coupon. 
                # Note: The Django 'create()' method instantiates and saves a 
                # model object.
                new_coupon = Coupon.objects.create(
                        store=new_sale.store,
                        sale=new_sale,
                        campaign=campaign,
                        customer= new_sale.customer,
                        identifier=coupon_identifier(),
                        discount_value=coupon_discount_value(
                                new_sale.final_value, 
                                campaign.bonus_rate),
                        discount_limit_rate=campaign.discount_limit_rate,
                        expiration_date=(date.today() + timedelta(
                                days=campaign.coupon_lifetime)),
                        )
                # Updates the new sale status to evaluated and returns the 
                # corresponding new coupon.
                new_sale.is_evaluated = True
                new_sale.save()
                return new_coupon
            else:
                new_coupon = None 
    else:
        new_coupon = None 
    # Case there aren't active campaigns or the sale does not match any 
    # campaign, updates the sale status to evaluated and returns 'None'.
    new_sale.is_evaluated = True
    new_sale.save()
    return new_coupon


def coupon_discount_value(sale_final_value, campaign_bonus_rate):
    """
    Calculate the 'coupon.discount_value' attribute when issuing a coupon.
    To a better usability, coupons must have an "integer" float discount value, 
    rounded up if needed. For instance, a raw coupon calculation of $233.12 must
    be rounded up $234 (and not $233) as well as is expected that a $478.94 
    result must be rounded up to $479.
    """
    coupon_discount_value = float(ceil(sale_final_value * 
            (campaign_bonus_rate / 100)))
    return coupon_discount_value


def sale_effective_discount(sale_initial_value, coupon_discount_value, 
        coupon_discount_limit_rate):
    """
    Calculate the effective discount when applying a coupon on a new sale.
    The real discount must be equal to or less than the maximum discout allowed.
    """
    max_discount = float(
            ceil(sale_initial_value * (coupon_discount_limit_rate / 100.0)))
    if coupon_discount_value > max_discount:
        effective_discount = max_discount
    else:
        effective_discount = coupon_discount_value
    return effective_discount

def coupon_identifier():
    """Generate a random alfanumeric string code with lenght=6'."""
    code = ''.join(secrets.choice('0123456789ABCDEF') for i in range(6))
    return code


def initial_store_settings(store_id):
    """
    Generate an initial store settings configuration. This function supports the
    new user (store) registration.
    """
    store = User.objects.get(id=store_id)
    store_settings = StoreSettings.objects.create(
            store=store,
            title='',
            country_code="55",
            long_distance_code="11",
            currency="R$",
            url='',
            bonus_rate=20,
            discount_limit_rate=30,
            coupon_lifetime=45,
            )
    # Return the new object.
    return store_settings


def cellphone_code_validation(customer_cellphone):
    """Send a validation code to a customer cellphone"""
    validation = ''.join(secrets.choice('0123456789ABCDEF') for i in range(4))
    message = f"Informe o código ao vendedor: {validation}"
    cellphone = f"+{customer_cellphone}"
    sending_sms_aws(cellphone, message)
    ## TO-DO: to implement a log registry of this function
    return validation


def check_content_owner(request, content):
    """Check the content owner (store) and avoid unauthorized access to data."""
    if content.store != request.user:
        raise Http404


def clean_phone_number(phone_number):
    """Clear phone numbers, eliminating symbols, blank space and letters."""
    cleaned_number = re.sub(r'[^0-9]', '', phone_number)
    return cleaned_number








