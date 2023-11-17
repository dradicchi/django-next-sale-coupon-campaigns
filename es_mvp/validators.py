"""
Set custom constraints and validators to use in models.py.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date


def validate_sale_date(sale_date, days_inferior_limit=15, 
            days_superior_limit=1):
    """
    A validator to check if the sale date is into the acceptable range.
    For fraud control, only is possible to record sales with a transaction date 
    from 15 days ago to one day ahead, considering the registration date of the
    sale.
    """
    delta = abs(date.today() - sale_date)
    # Sale date is too old...
    if (sale_date < date.today()) and (delta.days > days_inferior_limit):
        raise ValidationError(
            _("It is a very old sale date. " + 
                    "The inferior limit is %(value)s day(s)."), 
            params={"value": format(days_inferior_limit, "02d")},
            code="date_invalid_inferior")
    # Sale date is in the future...
    elif (sale_date > date.today()) and (delta.days > days_superior_limit):
        raise ValidationError(
            _("The sale date is far in the future. " + 
                    "The superior limit is  %(value)s day(s)."), 
            params={"value": format(days_superior_limit, "02d")},
            code="date_invalid_superior")
    else:
        return None


