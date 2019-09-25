from django.conf import settings
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView,DetailView,View
from .models import Item,Order,OrderItem,Address,Payment,Cupon,Refund
from .forms import CheckoutForm,CuponForm,RefundForm
from django.utils import timezone

import random
import string
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def create_ref_code():
    return '.'.join(random.choice(string.ascii_lowercase + string.digits))

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = 'home-page.html'

class OrderSummaryView(LoginRequiredMixin,View):
    def get(self,*args,**kwargs):
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            context={
                'object':order
            }
            return render(self.request, 'order_summary.html',context)
        except ObjectDoesNotExist:
            messages.error(self.request,'You don"t have active order')
            return redirect('/')

def is_valid_form(values):
    valid=True
    for value in values:
        if value=='':
            valid=False
    return valid

class CheckoutView(View):
    def get(self,*args,**kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form=CheckoutForm()
            context={
                'form':form,
                'couponForm':CuponForm(),
                'order':order,
                'DISPLAY_COUPON_FORM': True,
            }

            shipping_address_qs=Address.objects.filter(user=self.request.user,address_type='S',default=True)
            if shipping_address_qs.exists():
                context.update({'default_shipping_address':shipping_address_qs[0]})
            billing_address_qs = Address.objects.filter(user=self.request.user, address_type='B', default=True)
            if billing_address_qs.exists():
                context.update({'default_billing_address': billing_address_qs[0]})
            return render(self.request,'checkout-page.html',context)
        except ObjectDoesNotExist:
            messages.info(self.request, 'You don not have an active order')
            return redirect('core:checkout')

    def post(self,*args,**kwargs):
        form=CheckoutForm(self.request.POST or None)
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():
                # For shipping address
                use_default_shipping=form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print('Using the default shipping address')
                    address_qs = Address.objects.filter(user=self.request.user, address_type='S', default=True)
                    if address_qs.exists():
                        shipping_address=address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request,'No default shipping address available')
                        return redirect('core:checkout')
                else:
                    print('User is entering new shipping address')
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country= form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    if is_valid_form(['shipping_address1','shipping_address2','shipping_country','shipping_zip']):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(self.request,'Please fill in the require shipping fill.')
                # For billing address
                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')
                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print('Using the default billing address')
                    address_qs = Address.objects.filter(user=self.request.user, address_type='B', default=True)
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, 'No default billing address available')
                        return redirect('core:checkout')
                else:
                    print('User is entering new billing address')
                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')
                    if is_valid_form(
                            ['billing_address1', 'billing_address2', 'billing_country', 'billing_zip']):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()
                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info(self.request, 'Please fill in the require billing fill.')
                payment_options = form.cleaned_data.get('payment_options')
                if payment_options=='S':
                    return redirect('core:payment',payment_option='stripe')
                elif payment_options=='P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request,'Invalid payment options selected')
                    return redirect('core:checkout')
            messages.warning(self.request,'Failed Checkout')
            return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request,'You don"t have active order')
            return redirect('core:order-summary')

class PaymentView(View):
    def get(self,*args,**kwargs):
        #order
        order=Order.objects.get(user=self.request.user,ordered=False)
        if order.billing_address:
            context={
                'order':order,
                'DISPLAY_COUPON_FORM':False
            }
            return render(self.request,'payment.html',context)
        else:
            messages.error(self.request, 'You did not added a billing address')
            return redirect('core:checkout')

    def post(self,*args,**kwargs):
        token=self.request.POST.get('stripeToken')
        order=Order.objects.get(user=self.request.user,ordered=False)
        amount=int(order.get_total_order_price() * 100)

        try:
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                source=token,  # obtained with Stripe.js
                description="Charge for jenny.rosen@example.com"
            )

            # Create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total_order_price()
            payment.save()

            # Assign the payment to the order
            order_items=order.item.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ordered = True
            order.payment = payment
            order.ref_code=create_ref_code()
            order.save()

            messages.success(self.request,'Your order was successful')
            return redirect('/')
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})

            messages.error(self.request,f"{err.get('message')}")
            return redirect('/')
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request,'Rate limit error')
            return redirect('/')
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request,'Invalid request error')
            return redirect('/')
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request,'Authentication error')
            return redirect('/')
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request,'Api connection error')
            return redirect('/')
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request,'Stripe error')
            return redirect('/')
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.error(self.request,'A serious error occurred.we have been notify')
            print('error:',e)
            return redirect('/')

class ProductDetailView(DetailView):
    model = Item
    template_name = 'product-page.html'

@login_required
def add_to_cart(request,slug):
    item=get_object_or_404(Item,slug=slug)
    order_item,created=OrderItem.objects.get_or_create(item=item,user=request.user,ordered=False)
    order_qs=Order.objects.filter(user=request.user,ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item.quantity+=1
            order_item.save()
            messages.info(request, 'This item quantity updated.')
            return redirect('core:order-summary')
        else:
            order.item.add(order_item)
            messages.info(request, 'This item was added your cart.')
            return redirect('core:order-summary')
    else:
        order_date=timezone.now()
        order=Order.objects.create(user=request.user,ordered_date=order_date)
        order.item.add(order_item)
        messages.info(request, 'This item was added your cart.')
        return redirect('core:order-summary')

@login_required
def remove_form_cart(request,slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            order.item.remove(order_item)
            messages.info(request, 'This item was removed your cart.')
            return redirect('core:order-summary')
        else:
            # add message saying item was not your cart
            messages.info(request, 'This item was not your cart.')
            return redirect('core:product-detail', slug=slug)
    else:
        # add message saying user doesn't have order
        messages.info(request, 'You don"t have active order.')
        return redirect('core:product-detail', slug=slug)


@login_required
def remove_single_item_form_cart(request,slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            if order_item.quantity >1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.item.remove(order_item)
            messages.info(request, 'This item quantity was updated.')
            return redirect('core:order-summary')
        else:
            # add message saying item was not your cart
            messages.info(request, 'This item was not your cart.')
            return redirect('core:product-detail', slug=slug)
    else:
        # add message saying user doesn't have order
        messages.info(request, 'You don"t have active order.')
        return redirect('core:product-detail', slug=slug)

def get_cupon(request,code):
    try:
        coupon = Cupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request,'This coupon does not exit')
        return redirect('core:checkout')

class AddCouponView(View):
    def post(self,*args,**kwargs):
        form=CuponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code=form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon=get_cupon(self.request,code)
                order.save()
                messages.success(self.request,'Successfully add coupon')
                return redirect('core:checkout')
            except ObjectDoesNotExist:
                messages.info(self.request,'You don not have an active order')
                return redirect('core:checkout')


class RequestRefundView(View):
    def get(self,*args,**kwargs):
        form=RefundForm()
        context={
            'form':form
        }
        return render(self.request,'request_refund.html',context)
    def post(self,*args,**kwargs):
        form=RefundForm(self.request.POST or None)
        if form.is_valid():
            ref_code=form.cleaned_data.get('ref_code')
            message=form.cleaned_data.get('message')
            email=form.cleaned_data.get('email')
            try:
                # edit the order
                order=Order.objects.get(ref_code=ref_code)
                order.refund_request=True
                order.save()

                # Store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
                messages.info(self.request, 'Your request was received')
                return redirect('core:request-refund')
            except ObjectDoesNotExist:
                messages.info(self.request, 'The order does not exist')
                return redirect('core:request-refund')
