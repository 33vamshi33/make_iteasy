from django.shortcuts import render,redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse,reverse_lazy
from django.contrib.auth import authenticate,login,logout
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,DetailView,CreateView
from app1.models import Customer,Broker,User,connection,feedback,Message, Dispute # Added Dispute
from app1.forms import userform,brokerform,searchform,userprofileform,feedbackform,loginform, DisputeForm # Added DisputeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages # Added messages
from django.shortcuts import get_object_or_404 # Added get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from test1 import settings
from django.core.mail import send_mail
from django.db.models import Avg,Count
from django.contrib.auth.forms import AuthenticationForm
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# For Blog CBVs
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import BlogPost, BlogCategory, connection as ConnectionModel # Renaming import to avoid conflict
from .forms import BlogPostForm
# reverse_lazy is already imported
from decimal import Decimal # Added Decimal for price handling

# Create your views here.

def customerauth(user):
    if user.id is not None:
        return user.is_customer and user.is_authenticated
    return False

def brokerauth(user):
    if user.id is not None:
        return user.is_broker and user.is_authenticated
    return False

def iscustomer(fn=None):
    decorator=user_passes_test(customerauth)
    if fn:
        return decorator(fn)
    return decorator

def isbroker(fn=None):
    decorator=user_passes_test(brokerauth)
    if fn:
        return decorator(fn)
    return decorator

class homepage(TemplateView):
    template_name="homepage.html"

@iscustomer
def customerdetail(request):
    connection.objects.filter(broker_status="order not accepted").update(broker_status="request pending")
    
    # Initialize filter values
    department_filter = request.POST.get('department', '') if request.method == 'POST' else ''
    location_filter = request.POST.get('location', '') if request.method == 'POST' else ''
    days_filter_list = []
    min_rating_filter = request.POST.get('min_rating', '') if request.method == 'POST' else ''
    sort_by_value = request.POST.get('sort_by', '-average_rating') if request.method == 'POST' else '-average_rating'

    brokers = Broker.objects.all() # Start with all brokers

    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False) # For nav notifications
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False) # For nav notifications
    
    customer_obj = Customer.objects.get(user=request.user) # Get the customer object

    if request.method=='POST':
        if "connect" in request.POST: # Handle connection request separately
            newconnection=connection()
            presentbroker=Broker.objects.get(user__username=request.POST.get("broker"))
            presentcustomer=Customer.objects.get(user=request.user)
            prevconnection=connection.objects.filter(customer=presentcustomer).filter(broker=presentbroker).filter(customer_status="order pending")
            newconnection.broker=presentbroker
            newconnection.customer=presentcustomer
            newconnection.customer_status="order pending"
            newconnection.broker_status="request pending"
            newconnection.description=request.POST.get('description')
            newconnection.created_time=timezone.now()
            newconnection.modified_time=timezone.now()
            if len(prevconnection) == 0 :
                subject = f"New Connection Request from {newconnection.customer.user.username}"
                message_body = f"""
Hi {newconnection.broker.user.username},

You have received a new connection request from {newconnection.customer.user.username}.

Details:
- Description: {newconnection.description}
- Customer Email: {newconnection.customer.user.email}

You can view and manage this request in your dashboard:
{request.build_absolute_uri(reverse('app1:broker_pendingrequests'))}

Thanks,
The Workiteasy Team
"""
                send_mail(
                    subject,
                    message_body,
                    settings.DEFAULT_FROM_EMAIL, # Use default from email
                    [newconnection.broker.user.email,],
                    fail_silently=False
                )
                newconnection.save()
                # Send notification to broker
                channel_layer = get_channel_layer()
                broker_group_name = f"broker_{newconnection.broker.user.id}"
                async_to_sync(channel_layer.group_send)(
                    broker_group_name,
                    {
                        "type": "notification.message",
                        "message": {
                            "event": "new_connection_request",
                            "customer_id": newconnection.customer.user.id,
                            "customer_name": newconnection.customer.user.username,
                            "description": newconnection.description,
                            "connection_id": newconnection.id,
                        }
                    }
                )
            return redirect(reverse('app1:customer_pendingorders'))

        else :
            department=request.POST.get('department')
            location=request.POST.get('location')
            mylist=[]
            alllist=[0,1,2,3,4,5,6]
            for i in alllist:
                if str(i) in request.POST:
                    mylist.append(i)
            if len(mylist) == 0:
                mylist=alllist 
            # This is the search/filter part of the POST request
            department_filter=request.POST.get('department', '')
            location_filter=request.POST.get('location', '')
            all_days_values=[0,1,2,3,4,5,6] # All possible days
            
            for i in all_days_values:
                if str(i) in request.POST:
                    days_filter_list.append(i)
            
            if not days_filter_list: # If no days selected, assume all days
                days_filter_list = all_days_values
            
            # Apply department and location filters first
            brokers = Broker.objects.filter(department_name__icontains=department_filter, location__icontains=location_filter)

            # Apply days filter (any selected day must be in broker's days)
            # This requires a more complex query or iterating if days are stored as a string/list in the model.
            # Assuming 'days' is a MultiSelectField or similar that stores a list of choices.
            # For simplicity, let's assume we filter if ANY of the selected days are present.
            # A more precise filter might be needed depending on how 'days' is stored.
            
            # If days_filter_list is not all_days_values, then apply the filter
            if set(days_filter_list) != set(all_days_values):
                filtered_by_day = Broker.objects.none()
                for day_val in days_filter_list:
                    filtered_by_day = filtered_by_day.union(brokers.filter(days__contains=day_val))
                brokers = filtered_by_day.distinct()


            # Apply minimum rating filter
            min_rating_filter = request.POST.get('min_rating')
            if min_rating_filter:
                try:
                    min_rating_value = float(min_rating_filter)
                    brokers = brokers.filter(average_rating__gte=min_rating_value)
                except ValueError:
                    pass # Ignore if min_rating is not a valid number

            # Apply sorting
            sort_by_value = request.POST.get('sort_by', '-average_rating') # Default sort
            if sort_by_value == 'rating_asc':
                brokers = brokers.order_by('average_rating')
            elif sort_by_value == 'rating_desc':
                brokers = brokers.order_by('-average_rating')
            elif sort_by_value == 'dept_asc':
                brokers = brokers.order_by('department_name')
            elif sort_by_value == 'dept_desc':
                brokers = brokers.order_by('-department_name')
            else:
                brokers = brokers.order_by('-average_rating') # Default
    else:
        # For GET request, apply default sorting
        brokers = Broker.objects.order_by(sort_by_value)


    # Calculate statistics for the customer
    new_pending_orders_count = connection.objects.filter(customer=customer_obj, customer_status="order pending", is_customerread=False).count()
    active_accepted_orders_count = connection.objects.filter(customer=customer_obj, customer_status="order accepted").count()
    # For "recently completed", let's do total completed for now, similar to broker.
    completed_orders_count = connection.objects.filter(customer=customer_obj, customer_status="order completed").count()

    context={
        "unreadconnections":unreadconnections, # For nav notifications
        "unreadmessages":unreadmessages, # For nav notifications
        "tl":len(unreadconnections)+len(unreadmessages), # For nav total
        "brokers": brokers,
        "customer": request.user, # request.user is the User object, customer_obj is the Customer profile
        "department_filter": department_filter,
        "location_filter": location_filter,
        "days_filter_list": days_filter_list, 
        "min_rating_filter": min_rating_filter,
        "sort_by_value": sort_by_value,
        "new_pending_orders_count": new_pending_orders_count,
        "active_accepted_orders_count": active_accepted_orders_count,
        "completed_orders_count": completed_orders_count,
    }
    return render(request,"customer/home.html",context)
    

@isbroker
@csrf_exempt
def brokerdetail(request):
    broker=Broker.objects.get(user=request.user)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False) # This is existing unread count for nav
    mylist=broker.days
    if request.method=='POST': # This POST is for updating broker's available days
        mylist=[]
        alllist=[0,1,2,3,4,5,6]
        for i in alllist:
            if str(i) in request.POST:
                mylist.append(i)
        broker.days=mylist
        broker.save()
        # It's good practice to redirect after a successful POST to avoid re-posting on refresh
        return redirect(reverse('app1:broker_home')) 

    # Calculate statistics
    new_pending_requests_count = connection.objects.filter(broker=broker, broker_status="request pending", is_brokerread=False).count()
    active_accepted_connections_count = connection.objects.filter(broker=broker, broker_status="request accepted").count()
    # For "recently completed", let's define "recent" as e.g., last 7 days, or just total completed.
    # For simplicity now, let's do total completed, can be refined later if "recent" is time-bound.
    completed_connections_count = connection.objects.filter(broker=broker, broker_status="request completed").count()

    context={
        "mylist":mylist,
        "unreadmessages":unreadmessages, # For nav notifications
        "unreadconnections":unreadconnections, # For nav notifications
        "tl":len(unreadconnections)+len(unreadmessages), # For nav total
        "new_pending_requests_count": new_pending_requests_count,
        "active_accepted_connections_count": active_accepted_connections_count,
        "completed_connections_count": completed_connections_count,
    }
    return render(request,"broker/home.html",context=context)

def customerlogin(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('app1:customer_home')
    else:
        form = AuthenticationForm()
    return render(request, 'customer/login.html', {'loginform': form})

def brokerlogin(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('app1:broker_home')
    else:
        form = AuthenticationForm()
    return render(request, 'broker/login.html', {'loginform': form})

def customersignup(request):
    registered=False
    if request.method=='POST':
        user_form=userform(data=request.POST)
        user_profileform=userprofileform(request.POST,request.FILES)

        if user_form.is_valid() and user_profileform.is_valid() :

            user=user_form.save()
            user.is_customer=True
            if 'picture' in request.FILES :
                user.picture=request.FILES['picture']
            user.save()
            customer=Customer()
            customer.user=user
            customer.save()
            subject = f"Welcome to Workiteasy, {user.username}!"
            message_body = f"""
Hi {user.username},

Thank you for registering with Workiteasy as a customer! We're excited to have you.

You can now log in and start finding skilled brokers for your needs:
{request.build_absolute_uri(reverse('app1:customer_login'))}

If you have any questions, feel free to contact our support.

Thanks,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email,],
                fail_silently=False
            )
            registered=True
        else:
            print(user_form.errors)
            print(user_profileform.errors)

    else:

        user_form=userform()
        user_profileform=userprofileform()
    if registered:
        return HttpResponseRedirect(reverse('app1:customer_login'))
    return render(request,'customer/signup.html',{'registered':registered,
                                                    'userform':user_form,
                                                    'userprofileform':user_profileform })


def brokersignup(request):
    registered=False

    if request.method=='POST':
        user_form=userform(data=request.POST)
        broker_form=brokerform(data=request.POST)
        user_profileform=userprofileform(request.POST,request.FILES)
        if user_form.is_valid() and broker_form.is_valid() and user_profileform.is_valid() :

            user=user_form.save()
            user.is_broker=True
            if 'picture' in request.FILES :
                user.picture=request.FILES['picture']
            user.save()
            
            broker=broker_form.save(commit=False)
            broker.user=user
            broker.save()

            subject = f"Welcome to Workiteasy, Broker {user.username}!"
            message_body = f"""
Hi {user.username},

Thank you for registering as a Broker on Workiteasy! We're thrilled to have you join our community of skilled professionals.

Your profile is now active. You can log in here:
{request.build_absolute_uri(reverse('app1:broker_login'))}

Make sure to complete your profile to attract more customers. If you have any questions, please don't hesitate to reach out.

Best regards,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email,],
                fail_silently=False
            )
            registered=True
        else:
            print(user_form.errors)
            print(broker_form.errors)

    else:

        user_form=userform()
        broker_form=brokerform()
        user_profileform=userprofileform()
    if registered:

        return HttpResponseRedirect(reverse('app1:broker_login'))
    return render(request,'broker/signup.html',{'registered':registered,
                                                'userform':user_form ,
                                                'brokerform':broker_form,
                                                "userprofileform":user_profileform})


@iscustomer
def customerlogout(request):
    logout(request)
    return redirect(reverse('app1:homepage'))

@isbroker
def brokerlogout(request):
    logout(request)
    return redirect(reverse('app1:homepage'))

@iscustomer
def customerorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    acceptedorders=orderslist.filter(customer_status="order accepted")
    rejectedorders=orderslist.filter(customer_status="order rejected")
    pendingorders=orderslist.filter(customer_status="order pending")
    completedorders=orderslist.filter(customer_status="order completed")
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    
    # Fetch disputes for all orders
    orders_with_disputes = []
    for order in orderslist:
        dispute = Dispute.objects.filter(connection=order, reporter_user=request.user).order_by('-created_at').first()
        orders_with_disputes.append({'order': order, 'dispute': dispute})
        
    #qs=connection.objects.filter(customer__user=request.user).update(is_read=True)
    context={
        "orders_with_disputes": orders_with_disputes, # Pass this instead of raw orderslist
        "acceptedorders":acceptedorders, # These might also need dispute info if rendered separately
        "rejectedorders":rejectedorders, # These might also need dispute info
        "pendingorders":pendingorders, # These might also need dispute info
        "completedorders":completedorders, # These might also need dispute info
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedorders),
        "rsize":len(rejectedorders),
        "psize":len(pendingorders),
        "csize":len(completedorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/orders.html",context=context)

@iscustomer
def customerpendingorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    # orderslist=connection.objects.filter(customer=presentcustomer) # Not used directly
    pendingorders_qs = connection.objects.filter(customer=presentcustomer, customer_status="order pending")
    pendingorders_qs.update(is_customerread=True) # Mark as read

    pendingorders_with_disputes = []
    for order in pendingorders_qs:
        dispute = Dispute.objects.filter(connection=order, reporter_user=request.user).order_by('-created_at').first()
        pendingorders_with_disputes.append({'order': order, 'dispute': dispute})

    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "pendingorders_with_disputes":pendingorders_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "psize":len(pendingorders_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/pendingorders.html",context=context)

@iscustomer
def customeracceptedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    # orderslist=connection.objects.filter(customer=presentcustomer) # Not used directly
    acceptedorders_qs = connection.objects.filter(customer=presentcustomer, customer_status="order accepted")
    acceptedorders_qs.update(is_customerread=True) # Mark as read

    acceptedorders_with_disputes = []
    for order in acceptedorders_qs:
        dispute = Dispute.objects.filter(connection=order, reporter_user=request.user).order_by('-created_at').first()
        acceptedorders_with_disputes.append({'order': order, 'dispute': dispute})
        
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "acceptedorders_with_disputes": acceptedorders_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedorders_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/acceptedorders.html",context=context)

@iscustomer
def customerrejectedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    # orderslist=connection.objects.filter(customer=presentcustomer) # Not used directly
    rejectedorders_qs = connection.objects.filter(customer=presentcustomer, customer_status="order rejected")
    rejectedorders_qs.update(is_customerread=True) # Mark as read

    rejectedorders_with_disputes = [] # Disputes might not be relevant for rejected orders, but for consistency:
    for order in rejectedorders_qs:
        dispute = Dispute.objects.filter(connection=order, reporter_user=request.user).order_by('-created_at').first()
        rejectedorders_with_disputes.append({'order': order, 'dispute': dispute})

    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "rejectedorders_with_disputes": rejectedorders_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "rsize":len(rejectedorders_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/rejectedorders.html",context=context)

@iscustomer
def customercompletedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    # orderslist=connection.objects.filter(customer=presentcustomer) # Not used directly
    completedorders_qs = connection.objects.filter(customer=presentcustomer, customer_status="order completed")
    completedorders_qs.update(is_customerread=True) # Mark as read

    completedorders_with_disputes = []
    for order in completedorders_qs:
        dispute = Dispute.objects.filter(connection=order, reporter_user=request.user).order_by('-created_at').first()
        completedorders_with_disputes.append({'order': order, 'dispute': dispute})

    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "completedorders_with_disputes": completedorders_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "csize":len(completedorders_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/completedorders.html",context=context)

@isbroker
@csrf_exempt
def brokerrequests(request):
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            
            # Get price from form
            price_str = request.POST.get(f'price_for_connection_{presentconnection.id}')
            if price_str:
                try:
                    presentconnection.price = Decimal(price_str)
                except (ValueError, TypeError):
                    messages.error(request, f"Invalid price format for connection {presentconnection.id}. Please enter a valid decimal number.")
                    # Optionally, do not save and return to form with error, or save without price
                    # For now, we'll save and broker can update later if needed.
                    pass # Price remains None or its old value
            else:
                # Handle case where price is not submitted - e.g. set a default, or raise error
                # For now, we allow it to be None if not provided, assuming it can be set later.
                 messages.warning(request, f"No price was set for connection {presentconnection.id} by the broker.")


            # subject="Yahoo! your order is accepted"
            # body=f"makeiteasy helps, it really helps"
            # receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentconnection.customer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "connection_accepted",
                        "broker_id": presentconnection.broker.user.id,
                        "broker_name": presentconnection.broker.user.username,
                        "connection_id": presentconnection.id,
                    }
                }
            )
            # return render(request,"broker/requests.html",context=context)
        elif "reject" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order rejected"
            presentconnection.broker_status="request rejected"
            presentconnection.modified_time=timezone.now()
                subject = f"Your Connection with {presentconnection.broker.user.username} is Now Complete (from Accepted)"
                message_body = f"""
Hi {presentconnection.customer.user.username},

This is to confirm that your accepted connection regarding "{presentconnection.description}" with broker {presentconnection.broker.user.username} has been marked as completed.

You can view your completed orders here:
{request.build_absolute_uri(reverse('app1:customer_completedorders'))}

We hope you had a great experience!

Thanks,
The Workiteasy Team
"""
                send_mail(
                    subject,
                    message_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [presentconnection.customer.user.email,],
                    fail_silently=False
                )
            presentconnection.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentconnection.customer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "connection_rejected",
                        "broker_id": presentconnection.broker.user.id,
                        "broker_name": presentconnection.broker.user.username,
                        "connection_id": presentconnection.id,
                    }
                }
            )
            # return render(request,"broker/requests.html",context=context)
        elif "completed" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order completed"
            presentconnection.broker_status="request completed"
            presentconnection.modified_time=timezone.now()
            
            # Price setting logic (from previous step, ensure it's here)
            price_str = request.POST.get(f'price_for_connection_{presentconnection.id}')
            if price_str:
                try:
                    presentconnection.price = Decimal(price_str)
                except (ValueError, TypeError):
                    messages.error(request, f"Invalid price format for connection {presentconnection.id}.")
                    pass 
            else:
                 messages.warning(request, f"No price was set for connection {presentconnection.id} by the broker.")

            subject = f"Your Connection Request with {presentconnection.broker.user.username} has been Accepted (from Pending)"
            message_body = f"""
Hi {presentconnection.customer.user.username},

Good news! Your pending connection request regarding "{presentconnection.description}" with broker {presentconnection.broker.user.username} has been accepted.

Price quoted: ${presentconnection.price if presentconnection.price is not None else "Not set yet."}

You can view the details here:
{request.build_absolute_uri(reverse('app1:customer_acceptedorders'))}

Thanks,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [presentconnection.customer.user.email,],
                fail_silently=False
            )
            presentconnection.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentconnection.customer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "connection_completed",
                        "broker_id": presentconnection.broker.user.id,
                        "broker_name": presentconnection.broker.user.username,
                        "connection_id": presentconnection.id,
                    }
                }
            )
        else:
            pass
            # return render(request,"broker/requests.html",context=context)
        
    presentbroker=Broker.objects.get(user=request.user)
    requestslist=connection.objects.filter(broker=presentbroker)
    acceptedrequests=requestslist.filter(broker_status="request accepted")
    rejectedrequests=requestslist.filter(broker_status="request rejected")
    pendingrequests=requestslist.filter(broker_status="request pending")
    completedrequests=requestslist.filter(broker_status="request completed")
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)

    def _get_connections_with_disputes(queryset):
        connections_with_disputes = []
        for conn in queryset:
            latest_dispute = Dispute.objects.filter(connection=conn).order_by('-created_at').first()
            connections_with_disputes.append({'connection': conn, 'latest_dispute': latest_dispute})
        return connections_with_disputes

    context={
        "requests_with_disputes": _get_connections_with_disputes(requestslist),
        "acceptedrequests_with_disputes": _get_connections_with_disputes(acceptedrequests),
        "rejectedrequests_with_disputes": _get_connections_with_disputes(rejectedrequests),
        "pendingrequests_with_disputes": _get_connections_with_disputes(pendingrequests),
        "completedrequests_with_disputes": _get_connections_with_disputes(completedrequests),
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedrequests), # Original querysets for counts
        "rsize":len(rejectedrequests),
        "psize":len(pendingrequests),
        "csize":len(completedrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/requests.html",context=context)

@isbroker
def brokerpendingrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    # requestlist=connection.objects.filter(broker=presentbroker) # Not used directly
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            
            # Get price from form - this was already done in the previous step, ensuring it's still here.
            price_str = request.POST.get(f'price_for_connection_{presentconnection.id}')
            if price_str:
                try:
                    presentconnection.price = Decimal(price_str)
                except (ValueError, TypeError):
                    messages.error(request, f"Invalid price format for connection {presentconnection.id}. Please enter a valid decimal number.")
                    pass 
            else:
                 messages.warning(request, f"No price was set for connection {presentconnection.id} by the broker.")

            subject = f"Your Connection Request with {presentconnection.broker.user.username} has been Accepted!"
            message_body = f"""
Hi {presentconnection.customer.user.username},

Good news! Your connection request regarding "{presentconnection.description}" with broker {presentconnection.broker.user.username} has been accepted.

Price quoted: ${presentconnection.price if presentconnection.price is not None else "Not set yet."}

You can view the details and proceed with payment (if applicable) here:
{request.build_absolute_uri(reverse('app1:customer_acceptedorders'))}

Thanks,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [presentconnection.customer.user.email,],
                fail_silently=False
            )
            presentconnection.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentconnection.customer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "connection_accepted_from_pending",
                        "broker_id": presentconnection.broker.user.id,
                        "broker_name": presentconnection.broker.user.username,
                        "connection_id": presentconnection.id,
                    }
                }
            )
            return redirect(reverse("app1:broker_acceptedrequests"))

            # return render(request,"broker/requests.html",context=context)
        elif "reject" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order rejected"
            presentconnection.broker_status="request rejected"
            presentconnection.modified_time=timezone.now()
            subject = f"Update on Your Connection Request with {presentconnection.broker.user.username}"
            message_body = f"""
Hi {presentconnection.customer.user.username},

We're writing to inform you that your connection request regarding "{presentconnection.description}" with broker {presentconnection.broker.user.username} has been rejected.

If you have any questions, you can contact the broker or search for other brokers.

View your rejected orders here:
{request.build_absolute_uri(reverse('app1:customer_rejectedorders'))}

Thanks,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [presentconnection.customer.user.email,],
                fail_silently=False
            )
            presentconnection.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentconnection.customer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "connection_rejected_from_pending",
                        "broker_id": presentconnection.broker.user.id,
                        "broker_name": presentconnection.broker.user.username,
                        "connection_id": presentconnection.id,
                    }
                }
            )
            return redirect(reverse("app1:broker_rejectedrequests"))

        else:
            pass

    pendingrequests_qs = connection.objects.filter(broker=presentbroker,broker_status="request pending")
    pendingrequests_qs.update(is_brokerread=True) # Mark as read

    pendingrequests_with_disputes = []
    for conn_obj in pendingrequests_qs:
        latest_dispute = Dispute.objects.filter(connection=conn_obj).order_by('-created_at').first()
        pendingrequests_with_disputes.append({'connection': conn_obj, 'latest_dispute': latest_dispute})

    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "pendingrequests_with_disputes": pendingrequests_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "psize":len(pendingrequests_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/pendingrequests.html",context)

@isbroker
def brokeracceptedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "completed" in request.POST and presentconnection is not None:
                presentconnection.customer_status="order completed"
                presentconnection.broker_status="request completed"
                presentconnection.modified_time=timezone.now()
            subject = f"Your Connection with {presentconnection.broker.user.username} is Complete!"
            message_body = f"""
Hi {presentconnection.customer.user.username},

Great news! Your connection regarding "{presentconnection.description}" with broker {presentconnection.broker.user.username} has been marked as completed.

We hope you had a positive experience. You can view your completed orders here:
{request.build_absolute_uri(reverse('app1:customer_completedorders'))}

Consider leaving a review for {presentconnection.broker.user.username} to help other users.

Thanks,
The Workiteasy Team
"""
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [presentconnection.customer.user.email,],
                fail_silently=False
            )
                presentconnection.save()
                # Send notification to customer
                channel_layer = get_channel_layer()
                customer_group_name = f"customer_{presentconnection.customer.user.id}"
                async_to_sync(channel_layer.group_send)(
                    customer_group_name,
                    {
                        "type": "notification.message",
                        "message": {
                            "event": "connection_completed_from_accepted",
                            "broker_id": presentconnection.broker.user.id,
                            "broker_name": presentconnection.broker.user.username,
                            "connection_id": presentconnection.id,
                        }
                    }
                )
    acceptedrequests_qs = connection.objects.filter(broker=presentbroker,broker_status="request accepted")
    acceptedrequests_qs.update(is_brokerread=True) # Mark as read

    acceptedrequests_with_disputes = []
    for conn_obj in acceptedrequests_qs:
        latest_dispute = Dispute.objects.filter(connection=conn_obj).order_by('-created_at').first()
        acceptedrequests_with_disputes.append({'connection': conn_obj, 'latest_dispute': latest_dispute})

    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "acceptedrequests_with_disputes": acceptedrequests_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedrequests_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/acceptedrequests.html",context)

@isbroker
def brokercompletedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    completedrequests_qs = connection.objects.filter(broker=presentbroker,broker_status="request completed")
    completedrequests_qs.update(is_brokerread=True) # Mark as read

    completedrequests_with_disputes = []
    for conn_obj in completedrequests_qs:
        latest_dispute = Dispute.objects.filter(connection=conn_obj).order_by('-created_at').first()
        completedrequests_with_disputes.append({'connection': conn_obj, 'latest_dispute': latest_dispute})
        
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "completedrequests_with_disputes": completedrequests_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "csize":len(completedrequests_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/completedrequests.html",context)

@isbroker
def brokerrejectedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            subject="Yahoo! your order is accepted"
            body=f"makeiteasy helps, it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()

    rejectedrequests_qs = connection.objects.filter(broker=presentbroker,broker_status="request rejected")
    rejectedrequests_qs.update(is_brokerread=True) # Mark as read

    rejectedrequests_with_disputes = []
    for conn_obj in rejectedrequests_qs:
        latest_dispute = Dispute.objects.filter(connection=conn_obj).order_by('-created_at').first()
        rejectedrequests_with_disputes.append({'connection': conn_obj, 'latest_dispute': latest_dispute})

    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "rejectedrequests_with_disputes": rejectedrequests_with_disputes, # Use this in template
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "rsize":len(rejectedrequests_qs), # Use original queryset for size
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/rejectedrequests.html",context)

@iscustomer
def customerprofile(request):
    picture_form=userprofileform()
    if request.method == 'POST' and request.user.id is not None:
        customer=Customer.objects.get(user=request.user)
        user=User.objects.filter(username=request.user.username).first()
        username=request.POST.get("username")
        password=request.POST.get("password")
        phonenumber=request.POST.get("phonenumber")
        email=request.POST.get("email")
        lists=User.objects.filter(username=username)
        if username is not None and len(username) and len(lists) ==0 :
            user.username=username
        if password is not None and len(password) :
            user.set_password(password)
        if email is not None and len(email):
            user.email=email
        picture_form=userprofileform(request.POST,request.FILES)

        if picture_form.is_valid() and 'picture' in request.FILES :
            user.picture=request.FILES['picture']
        user.save()
        customer.user=user
        customer.save()
        return redirect(reverse("app1:customer_home"))
    customer=Customer.objects.get(user=request.user)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "customer":customer,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "pictureform":picture_form,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/profile.html",context=context)

@isbroker
def brokerprofile(request):
    picture_form=userprofileform()
    if request.method == 'POST' and request.user.id is not None:
        broker=Broker.objects.get(user=request.user)
        user=User.objects.filter(username=request.user.username).first()
        username=request.POST.get("username")
        password=request.POST.get("password")
        phonenumber=request.POST.get("phonenumber")
        email=request.POST.get("email")
        departmentname=request.POST.get("departmentname")
        location=request.POST.get("location")
        experience = request.POST.get("experience")
        skills = request.POST.get("skills")
        portfolio_link = request.POST.get("portfolio_link")

        lists=User.objects.filter(username=username)
        if len(username) and len(lists) ==0 : # check if username is not empty and not already taken
            user.username=username
        if len(password) :
            user.set_password(password)
        if len(email): # check if email is not empty
            user.email=email

        picture_form=userprofileform(request.POST,request.FILES)

        if picture_form.is_valid() and 'picture' in request.FILES :
            user.picture=request.FILES['picture']
        user.save() # Save user object first

        broker.user=user # This should already be set, but re-assigning is fine
        if departmentname: # check if not empty
            broker.department_name=departmentname
        if location: # check if not empty
            broker.location=location
        if experience:
            try:
                broker.experience = int(experience)
            except ValueError:
                pass # Or handle error
        broker.skills = skills if skills is not None else broker.skills # Update if provided, else keep old
        broker.portfolio_link = portfolio_link if portfolio_link is not None else broker.portfolio_link # Update if provided

        broker.save()
        return redirect(reverse("app1:broker_home"))

    broker=Broker.objects.get(user=request.user)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "broker":broker,
        "pictureform":picture_form,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages),
        # Pass current values of new fields for pre-filling the form
        "current_experience": broker.experience,
        "current_skills": broker.skills,
        "current_portfolio_link": broker.portfolio_link,
    }
    return render(request,"broker/profile.html",context)

@iscustomer
def customerreview(request,pk):
    feedback_form=feedbackform()
    customer=Customer.objects.get(user=request.user)
    broker=Broker.objects.get(pk=pk)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    if request.method=='POST' :
        description=request.POST.get("description")
        rating=request.POST.get("rating")
        newfeedback=feedback()
        oldfeedback=feedback.objects.filter(customer=customer,broker=broker).first()
        if oldfeedback is   None:
            newfeedback.customer=customer
            newfeedback.broker=broker
            newfeedback.description=description
            newfeedback.rating=rating
            newfeedback.created_time=timezone.now()
            newfeedback.save()
            reviews=feedback.objects.filter(broker=broker)
            presentbrokerfeedback=feedback.objects.filter(broker=broker)
            avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
            broker.average_rating=avgrating
            broker.save()
            return redirect("app1:customer_home")
        else :
            oldfeedback.description=description
            oldfeedback.rating=rating
            oldfeedback.save()
            reviews=feedback.objects.filter(broker=broker)
            presentbrokerfeedback=feedback.objects.filter(broker=broker)
            avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
            broker.average_rating=avgrating
            broker.save()
            
            return redirect("app1:customer_home")
    else :
        feedback_form=feedbackform()
        context={
            "feedbackform":feedback_form,
            "unreadmessages":unreadmessages,
            "unreadconnections":unreadconnections,
            "tl":len(unreadconnections)+len(unreadmessages)
        }
        return render(request,"customer/review.html",context)

@login_required
def brokerreviews(request,pk):
    presentbroker=Broker.objects.filter(user__pk=pk).first()
    reviews=feedback.objects.filter(broker=presentbroker)
    presentbrokerfeedback=feedback.objects.filter(broker=presentbroker)
    avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
    if avgrating is not None:
        presentbroker.average_rating=avgrating
    else :
        avgrating=0
    presentbroker.save()
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "reviews":reviews,
        "rsize":len(reviews),
        "avgrating":avgrating,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/review.html",context)

@iscustomer
def customerchat(request,pk):
    presentcustomer=Customer.objects.get(user=request.user)
    presentbroker=Broker.objects.get(pk=pk)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    if request.method=='POST':
        message=request.POST.get("message")
        if message != "":
            newmessage=Message()
            newmessage.customer=Customer.objects.get(user=request.user)
            newmessage.broker=Broker.objects.get(pk=pk)
            newmessage.message=message
            newmessage.timestamp=timezone.now()
            newmessage.flag=True
            newmessage.is_read=False # For broker, customer has read it by sending
            newmessage.save()
            # Send notification to broker
            channel_layer = get_channel_layer()
            broker_group_name = f"broker_{presentbroker.user.id}"
            async_to_sync(channel_layer.group_send)(
                broker_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "new_chat_message",
                        "sender_id": presentcustomer.user.id,
                        "sender_name": presentcustomer.user.username,
                        "sender_role": "customer",
                        "receiver_id": presentbroker.user.id,
                        "message_text": newmessage.message,
                        "connection_pk": f"{presentcustomer.id}_{presentbroker.id}" # A potential way to identify chat context
                    }
                }
            )

    messages=Message.objects.filter(customer=presentcustomer,broker=presentbroker).order_by("-timestamp")[::-1]
    Message.objects.filter(customer=presentcustomer,broker=presentbroker).update(is_customerread=True)
    context={
        "messages":messages,
        "msize":len(messages),
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/chat.html",context)

@isbroker
def brokerchat(request,pk):
    presentcustomer=Customer.objects.get(pk=pk)
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        message=request.POST.get("message")
        if message != "":
            newmessage=Message()
            newmessage.customer=presentcustomer
            newmessage.broker=presentbroker
            newmessage.message=message
            newmessage.timestamp=timezone.now()
            newmessage.flag=False
            newmessage.is_read=False # For customer, broker has read it by sending
            newmessage.save()
            # Send notification to customer
            channel_layer = get_channel_layer()
            customer_group_name = f"customer_{presentcustomer.user.id}"
            async_to_sync(channel_layer.group_send)(
                customer_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "new_chat_message",
                        "sender_id": presentbroker.user.id,
                        "sender_name": presentbroker.user.username,
                        "sender_role": "broker",
                        "receiver_id": presentcustomer.user.id,
                        "message_text": newmessage.message,
                        "connection_pk": f"{presentcustomer.id}_{presentbroker.id}" # A potential way to identify chat context
                    }
                }
            )

    messages=Message.objects.filter(customer=presentcustomer,broker=presentbroker).order_by("-timestamp")[::-1]
    Message.objects.filter(customer=presentcustomer,broker=presentbroker).update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "messages":messages,
        "msize":len(messages),
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/chat.html",context)


@iscustomer
def report_dispute(request, connection_id):
    conn = get_object_or_404(connection, id=connection_id, customer__user=request.user)
    
    # Check if an 'Open' or 'Under Review' dispute already exists for this connection by this user
    existing_dispute = Dispute.objects.filter(connection=conn, reporter_user=request.user, status__in=['Open', 'Under Review']).first()
    if existing_dispute:
        messages.error(request, f"An active dispute (Status: {existing_dispute.status}) already exists for this connection.")
        return redirect('app1:customer_orders') # Or wherever appropriate

    if request.method == 'POST':
        form = DisputeForm(request.POST)
        if form.is_valid():
            dispute = Dispute(
                connection=conn,
                reporter_user=request.user,
                reason=form.cleaned_data['reason']
            )
            dispute.save()
            messages.success(request, 'Your dispute has been successfully reported.')
            # Send notification to broker about the dispute
            channel_layer = get_channel_layer()
            broker_group_name = f"broker_{conn.broker.user.id}"
            async_to_sync(channel_layer.group_send)(
                broker_group_name,
                {
                    "type": "notification.message",
                    "message": {
                        "event": "new_dispute_reported",
                        "customer_name": request.user.username,
                        "connection_id": conn.id,
                        "reason": dispute.reason,
                    }
                }
            )
            return redirect('app1:customer_orders')
    else:
        form = DisputeForm()

    context = {
        'form': form,
        'connection_obj': conn  # Renamed to avoid conflict with the model name 'connection'
    }
    return render(request, 'customer/report_dispute.html', context)

# Blog Views

class BlogPostListView(ListView):
    model = BlogPost
    template_name = 'blog/blog_post_list.html' # Assuming templates are in app1/templates/blog/
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        return BlogPost.objects.filter(status='Published').order_by('-published_date')

class BlogPostDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/blog_post_detail.html' # Assuming templates are in app1/templates/blog/
    context_object_name = 'post'
    # Queryset to ensure only published posts are accessible via detail view directly
    # Slug uniqueness for date should handle most cases, but status check is good practice
    queryset = BlogPost.objects.filter(status='Published') 

class BlogPostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'blog/blog_post_form.html' # Assuming templates are in app1/templates/blog/
    success_url = reverse_lazy('app1:blog_post_list') # Make sure app_name is 'app1'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_broker or request.user.is_staff):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        # If slug is not provided or needs to be auto-generated from title before validation/saving:
        # if not form.instance.slug:
        #     form.instance.slug = slugify(form.instance.title) 
        #     # Basic check for slug collision if not relying solely on unique_for_date
        #     # This is better handled in form's clean_slug or model's save if complex logic is needed
        return super().form_valid(form)

class BlogPostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'blog/blog_post_form.html' # Assuming templates are in app1/templates/blog/
    # success_url = reverse_lazy('app1:blog_post_list') # Can also redirect to post detail

    def get_success_url(self):
        return reverse_lazy('app1:blog_post_detail', kwargs={'slug': self.object.slug})

    def test_func(self):
        post = self.get_object()
        return post.author == self.request.user or self.request.user.is_staff

# Payment Views

@login_required
@iscustomer
def create_checkout_session(request, connection_id):
    conn = get_object_or_404(ConnectionModel, id=connection_id, customer__user=request.user)

    if not conn.price or conn.price <= 0:
        messages.error(request, "Price not set for this connection or is invalid. Please contact the broker.")
        return redirect('app1:customer_acceptedorders') # Or wherever appropriate

    # Simulate Stripe call
    print(f"Attempting to create Stripe checkout session for connection ID {connection_id} with price {conn.price}")
    
    # Simulate successful payment processing
    conn.payment_status = 'Paid'
    conn.stripe_payment_intent_id = f'simulated_pi_{conn.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}'
    conn.save()

    messages.success(request, "Payment processed successfully (Simulated).")
    return redirect(reverse('app1:payment_success'))

@login_required
@iscustomer
def payment_success(request):
    return render(request, 'customer/payment_success.html')

@login_required
@iscustomer
def payment_cancel(request):
    return render(request, 'customer/payment_cancel.html')