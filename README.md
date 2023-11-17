# es_mvp_next_order_coupon

A complete Django SaaS app to launching "next sale coupons" campaigns and incentive sales on retail business. This project applies a well-known heuristic from behavioral economics to encourage unexpected sales of products and services.

Note: This package is the first MVP deprecated (but completely functional) version of my Micro-SaaS business: ElasticSale.com

## CONTEXT

This app models a sale incentive program that rewards customers that originated a recent sale with a cashback coupon, redeemable on a new sale. The goal is to make 1 in 10 customers return (before the average repurchase period) to generate a new sale with a value close the original purchase.

The ordinary app user is a "store". It is a flexible concept that can  represent a single store, an autonomous salesperson, a retail chain with many
stores or even an e-commerce. A store owns (and only sees and manages) its  sales, customers, campaigns and respective coupons.

Therefore a sale is the trigger to bonify customers. Each new registered sale  can issue (if eligible) a single new coupon to be redeemed at the same store  as the original purchase. 

A coupon has an expiration date, a face value and its specific redemption conditions. Although is possible for a customer to accumulate many coupons for
the same store, only one coupon can be redeemed in a future new sale.

The eligibility and usage conditions for coupons are defined by campaigns. A store can have more than one campaign active at a given time, but only the one
that is applicable and has the highest cashback rate – is considered when  issuing the coupon.


## FEATURES

- Supports multiple campaigns and it is possible to activate/deactivate them;
- Allows standard parameters for launching campaigns and issuing coupons;
- There is a minimum/maximum sales value range for coupon issuance eligibility;
- Each issued coupon has a cashback value face, an expiration date and a maximum discount rate;
- Uses SMS messages to delivery cashback coupons;
- Lists sales, campaigns and coupons historics;
- Shows KPIs to control campaigns performance.


## TECHNICAL ASPECTS

- App implemented on Django 4.2;
- Indiscriminate use of javascript was avoided... Everything happens server-side, via POST/GET calls;
- SMS sending is supported by AWS SNS;
- The Django project configuration file has been preconfigured to support deployment to Platform.sh.

## Copyright

2023 dradicchi at gmail.com
